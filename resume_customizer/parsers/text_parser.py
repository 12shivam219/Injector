"""
Text parsing module for Resume Customizer application.
Handles parsing of tech stacks and bullet points from different input formats.
"""

import re
from typing import List, Tuple, Optional, Dict
from functools import lru_cache
from config import PARSING_CONFIG
from infrastructure.utilities.logger import get_logger
from infrastructure.monitoring.performance_cache import cached, get_cache_manager
from infrastructure.security.security_enhancements import InputSanitizer

logger = get_logger()


class TechStackParser:
    """Parser for extracting tech stacks and bullet points from text input."""
    
    # Precompiled regex patterns for better performance
    TECH_STACK_PATTERN = re.compile(r"(?P<stack>[A-Za-z0-9_+#\- ]+):\s*(?P<points>(?:• .+\n?)+)")
    BULLET_POINT_PATTERN = re.compile(r"•\s*(.+)")
    
    # Common tech keywords for detection
    TECH_KEYWORDS = frozenset([
        'python', 'javascript', 'java', 'react', 'node', 'aws', 'sql', 'html', 'css',
        'git', 'docker', 'kubernetes', 'angular', 'vue', 'typescript', 'c++', 'c#',
        '.net', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'flutter', 'django',
        'flask', 'spring', 'laravel', 'express', 'mongodb', 'postgresql', 'redis'
    ])
    
    def __init__(self):
        self.tech_exclude_words = PARSING_CONFIG["tech_name_exclude_words"]
        self._cache_hits = 0
        self._cache_misses = 0
        self.sanitizer = InputSanitizer()
    
    def parse_new_format(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Parse the new block format where tech names and bullet points are separated by blank lines.
        
        Format:
            TechName1
            bulletPoint1
            bulletPoint2
            
            TechName2
            bulletPoint1
            bulletPoint2
        
        Args:
            text: Input text to parse
            
        Returns:
            Tuple of (selected_points, tech_stacks_used)
        """
        if not text.strip():
            return [], []
            
        try:
            blocks = self._split_into_blocks(text)
            return self._process_blocks(blocks)
        except Exception as e:
            logger.warning(f"Error parsing new format: {e}")
            return [], []
    
    def _split_into_blocks(self, text: str) -> List[List[str]]:
        """Split input text into blocks separated by blank lines."""
        lines = text.strip().split('\n')
        blocks = []
        current_block = []
        
        for line in lines:
            line = line.strip()
            if not line:  # Empty line - end of block
                if current_block:
                    blocks.append(current_block)
                    current_block = []
            else:
                current_block.append(line)
        
        # Add the last block if it exists
        if current_block:
            blocks.append(current_block)
            
        return blocks
    
    def _process_blocks(self, blocks: List[List[str]]) -> Tuple[List[str], List[str]]:
        """Process blocks to extract tech stacks and bullet points."""
        tech_stacks_used = []
        selected_points = []
        
        for block in blocks:
            if not block:
                continue
                
            first_line = block[0]
            
            if self._looks_like_tech_name(first_line):
                tech_stacks_used.append(first_line)
                # Add remaining lines as bullet points
                selected_points.extend(block[1:])
            else:
                # Treat all lines as bullet points
                selected_points.extend(block)
        
        return selected_points, tech_stacks_used
    
    def parse_original_format(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Parse the original format: TechName: • point1 • point2
        
        Args:
            text: Input text to parse
            
        Returns:
            Tuple of (selected_points, tech_stacks_used)
        """
        if not text.strip():
            return [], []
            
        try:
            matches = list(self.TECH_STACK_PATTERN.finditer(text))
            
            if not matches:
                return [], []
            
            selected_points = []
            tech_stacks_used = []
            
            for match in matches:
                stack = match.group("stack").strip()
                points_block = match.group("points").strip()
                
                # Split bullet points properly - handle both inline and multiline formats
                points = self._extract_bullet_points_from_block(points_block)
                
                if points:  # Only add if we found valid points
                    selected_points.extend(points)
                    tech_stacks_used.append(stack)
            
            return selected_points, tech_stacks_used
            
        except Exception as e:
            logger.warning(f"Error parsing original format: {e}")
            return [], []
    
    @cached(ttl_seconds=3600)  # Cache for 1 hour
    def parse_tech_stacks(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Parse tech stacks from text, trying multiple formats and caching results.
        
        Args:
            text: Input text to parse
            
        Returns:
            Tuple of (selected_points, tech_stacks_used)
        """
        if not text.strip():
            return [], []
            
        # Sanitize input text for security
        text = self.sanitizer.sanitize_text_input(text, max_length=50000)
            
        try:
            # Track cache performance
            self._cache_hits += 1
            
            # First try the new block format
            selected_points, tech_stacks_used = self.parse_new_format(text)
            
            # If successful, return results
            if selected_points and tech_stacks_used:
                logger.debug(f"Successfully parsed {len(tech_stacks_used)} tech stacks using new format")
                return selected_points, tech_stacks_used
            
            # Fallback to original format
            selected_points, tech_stacks_used = self.parse_original_format(text)
            if selected_points and tech_stacks_used:
                logger.debug(f"Successfully parsed {len(tech_stacks_used)} tech stacks using original format")
                return selected_points, tech_stacks_used
            
            # If both formats fail, try to extract any bullet points
            fallback_points = self._extract_fallback_points(text)
            if fallback_points:
                logger.debug(f"Extracted {len(fallback_points)} fallback points")
                return fallback_points, ['General']
                
            return [], []
            
        except Exception as e:
            logger.error(f"Error parsing tech stacks: {e}")
            return [], []
    
    def _extract_bullet_points_from_block(self, points_block: str) -> List[str]:
        """
        Extract individual bullet points from a block of text.
        Handles both inline format ('• point1 • point2') and multiline format.
        
        Args:
            points_block: Block of text containing bullet points
            
        Returns:
            List of individual bullet points
        """
        points = []
        
        # First try to split by bullet markers within the same line
        # Check for various bullet markers, not just standard bullet
        bullet_marker = None
        for marker in ['•', '-', '–', '—', '*', '◦']:
            if marker in points_block:
                bullet_marker = marker
                break
        
        if bullet_marker:
            # Split by detected bullet marker and clean up
            raw_points = points_block.split(bullet_marker)
            for point in raw_points:
                clean_point = point.strip()
                if clean_point:  # Skip empty points
                    points.append(clean_point)
        else:
            # Fallback to regex pattern for multiline format
            regex_points = self.BULLET_POINT_PATTERN.findall(points_block)
            points.extend(regex_points)
        
        return points
    
    def _extract_fallback_points(self, text: str) -> List[str]:
        """Extract any bullet points as fallback when formal parsing fails."""
        points = []
        for line in text.strip().split('\n'):
            line = line.strip()
            if line and any(line.startswith(marker) for marker in ['•', '-', '–', '—', '*', '◦', '◦']):
                # Remove bullet markers including dash variants and add to points
                clean_point = line.lstrip('•-–—*◦◦ \t')
                if clean_point:
                    points.append(clean_point)
        return points
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache performance statistics."""
        cache_info = self.parse_tech_stacks.cache_info()
        return {
            'hits': cache_info.hits,
            'misses': cache_info.misses,
            'current_size': cache_info.currsize,
            'max_size': cache_info.maxsize
        }
    
    def _is_bullet_point_text(self, line: str) -> bool:
        """
        Check if a line looks like a bullet point rather than a tech stack name.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line looks like a bullet point
        """
        return any(line.lower().startswith(word) for word in self.tech_exclude_words)
    
    def _looks_like_tech_name(self, line: str) -> bool:
        """
        Determine if a line looks like a technology name using improved heuristics.
        
        Args:
            line: Text line to check
            
        Returns:
            True if line looks like a technology name
        """
        line_lower = line.lower().strip()
        
        # Skip empty lines
        if not line_lower:
            return False
        
        # If it starts with action words, it's likely a bullet point
        if any(line_lower.startswith(word) for word in self.tech_exclude_words):
            return False
        
        # Check for common bullet markers including dash variants
        if any(line_lower.startswith(marker) for marker in ['•', '-', '–', '—', '*', '◦']):
            return False
        
        # If it contains common tech keywords, likely a tech name
        if any(keyword in line_lower for keyword in self.TECH_KEYWORDS):
            return True
        
        # Short lines without action words are likely tech names
        word_count = len(line.split())
        if word_count <= 3 and not any(char in line for char in '.!?'):
            return True
            
        # Default: treat as tech name if it's very short
        return word_count <= 2


class ManualPointsParser:
    """Parser for handling manually edited points with improved cleaning."""
    
    # Common bullet markers to strip
    BULLET_MARKERS = '•●◦▪▫‣*-'
    
    @staticmethod
    def parse_manual_points(text: str) -> List[str]:
        """
        Parse manually entered points with robust cleaning and validation.
        
        Args:
            text: Manual points text
            
        Returns:
            List of cleaned and validated points
        """
        if not text.strip():
            return []
        
        try:
            points = []
            for line in text.splitlines():
                clean_line = line.strip()
                if not clean_line:
                    continue
                    
                # Remove bullet markers and extra whitespace
                clean_point = clean_line.lstrip(ManualPointsParser.BULLET_MARKERS + ' \t').strip()
                
                # Skip empty points after cleaning
                if clean_point and len(clean_point) > 2:  # Minimum meaningful length
                    points.append(clean_point)
            
            return points
            
        except Exception as e:
            logger.warning(f"Error parsing manual points: {e}")
            return []


class LegacyParser:
    """Parser for legacy format handling with improved performance."""
    
    # Reuse compiled patterns from TechStackParser for consistency
    _TECH_PATTERN = TechStackParser.TECH_STACK_PATTERN
    _BULLET_PATTERN = TechStackParser.BULLET_POINT_PATTERN
    
    @staticmethod
    def extract_points_from_legacy_format(raw_text: str) -> Tuple[List[str], List[str]]:
        """
        Extract points from legacy regex-based format with error handling.
        Used for backward compatibility in preview sections.
        
        Args:
            raw_text: Raw input text
            
        Returns:
            Tuple of (selected_points, tech_stacks_used)
        """
        if not raw_text.strip():
            return [], []
            
        try:
            matches = list(LegacyParser._TECH_PATTERN.finditer(raw_text))
            
            if not matches:
                return [], []
            
            selected_points = []
            tech_stacks_used = []
            
            for match in matches:
                stack = match.group("stack").strip()
                points_block = match.group("points").strip()
                points = LegacyParser._BULLET_PATTERN.findall(points_block)
                
                if points:  # Only include if points were found
                    selected_points.extend(points)
                    tech_stacks_used.append(stack)
            
            return selected_points, tech_stacks_used
            
        except Exception as e:
            logger.warning(f"Error in legacy parsing: {e}")
            return [], []


# Global parser instance for reuse
_global_parser: Optional[TechStackParser] = None

def get_parser() -> TechStackParser:
    """
    Get a singleton instance of the tech stack parser for better performance.
    
    Returns:
        TechStackParser instance
    """
    global _global_parser
    if _global_parser is None:
        _global_parser = TechStackParser()
    return _global_parser


def parse_input_text(text: str, manual_text: str = "") -> Tuple[List[str], List[str]]:
    """
    Main entry point for parsing input text with comprehensive error handling.
    
    Args:
        text: Main input text to parse
        manual_text: Optional manual points text (overrides parsed points)
        
    Returns:
        Tuple of (selected_points, tech_stacks_used)
    """
    if not text.strip() and not manual_text.strip():
        return [], []
        
    try:
        parser = get_parser()
        selected_points, tech_stacks_used = parser.parse_tech_stacks(text)
        
        # Override with manual points if provided
        if manual_text.strip():
            manual_parser = ManualPointsParser()
            manual_points = manual_parser.parse_manual_points(manual_text)
            if manual_points:
                selected_points = manual_points
                logger.debug(f"Using {len(manual_points)} manual points instead of parsed points")
        
        logger.info(f"Parsed {len(selected_points)} points from {len(tech_stacks_used)} tech stacks")
        return selected_points, tech_stacks_used
        
    except Exception as e:
        logger.error(f"Error parsing input text: {e}")
        return [], []


def get_parser_stats() -> Optional[Dict[str, int]]:
    """
    Get parser performance statistics.
    
    Returns:
        Cache statistics dictionary or None if no parser exists
    """
    global _global_parser
    if _global_parser is not None:
        return _global_parser.get_cache_stats()
    return None


