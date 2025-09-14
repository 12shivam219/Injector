"""
Email template management module for Resume Customizer application.
"""

import os
import json
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from string import Template

from infrastructure.utilities.logger import get_logger
from infrastructure.utilities.structured_logger import get_structured_logger
from infrastructure.security.security_enhancements import InputSanitizer

logger = get_logger()
structured_logger = get_structured_logger("email_templates")


@dataclass
class EmailTemplate:
    """Email template definition."""
    id: str
    name: str
    subject_template: str
    body_template: str
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def render(self, data: Dict[str, Any]) -> Tuple[str, str]:
        """Render the template with provided data."""
        sanitizer = InputSanitizer()
        safe_data = {k: sanitizer.sanitize(str(v)) for k, v in data.items()}
        
        subject = Template(self.subject_template).safe_substitute(safe_data)
        body = Template(self.body_template).safe_substitute(safe_data)
        
        return subject, body


class TemplateManager:
    """Manages email templates for the application."""
    _instance = None
    _lock = threading.Lock()
    
    def __init__(self):
        self.templates: Dict[str, EmailTemplate] = {}
        self.default_template_path = Path("templates")
        self._load_default_templates()
    
    @classmethod
    def get_instance(cls) -> 'TemplateManager':
        """Get or create singleton instance."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance
    
    def _load_default_templates(self) -> None:
        """Load built-in email templates."""
        try:
            default_templates = {
                "resume_success": EmailTemplate(
                    id="resume_success",
                    name="Resume Processing Success",
                    subject_template="Your Resume: $filename has been processed",
                    body_template="""
                    Hello $name,

                    Your resume '$filename' has been successfully processed.
                    You can now download the customized version.

                    Processing Details:
                    - Date: $date
                    - Status: $status
                    - Format: $format

                    Best regards,
                    Resume Customizer Team
                    """
                ),
                "error_notification": EmailTemplate(
                    id="error_notification",
                    name="Processing Error Notification",
                    subject_template="Error Processing Resume: $filename",
                    body_template="""
                    Hello $name,

                    We encountered an error while processing your resume '$filename'.

                    Error Details:
                    - Error Type: $error_type
                    - Time: $time
                    - Status: $status

                    Our team has been notified and will investigate the issue.

                    Best regards,
                    Resume Customizer Team
                    """
                )
            }
            self.templates.update(default_templates)
            logger.info("Default email templates loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading default templates: {str(e)}")
            raise
    
    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get a template by ID."""
        return self.templates.get(template_id)
    
    def add_template(self, template: EmailTemplate) -> None:
        """Add a new template."""
        if template.id in self.templates:
            raise ValueError(f"Template with ID {template.id} already exists")
        self.templates[template.id] = template
        logger.info(f"Added new template: {template.id}")
    
    def update_template(self, template: EmailTemplate) -> None:
        """Update an existing template."""
        if template.id not in self.templates:
            raise ValueError(f"Template with ID {template.id} does not exist")
        template.updated_at = datetime.now()
        self.templates[template.id] = template
        logger.info(f"Updated template: {template.id}")
    
    def delete_template(self, template_id: str) -> None:
        """Delete a template."""
        if template_id not in self.templates:
            raise ValueError(f"Template with ID {template_id} does not exist")
        del self.templates[template_id]
        logger.info(f"Deleted template: {template_id}")
    
    def list_templates(self) -> List[EmailTemplate]:
        """Get all available templates."""
        return list(self.templates.values())


def get_template_manager() -> TemplateManager:
    """Get the singleton instance of TemplateManager."""
    return TemplateManager.get_instance()