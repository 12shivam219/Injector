"""
Document processing module for Resume Customizer application.
Handles Word document operations, project detection, and point insertion.
"""

import time
from typing import List, Dict, Any, Optional, Tuple
from io import BytesIO
from docx import Document
from docx.text.paragraph import Paragraph

import logging
from infrastructure.utilities.logger import get_logger
from infrastructure.utilities.structured_logger import get_structured_logger
from ..detectors.project_detector import ProjectDetector, ProjectInfo
from ..formatters.bullet_formatter import BulletFormatter, BulletFormatting
from .point_distributor import PointDistributor

# Initialize logger with fallback
try:
    logger = get_logger()
except Exception:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

try:
    structured_logger = get_structured_logger("document_processor")
except Exception:
    structured_logger = logging.getLogger("document_processor")
    structured_logger.setLevel(logging.INFO)


class DocumentProcessor:
    """Handles document processing operations with enhanced formatting preservation."""
    
    def __init__(self):
        self.project_detector = ProjectDetector()
        self.bullet_formatter = BulletFormatter()
        self.point_distributor = PointDistributor()
        self._document_bullet_marker_cache = {}
    
    def process_document(self, file_content: BytesIO, parsed_points: Tuple[List[str], List[str]]) -> BytesIO:
        """
        Process a document by adding tech stack points to projects.
        
        Args:
            file_content: Document content as BytesIO
            parsed_points: Tuple of (selected_points, tech_stacks_used)
            
        Returns:
            Processed document as BytesIO
        """
        try:
            # Load document
            doc = Document(file_content)
            
            # Detect document-wide bullet marker for consistency
            document_marker = self.bullet_formatter.detect_document_bullet_marker(doc)
            logger.info(f"Detected document bullet marker: '{document_marker}'")
            
            # Find projects
            projects = self.project_detector.find_projects(doc)
            if not projects:
                raise ValueError("No projects found in document")
            
            # Distribute points
            distribution_result = self.point_distributor.distribute_points(projects, parsed_points)
            
            # Add points to projects with consistent formatting
            total_added = 0
            for project_name, points in distribution_result.distribution.items():
                project = next((p for p in projects if p.name == project_name), None)
                if project:
                    added = self._add_points_to_project(doc, project, points, document_marker)
                    total_added += added
            
            # Save to buffer
            output_buffer = BytesIO()
            doc.save(output_buffer)
            output_buffer.seek(0)
            
            logger.info(f"Document processed successfully, added {total_added} points")
            return output_buffer
            
        except Exception as e:
            logger.error(f"Document processing failed: {e}")
            raise
    
    def _add_points_to_project(self, doc: Document, project: ProjectInfo, 
                              points: List[Dict[str, Any]], document_marker: str) -> int:
        """
        Add points to a specific project with consistent formatting.
        
        Args:
            doc: Document to modify
            project: Project information
            points: Points to add
            document_marker: Document-wide bullet marker to use
            
        Returns:
            Number of points added
        """
        if not points:
            return 0
        
        try:
            # Find the insertion point (after existing responsibilities)
            insertion_index = self._find_insertion_point(doc, project)
            
            # Get existing bullet formatting from the project
            existing_formatting = self._get_project_bullet_formatting(doc, project, document_marker)
            
            # Add each point with consistent formatting
            points_added = 0
            for i, point_data in enumerate(points):
                point_text = point_data.get('text', str(point_data))
                
                # Insert new paragraph at the correct position
                new_para = doc.paragraphs[insertion_index + i]._element.getparent().insert(
                    insertion_index + i + 1,
                    doc.add_paragraph()._element
                )
                new_paragraph = Paragraph(new_para, doc.paragraphs[0]._parent)
                
                # Apply consistent formatting
                self.bullet_formatter.apply_formatting(
                    new_paragraph, 
                    existing_formatting, 
                    point_text
                )
                
                points_added += 1
            
            logger.info(f"Added {points_added} points to project '{project.name}' with marker '{document_marker}'")
            return points_added
            
        except Exception as e:
            logger.error(f"Failed to add points to project '{project.name}': {e}")
            return 0
    
    def _find_insertion_point(self, doc: Document, project: ProjectInfo) -> int:
        """
        Find the correct insertion point for new bullet points.
        
        Args:
            doc: Document to search
            project: Project information
            
        Returns:
            Index where new points should be inserted
        """
        # Start from the end of the project's responsibilities section
        insertion_index = project.end_index
        
        # Look for the last bullet point in this project
        for i in range(project.end_index, project.start_index - 1, -1):
            if i < len(doc.paragraphs):
                para_text = doc.paragraphs[i].text.strip()
                if self.bullet_formatter._is_bullet_point(para_text):
                    insertion_index = i
                    break
        
        return insertion_index
    
    def _get_project_bullet_formatting(self, doc: Document, project: ProjectInfo, 
                                     document_marker: str) -> BulletFormatting:
        """
        Get bullet formatting from existing project bullets or create consistent formatting.
        
        Args:
            doc: Document to analyze
            project: Project information
            document_marker: Document-wide bullet marker
            
        Returns:
            BulletFormatting object with consistent formatting
        """
        # Try to extract formatting from existing bullets in this project
        for i in range(project.start_index, min(project.end_index + 1, len(doc.paragraphs))):
            para = doc.paragraphs[i]
            if self.bullet_formatter._is_bullet_point(para.text):
                formatting = self.bullet_formatter.extract_formatting(doc, i)
                if formatting:
                    # Ensure the marker matches the document-wide marker
                    formatting.bullet_marker = document_marker
                    logger.debug(f"Extracted formatting from project '{project.name}' with marker '{document_marker}'")
                    return formatting
        
        # No existing bullets found, create default formatting with document marker
        logger.debug(f"No existing bullets found in project '{project.name}', creating default formatting with marker '{document_marker}'")
        return BulletFormatting(
            runs_formatting=[{
                'text': '',
                'font_name': None,
                'font_size': None,
                'bold': None,
                'italic': None,
                'underline': None,
                'color': None
            }],
            paragraph_formatting={},
            style='Normal',
            bullet_marker=document_marker,
            bullet_separator=' ',
            list_format={
                'ilvl': 0,
                'numId': 1,
                'style': 'List Bullet',
                'indent': 0,
                'is_list': True
            }
        )


class FileProcessor:
    """Handles file operations and memory management."""
    
    def __init__(self):
        self.processed_files = {}
    
    def ensure_file_has_name(self, file_obj, filename: str):
        """Ensure file object has a name attribute."""
        if not hasattr(file_obj, 'name'):
            file_obj.name = filename
        return file_obj
    
    def cleanup_memory(self):
        """Clean up processed file cache."""
        self.processed_files.clear()


# Global document processor instance
_document_processor = None

def get_document_processor() -> DocumentProcessor:
    """Get singleton document processor instance."""
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor