"""
Restricted Text Parser for Resume Customizer application.
Only accepts 3 specific formats as defined by user requirements.
"""

import re
from typing import List, Tuple, Optional, Dict
import logging
from infrastructure.utilities.logger import get_logger
from infrastructure.security.security_enhancements import InputSanitizer

# Initialize logger with fallback
try:
    logger = get_logger()
except Exception:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)


class RestrictedFormatError(Exception):
    """Exception raised when input doesn't match any of the 3 supported formats."""
    pass


class RestrictedTechStackParser:
    """Parser that only accepts exactly 3 specified input formats."""
    
    def __init__(self):
        self.sanitizer = InputSanitizer()
        self.supported_formats = self._get_format_examples()
    
    def _get_format_examples(self) -> str:
        """Get formatted examples of the 3 supported formats for error messages."""
        return """
Please use one of these 3 supported formats:

FORMAT 1: Tech Stack (no colon) + Tabbed Bullet Points
Java
•       Point with tab indentation
•       Another point with tab
•       Third point with tab

FORMAT 2: Tech Stack with Colon + Tabbed Bullet Points  
Java:
•       Point with tab indentation
•       Another point with tab
•       Third point with tab

FORMAT 3: Tech Stack (no colon) + Regular Bullet Points
Java
• Point with regular bullet (no tab)
• Another point with regular bullet
• Third point with regular bullet

Note: You can mix different formats in the same input.
"""

    def parse_restricted_format(self, text: str) -> Tuple[List[str], List[str]]:
        """
        Parse text using only the 3 restricted formats.
        
        Args:
            text: Input text to parse
            
        Returns:
            Tuple of (selected_points, tech_stacks_used)
            
        Raises:
            RestrictedFormatError: If input doesn't match supported formats
        """
        if not text.strip():
            return [], []
            
        # Sanitize input text for security
        text = self.sanitizer.sanitize_text_input(text, max_length=50000)
        
        try:
            # Split input into blocks separated by blank lines
            blocks = self._split_into_blocks(text)
            
            if not blocks:
                return [], []
            
            # Validate all blocks match one of the 3 formats
            self._validate_all_blocks(blocks)
            
            # Process valid blocks
            return self._process_validated_blocks(blocks)
            
        except RestrictedFormatError:
            raise
        except Exception as e:
            logger.error(f"Error parsing restricted format: {e}")
            raise RestrictedFormatError(f"Parsing error: {str(e)}\n{self.supported_formats}")
    
    def _split_into_blocks(self, text: str) -> List[List[str]]:
        """Split input text into blocks separated by blank lines."""
        lines = text.strip().split('\n')
        blocks = []
        current_block = []
        
        for line in lines:
            # Keep original spacing but strip trailing whitespace
            line = line.rstrip()
            if not line.strip():  # Empty line - end of block
                if current_block:
                    blocks.append(current_block)
                    current_block = []
            else:
                current_block.append(line)
        
        # Add the last block if it exists
        if current_block:
            blocks.append(current_block)
            
        return blocks
    
    def _validate_all_blocks(self, blocks: List[List[str]]) -> None:
        """
        Validate that all blocks match one of the 3 supported formats.
        
        Raises:
            RestrictedFormatError: If any block doesn't match supported formats
        """
        for i, block in enumerate(blocks):
            if not self._is_valid_block_format(block):
                invalid_content = '\n'.join(block[:3])  # Show first 3 lines
                if len(block) > 3:
                    invalid_content += '\n...'
                    
                raise RestrictedFormatError(
                    f"Block {i+1} doesn't match any supported format:\n\n{invalid_content}\n\n{self.supported_formats}"
                )
    
    def _is_valid_block_format(self, block: List[str]) -> bool:
        """Check if a block matches one of the 3 supported formats."""
        if len(block) < 2:  # Need at least tech name + 1 bullet point
            return False
        
        first_line = block[0].strip()
        remaining_lines = block[1:]
        
        # Check Format 1: Tech Stack (no colon) + Tabbed bullets
        if self._is_format_1(first_line, remaining_lines):
            return True
            
        # Check Format 2: Tech Stack with colon + Tabbed bullets
        if self._is_format_2(first_line, remaining_lines):
            return True
            
        # Check Format 3: Tech Stack (no colon) + Regular bullets
        if self._is_format_3(first_line, remaining_lines):
            return True
        
        return False
    
    def _is_format_1(self, first_line: str, bullet_lines: List[str]) -> bool:
        """Check Format 1: Tech Stack (no colon) + Tabbed bullet points."""
        # Tech stack line should not end with colon and not start with bullet
        if first_line.endswith(':') or self._starts_with_bullet(first_line):
            return False
        
        # All bullet lines must be tabbed bullet points
        return all(self._is_tabbed_bullet(line) for line in bullet_lines)
    
    def _is_format_2(self, first_line: str, bullet_lines: List[str]) -> bool:
        """Check Format 2: Tech Stack with colon + Tabbed bullet points."""
        # Tech stack line should end with colon and not start with bullet
        if not first_line.endswith(':') or self._starts_with_bullet(first_line):
            return False
        
        # All bullet lines must be tabbed bullet points
        return all(self._is_tabbed_bullet(line) for line in bullet_lines)
    
    def _is_format_3(self, first_line: str, bullet_lines: List[str]) -> bool:
        """Check Format 3: Tech Stack (no colon) + Regular bullet points."""
        # Tech stack line should not end with colon and not start with bullet
        if first_line.endswith(':') or self._starts_with_bullet(first_line):
            return False
        
        # All bullet lines must be regular bullet points (no tabs)
        return all(self._is_regular_bullet(line) for line in bullet_lines)
    
    def _starts_with_bullet(self, line: str) -> bool:
        """Check if line starts with a bullet marker."""
        stripped = line.strip()
        return stripped.startswith('•') or stripped.startswith('*') or stripped.startswith('-')
    
    def _is_tabbed_bullet(self, line: str) -> bool:
        """Check if line is a tabbed bullet point (Format 1 & 2)."""
        # Must start with bullet symbol followed by tab or multiple spaces
        if not line.startswith('•'):
            return False
        
        # After bullet, there should be tab or multiple spaces (≥2)
        after_bullet = line[1:]
        if after_bullet.startswith('\t'):
            return True
        
        # Check for multiple spaces (flexible - accept 2 or more spaces)
        space_count = 0
        for char in after_bullet:
            if char == ' ':
                space_count += 1
            else:
                break
        
        # Accept 2 or more spaces as "tabbed"
        return space_count >= 2
    
    def _is_regular_bullet(self, line: str) -> bool:
        """Check if line is a regular bullet point (Format 3)."""
        stripped = line.strip()
        
        # Must start with bullet symbol
        if not stripped.startswith('•'):
            return False
        
        # After bullet, should have exactly one space (not tab, not multiple spaces)
        if len(line) < 2 or line[0] != '•':
            return False
        
        after_bullet = line[1:]
        
        # Should not start with tab
        if after_bullet.startswith('\t'):
            return False
        
        # Should start with exactly one space
        if not after_bullet.startswith(' '):
            return False
        
        # Should not start with multiple spaces
        if len(after_bullet) > 1 and after_bullet[1] == ' ':
            return False
        
        return True
    
    def _process_validated_blocks(self, blocks: List[List[str]]) -> Tuple[List[str], List[str]]:
        """Process validated blocks to extract tech stacks and bullet points."""
        tech_stacks_used = []
        selected_points = []
        
        for block in blocks:
            if len(block) < 2:
                continue
                
            # Extract tech stack name (remove colon if present)
            tech_name = block[0].strip().rstrip(':')
            tech_stacks_used.append(tech_name)
            
            # Extract bullet points (remove bullet markers and clean)
            for line in block[1:]:
                clean_point = self._extract_bullet_content(line)
                if clean_point:
                    selected_points.append(clean_point)
        
        logger.info(f"Successfully parsed {len(selected_points)} points from {len(tech_stacks_used)} tech stacks using restricted format")
        return selected_points, tech_stacks_used
    
    def _extract_bullet_content(self, line: str) -> str:
        """Extract the content from a bullet point line."""
        # Remove bullet marker and any leading whitespace/tabs
        if line.startswith('•'):
            content = line[1:].lstrip(' \t')
            return content.strip()
        return line.strip()


class RestrictedParser:
    """Main interface for the restricted parser."""
    
    def __init__(self):
        self.parser = RestrictedTechStackParser()
    
    def parse_input_text(self, text: str, manual_text: str = "") -> Tuple[List[str], List[str]]:
        """
        Main entry point for parsing input text with restricted format validation.
        
        Args:
            text: Main input text to parse
            manual_text: Optional manual points text (currently not used in restricted mode)
            
        Returns:
            Tuple of (selected_points, tech_stacks_used)
            
        Raises:
            RestrictedFormatError: If input doesn't match supported formats
        """
        if not text.strip():
            if manual_text.strip():
                raise RestrictedFormatError(
                    f"Manual text input is not supported in restricted mode.\n{self.parser.supported_formats}"
                )
            return [], []
        
        return self.parser.parse_restricted_format(text)


# Global restricted parser instance
_restricted_parser: Optional[RestrictedParser] = None

def get_restricted_parser() -> RestrictedParser:
    """Get singleton instance of restricted parser."""
    global _restricted_parser
    if _restricted_parser is None:
        _restricted_parser = RestrictedParser()
    return _restricted_parser


def parse_input_text_restricted(text: str, manual_text: str = "") -> Tuple[List[str], List[str]]:
    """
    Main entry point for restricted parsing.
    
    Args:
        text: Main input text to parse
        manual_text: Optional manual points text (not used in restricted mode)
        
    Returns:
        Tuple of (selected_points, tech_stacks_used)
        
    Raises:
        RestrictedFormatError: If input doesn't match supported formats
    """
    parser = get_restricted_parser()
    return parser.parse_input_text(text, manual_text)