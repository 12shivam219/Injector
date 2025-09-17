"""
Base formatters for document processing.
Handles common formatting operations for documents and runs.
"""
from typing import Any, Dict, Optional
from docx.document import Document as DocumentType
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph
from docx.text.run import Run

class DocumentFormatter:
    """Handles document formatting operations."""
    
    @staticmethod
    def copy_paragraph_formatting(source_para: Paragraph, target_para: Paragraph) -> None:
        """
        Copy all formatting from source paragraph to target paragraph with error handling.
        
        Args:
            source_para: Source paragraph to copy formatting from
            target_para: Target paragraph to apply formatting to
        """
        try:
            # Copy paragraph style
            if source_para.style:
                target_para.style = source_para.style
            
            # Copy paragraph alignment
            if source_para.paragraph_format.alignment is not None:
                target_para.paragraph_format.alignment = source_para.paragraph_format.alignment
            
            # Copy paragraph spacing
            if source_para.paragraph_format.space_before is not None:
                target_para.paragraph_format.space_before = source_para.paragraph_format.space_before
            if source_para.paragraph_format.space_after is not None:
                target_para.paragraph_format.space_after = source_para.paragraph_format.space_after
            if source_para.paragraph_format.line_spacing is not None:
                target_para.paragraph_format.line_spacing = source_para.paragraph_format.line_spacing
            
            # Copy indentation
            if source_para.paragraph_format.left_indent is not None:
                target_para.paragraph_format.left_indent = source_para.paragraph_format.left_indent
            if source_para.paragraph_format.first_line_indent is not None:
                target_para.paragraph_format.first_line_indent = source_para.paragraph_format.first_line_indent
        except Exception as e:
            # Log the error but don't fail the operation
            pass
    
    @staticmethod
    def copy_run_formatting(source_run: Run, target_run: Run) -> None:
        """
        Copy all formatting from source run to target run.
        
        Args:
            source_run: Source run to copy formatting from
            target_run: Target run to apply formatting to
        """
        try:
            # Copy font properties
            target_run.font.name = source_run.font.name
            target_run.font.size = source_run.font.size
            target_run.font.bold = source_run.font.bold
            target_run.font.italic = source_run.font.italic
            target_run.font.underline = source_run.font.underline
            
            # Copy font color
            if source_run.font.color and source_run.font.color.rgb:
                target_run.font.color.rgb = source_run.font.color.rgb
            
            # Copy highlighting if available
            if hasattr(source_run.font, 'highlight_color') and source_run.font.highlight_color:
                target_run.font.highlight_color = source_run.font.highlight_color
        except Exception as e:
            # Log the error but don't fail the operation
            pass


class BaseFormatter:
    """Base class for document formatters."""
    
    def __init__(self):
        self.document_formatter = DocumentFormatter()
    
    def format_document(self, document: DocumentType) -> None:
        """Base method for document formatting."""
        pass

class ListFormatterMixin:
    """Mixin class providing list formatting functionality."""
    
    @staticmethod
    def _apply_list_formatting(paragraph: Paragraph, list_format: Dict[str, Any]) -> None:
        """
        Apply Word list formatting to paragraph.
        
        Args:
            paragraph: Paragraph to format
            list_format: Dictionary containing list formatting information
        """
        try:
            num_id = list_format.get('numId')
            ilvl = list_format.get('ilvl', 0)
            
            if num_id is not None:
                # Create numbering properties XML
                num_pr = OxmlElement('w:numPr')
                
                # Add list level
                ilvl_elem = OxmlElement('w:ilvl')
                ilvl_elem.set(qn('w:val'), str(ilvl))
                
                # Add numbering ID
                num_id_elem = OxmlElement('w:numId')
                num_id_elem.set(qn('w:val'), str(num_id))
                
                # Assemble the XML structure
                num_pr.append(ilvl_elem)
                num_pr.append(num_id_elem)
                
                # Get or create paragraph properties
                p_pr = paragraph._element.get_or_add_pPr()
                
                # Remove existing numbering properties if any
                existing_num_pr = p_pr.find(qn('w:numPr'))
                if existing_num_pr is not None:
                    p_pr.remove(existing_num_pr)
                
                # Add new numbering properties
                p_pr.append(num_pr)
        except Exception as e:
            # Log the error but don't fail the operation
            pass


