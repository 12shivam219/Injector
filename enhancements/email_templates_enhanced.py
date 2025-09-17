"""
Advanced email template system for Resume Customizer application.
Provides multiple templates, personalization, and professional formatting.
"""

import os
import json
import threading
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from string import Template
import streamlit as st

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
    category: str
    description: str
    required_variables: List[str] = field(default_factory=list)
    optional_variables: List[str] = field(default_factory=list)
    preview_variables: Dict[str, str] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    
    def render(self, variables: Dict[str, str]) -> Tuple[str, str]:
        """
        Render template with variables.
        
        Args:
            variables: Variables to substitute in template
            
        Returns:
            Tuple of (subject, body)
        """
        try:
            subject_template = Template(self.subject_template)
            body_template = Template(self.body_template)
            
            # Sanitize variables
            sanitizer = InputSanitizer()
            safe_variables = {
                key: sanitizer.sanitize_text_input(str(value), max_length=500)
                for key, value in variables.items()
            }
            
            # Add default variables if missing
            defaults = {
                'current_date': datetime.now().strftime('%B %d, %Y'),
                'current_year': str(datetime.now().year),
                'sender_name': safe_variables.get('applicant_name', 'Job Applicant')
            }
            
            for key, value in defaults.items():
                if key not in safe_variables:
                    safe_variables[key] = value
            
            subject = subject_template.safe_substitute(**safe_variables)
            body = body_template.safe_substitute(**safe_variables)
            
            return subject, body
            
        except Exception as e:
            logger.error(f"Template rendering failed: {e}")
            return f"Resume from {variables.get('applicant_name', 'Applicant')}", "Please find my resume attached."


class EmailTemplateManager:
    """
    Advanced email template manager with multiple templates and personalization.
    """
    
    def __init__(self, templates_dir: Optional[str] = None):
        self.templates_dir = templates_dir or "email_templates"
        self.templates: Dict[str, EmailTemplate] = {}
        self._lock = threading.RLock()
        self.sanitizer = InputSanitizer()
        
        # Ensure templates directory exists
        Path(self.templates_dir).mkdir(exist_ok=True)
        
        # Load built-in templates
        self._load_builtin_templates()
        
        # Load custom templates
        self._load_custom_templates()
        
        structured_logger.info(
            f"Email template manager initialized with {len(self.templates)} templates",
            operation="template_manager_init",
            template_count=len(self.templates)
        )
    
    def _load_builtin_templates(self):
        """Load built-in email templates."""
        builtin_templates = [
            EmailTemplate(
                id="professional_standard",
                name="Professional Standard",
                category="Professional",
                description="A formal, professional email template suitable for corporate positions",
                subject_template="Application for ${position_title} - ${applicant_name}",
                body_template="""Dear Hiring Manager,

I am writing to express my strong interest in the ${position_title} position at ${company_name}. With my background in ${field_of_expertise}, I believe I would be a valuable addition to your team.

Please find my resume attached for your review. I would welcome the opportunity to discuss how my skills and experience align with your requirements.

Key highlights from my background:
• ${experience_years}+ years of experience in ${field_of_expertise}
• Proven track record in ${key_achievements}
• Strong expertise in ${technical_skills}

I look forward to hearing from you and would appreciate the opportunity to discuss this position further.

Best regards,
${applicant_name}
${phone_number}
${email_address}""",
                required_variables=["applicant_name", "position_title", "company_name"],
                optional_variables=["field_of_expertise", "experience_years", "key_achievements", "technical_skills", "phone_number", "email_address"],
                preview_variables={
                    "applicant_name": "John Smith",
                    "position_title": "Software Engineer",
                    "company_name": "TechCorp Inc.",
                    "field_of_expertise": "software development",
                    "experience_years": "5",
                    "key_achievements": "leading development teams and delivering projects on time",
                    "technical_skills": "Python, JavaScript, and cloud technologies",
                    "phone_number": "(555) 123-4567",
                    "email_address": "john.smith@email.com"
                },
                tags=["professional", "corporate", "formal"]
            ),
            
            EmailTemplate(
                id="creative_enthusiastic",
                name="Creative & Enthusiastic",
                category="Creative",
                description="An engaging, creative template for design, marketing, or creative roles",
                subject_template="🎨 Excited to Apply: ${position_title} at ${company_name} - ${applicant_name}",
                body_template="""Hello ${hiring_manager_name}!

I hope this email finds you well! I'm thrilled to submit my application for the ${position_title} role at ${company_name}. 

Your company's mission to ${company_mission} resonates deeply with my passion for ${passion_area}. I'm excited about the possibility of contributing my ${unique_skills} to help ${company_name} achieve even greater success.

✨ What I bring to the table:
• ${experience_years} years of creative experience in ${industry}
• A fresh perspective on ${specialization}
• Proven ability to ${key_accomplishment}
• Enthusiasm for ${company_values}

I've attached my resume and would love to chat about how we can create something amazing together!

Looking forward to connecting,
${applicant_name}
${contact_info}

P.S. I'm particularly excited about ${specific_project} - I'd love to discuss my ideas for this!""",
                required_variables=["applicant_name", "position_title", "company_name"],
                optional_variables=["hiring_manager_name", "company_mission", "passion_area", "unique_skills", "experience_years", "industry", "specialization", "key_accomplishment", "company_values", "contact_info", "specific_project"],
                preview_variables={
                    "applicant_name": "Sarah Creative",
                    "position_title": "UX Designer",
                    "company_name": "Design Studio",
                    "hiring_manager_name": "Alex Johnson",
                    "company_mission": "create beautiful, user-centered designs",
                    "passion_area": "creating intuitive user experiences",
                    "unique_skills": "user research and design thinking expertise",
                    "experience_years": "4",
                    "industry": "digital design",
                    "specialization": "mobile app design",
                    "key_accomplishment": "increase user engagement by 40%",
                    "company_values": "innovation and user-centric design",
                    "contact_info": "sarah.creative@email.com | Portfolio: sarah-designs.com",
                    "specific_project": "the new mobile app redesign project"
                },
                tags=["creative", "enthusiastic", "design", "marketing"]
            ),
            
            EmailTemplate(
                id="technical_detailed",
                name="Technical & Detailed",
                category="Technical",
                description="A detailed technical template for engineering and IT positions",
                subject_template="Technical Application: ${position_title} - ${applicant_name}",
                body_template="""Dear ${hiring_manager_name},

I am submitting my application for the ${position_title} position at ${company_name}. As a ${current_title} with ${experience_years} years of experience, I am excited about the opportunity to contribute to your team's technical objectives.

TECHNICAL EXPERTISE:
• Programming Languages: ${programming_languages}
• Frameworks & Technologies: ${frameworks}
• Cloud Platforms: ${cloud_platforms}
• Database Systems: ${databases}

RELEVANT EXPERIENCE:
• ${key_project_1}
• ${key_project_2}
• ${key_project_3}

ACHIEVEMENTS:
• ${technical_achievement_1}
• ${technical_achievement_2}
• ${performance_improvement}

I am particularly interested in ${specific_interest} at ${company_name} and believe my experience with ${relevant_technology} would be valuable for your team.

Please find my detailed resume attached. I would appreciate the opportunity to discuss how my technical background aligns with your requirements.

Technical regards,
${applicant_name}
${professional_contact}
GitHub: ${github_profile}
LinkedIn: ${linkedin_profile}""",
                required_variables=["applicant_name", "position_title", "company_name", "current_title", "experience_years"],
                optional_variables=["hiring_manager_name", "programming_languages", "frameworks", "cloud_platforms", "databases", "key_project_1", "key_project_2", "key_project_3", "technical_achievement_1", "technical_achievement_2", "performance_improvement", "specific_interest", "relevant_technology", "professional_contact", "github_profile", "linkedin_profile"],
                preview_variables={
                    "applicant_name": "Alex Developer",
                    "position_title": "Senior Software Engineer",
                    "company_name": "TechCorp",
                    "current_title": "Software Engineer",
                    "experience_years": "7",
                    "hiring_manager_name": "Engineering Manager",
                    "programming_languages": "Python, Java, JavaScript, Go",
                    "frameworks": "Django, React, Spring Boot, Node.js",
                    "cloud_platforms": "AWS, Azure, Google Cloud Platform",
                    "databases": "PostgreSQL, MongoDB, Redis, Elasticsearch",
                    "key_project_1": "Led migration of legacy monolith to microservices architecture",
                    "key_project_2": "Implemented CI/CD pipeline reducing deployment time by 75%",
                    "key_project_3": "Built real-time analytics platform handling 1M+ events/day",
                    "technical_achievement_1": "Optimized database queries improving performance by 60%",
                    "technical_achievement_2": "Mentored junior developers and conducted technical interviews",
                    "performance_improvement": "Reduced system latency from 200ms to 50ms",
                    "specific_interest": "the scalability challenges in handling high-traffic applications",
                    "relevant_technology": "distributed systems and event-driven architecture",
                    "professional_contact": "alex.developer@email.com | (555) 987-6543",
                    "github_profile": "github.com/alexdev",
                    "linkedin_profile": "linkedin.com/in/alexdeveloper"
                },
                tags=["technical", "engineering", "detailed", "IT"]
            ),
            
            EmailTemplate(
                id="executive_strategic",
                name="Executive & Strategic",
                category="Executive",
                description="A strategic template for senior executive and leadership positions",
                subject_template="Executive Application: ${position_title} - Strategic Leadership Opportunity",
                body_template="""Dear ${board_member} and Executive Search Committee,

I am writing to express my interest in the ${position_title} role at ${company_name}. With over ${experience_years} years of executive leadership experience, I am excited about the opportunity to drive strategic growth and operational excellence at your organization.

EXECUTIVE SUMMARY:
My career has been defined by transforming organizations through strategic vision, operational optimization, and team leadership. At ${current_company}, I ${major_achievement}, resulting in ${business_impact}.

STRATEGIC CONTRIBUTIONS:
• Revenue Growth: ${revenue_achievement}
• Operational Efficiency: ${efficiency_improvement}
• Market Expansion: ${market_expansion}
• Team Development: ${leadership_achievement}

RELEVANT EXPERIENCE:
• ${experience_highlight_1}
• ${experience_highlight_2}
• ${experience_highlight_3}

I am particularly drawn to ${company_name}'s commitment to ${company_vision} and believe my proven track record in ${expertise_area} would be instrumental in achieving your strategic objectives.

I would welcome the opportunity to discuss how my executive experience can contribute to ${company_name}'s continued success and growth.

With executive regards,

${applicant_name}
${title}
${executive_contact}

Confidential References Available Upon Request""",
                required_variables=["applicant_name", "position_title", "company_name", "experience_years"],
                optional_variables=["board_member", "current_company", "major_achievement", "business_impact", "revenue_achievement", "efficiency_improvement", "market_expansion", "leadership_achievement", "experience_highlight_1", "experience_highlight_2", "experience_highlight_3", "company_vision", "expertise_area", "title", "executive_contact"],
                preview_variables={
                    "applicant_name": "Patricia Executive",
                    "position_title": "Chief Technology Officer",
                    "company_name": "InnovateCorp",
                    "experience_years": "15",
                    "board_member": "Board Members",
                    "current_company": "TechGlobal Inc.",
                    "major_achievement": "led the digital transformation initiative",
                    "business_impact": "$50M+ in cost savings and 200% increase in operational efficiency",
                    "revenue_achievement": "Increased revenue by 300% over 4 years",
                    "efficiency_improvement": "Streamlined operations reducing costs by 40%",
                    "market_expansion": "Successfully expanded into 12 new markets",
                    "leadership_achievement": "Built and led cross-functional teams of 200+ professionals",
                    "experience_highlight_1": "Spearheaded merger integration of 3 companies worth $2B+",
                    "experience_highlight_2": "Launched innovative product line generating $100M+ ARR",
                    "experience_highlight_3": "Established strategic partnerships with Fortune 500 companies",
                    "company_vision": "innovation and sustainable growth",
                    "expertise_area": "strategic planning and technology leadership",
                    "title": "Chief Technology Officer",
                    "executive_contact": "patricia.exec@email.com | Executive Assistant: (555) 111-2222"
                },
                tags=["executive", "strategic", "leadership", "senior"]
            )
        ]
        
        for template in builtin_templates:
            self.templates[template.id] = template
    
    def _load_custom_templates(self):
        """Load custom templates from files."""
        try:
            templates_path = Path(self.templates_dir)
            if templates_path.exists():
                for template_file in templates_path.glob("*.json"):
                    try:
                        with open(template_file, 'r', encoding='utf-8') as f:
                            template_data = json.load(f)
                        
                        template = EmailTemplate(**template_data)
                        self.templates[template.id] = template
                        
                        structured_logger.debug(
                            f"Loaded custom template: {template.name}",
                            operation="load_custom_template",
                            template_id=template.id
                        )
                        
                    except Exception as e:
                        logger.warning(f"Failed to load template from {template_file}: {e}")
        
        except Exception as e:
            logger.warning(f"Failed to load custom templates: {e}")
    
    def get_templates(self, category: Optional[str] = None) -> List[EmailTemplate]:
        """
        Get available templates, optionally filtered by category.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of matching templates
        """
        with self._lock:
            templates = list(self.templates.values())
            
            if category:
                templates = [t for t in templates if t.category.lower() == category.lower()]
            
            # Sort by category, then by name
            templates.sort(key=lambda t: (t.category, t.name))
            return templates
    
    def get_template(self, template_id: str) -> Optional[EmailTemplate]:
        """Get specific template by ID."""
        with self._lock:
            return self.templates.get(template_id)
    
    def get_categories(self) -> List[str]:
        """Get all available template categories."""
        with self._lock:
            categories = {template.category for template in self.templates.values()}
            return sorted(categories)
    
    def generate_email(self, 
                      template_id: str, 
                      variables: Dict[str, str],
                      validate_required: bool = True) -> Optional[Tuple[str, str]]:
        """
        Generate email from template.
        
        Args:
            template_id: ID of template to use
            variables: Variables for template substitution
            validate_required: Whether to validate required variables
            
        Returns:
            Tuple of (subject, body) or None if template not found
        """
        with self._lock:
            template = self.templates.get(template_id)
            if not template:
                logger.error(f"Template {template_id} not found")
                return None
            
            # Validate required variables if requested
            if validate_required:
                missing_vars = [var for var in template.required_variables if var not in variables]
                if missing_vars:
                    logger.warning(f"Missing required variables: {missing_vars}")
                    # Don't fail, just log warning
            
            try:
                subject, body = template.render(variables)
                
                structured_logger.info(
                    f"Email generated using template: {template.name}",
                    operation="email_generation",
                    template_id=template_id,
                    template_name=template.name
                )
                
                return subject, body
                
            except Exception as e:
                logger.error(f"Email generation failed: {e}")
                return None
    
    def preview_template(self, template_id: str) -> Optional[Tuple[str, str]]:
        """
        Generate preview of template using preview variables.
        
        Args:
            template_id: ID of template to preview
            
        Returns:
            Tuple of (subject, body) for preview
        """
        with self._lock:
            template = self.templates.get(template_id)
            if not template:
                return None
            
            return template.render(template.preview_variables)
    
    def add_custom_template(self, template: EmailTemplate) -> bool:
        """
        Add a custom template.
        
        Args:
            template: Template to add
            
        Returns:
            True if template was added successfully
        """
        with self._lock:
            try:
                # Validate template
                if not template.id or not template.name:
                    logger.error("Template must have ID and name")
                    return False
                
                # Save to file
                template_file = Path(self.templates_dir) / f"{template.id}.json"
                with open(template_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'id': template.id,
                        'name': template.name,
                        'subject_template': template.subject_template,
                        'body_template': template.body_template,
                        'category': template.category,
                        'description': template.description,
                        'required_variables': template.required_variables,
                        'optional_variables': template.optional_variables,
                        'preview_variables': template.preview_variables,
                        'tags': template.tags
                    }, indent=2)
                
                # Add to memory
                self.templates[template.id] = template
                
                structured_logger.info(
                    f"Custom template added: {template.name}",
                    operation="add_custom_template",
                    template_id=template.id
                )
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to add custom template: {e}")
                return False
    
    def delete_custom_template(self, template_id: str) -> bool:
        """
        Delete a custom template.
        
        Args:
            template_id: ID of template to delete
            
        Returns:
            True if template was deleted successfully
        """
        with self._lock:
            try:
                if template_id not in self.templates:
                    return False
                
                # Check if it's a built-in template
                builtin_ids = {"professional_standard", "creative_enthusiastic", "technical_detailed", "executive_strategic"}
                if template_id in builtin_ids:
                    logger.error("Cannot delete built-in templates")
                    return False
                
                # Delete file
                template_file = Path(self.templates_dir) / f"{template_id}.json"
                if template_file.exists():
                    template_file.unlink()
                
                # Remove from memory
                del self.templates[template_id]
                
                structured_logger.info(
                    f"Custom template deleted: {template_id}",
                    operation="delete_custom_template",
                    template_id=template_id
                )
                
                return True
                
            except Exception as e:
                logger.error(f"Failed to delete custom template: {e}")
                return False
    
    def get_template_variables_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get information about template variables.
        
        Args:
            template_id: ID of template
            
        Returns:
            Dictionary with variable information
        """
        with self._lock:
            template = self.templates.get(template_id)
            if not template:
                return None
            
            return {
                'required_variables': template.required_variables,
                'optional_variables': template.optional_variables,
                'all_variables': template.required_variables + template.optional_variables,
                'preview_variables': template.preview_variables,
                'description': template.description
            }


# Streamlit integration for template selection and editing
class StreamlitTemplateInterface:
    """Streamlit interface for email template management."""
    
    @staticmethod
    def template_selector(manager: EmailTemplateManager, 
                         key_prefix: str = "email_template") -> Optional[str]:
        """
        Create Streamlit template selector.
        
        Args:
            manager: Email template manager
            key_prefix: Unique key prefix for Streamlit components
            
        Returns:
            Selected template ID or None
        """
        categories = manager.get_categories()
        
        # Category selector
        selected_category = st.selectbox(
            "📁 Template Category",
            ["All"] + categories,
            key=f"{key_prefix}_category"
        )
        
        # Get templates for selected category
        if selected_category == "All":
            templates = manager.get_templates()
        else:
            templates = manager.get_templates(selected_category)
        
        if not templates:
            st.warning("No templates available for selected category.")
            return None
        
        # Template selector
        template_options = {f"{t.name} - {t.description}": t.id for t in templates}
        
        selected_name = st.selectbox(
            "📧 Select Email Template",
            list(template_options.keys()),
            key=f"{key_prefix}_selection"
        )
        
        return template_options[selected_name]
    
    @staticmethod
    def template_preview(manager: EmailTemplateManager, 
                        template_id: str,
                        key_prefix: str = "preview") -> None:
        """
        Show template preview.
        
        Args:
            manager: Email template manager
            template_id: ID of template to preview
            key_prefix: Unique key prefix for Streamlit components
        """
        template = manager.get_template(template_id)
        if not template:
            return
        
        with st.expander("📋 Template Preview", expanded=False):
            subject, body = manager.preview_template(template_id)
            
            st.subheader("Subject Line")
            st.code(subject)
            
            st.subheader("Email Body")
            st.text_area(
                "Email Content",
                value=body,
                height=300,
                disabled=True,
                key=f"{key_prefix}_body"
            )
            
            # Show variable information
            var_info = manager.get_template_variables_info(template_id)
            if var_info:
                st.subheader("Template Variables")
                
                if var_info['required_variables']:
                    st.write("**Required Variables:**")
                    for var in var_info['required_variables']:
                        st.write(f"• `{var}`")
                
                if var_info['optional_variables']:
                    st.write("**Optional Variables:**")
                    for var in var_info['optional_variables']:
                        st.write(f"• `{var}`")
    
    @staticmethod
    def variable_input_form(manager: EmailTemplateManager, 
                           template_id: str,
                           key_prefix: str = "vars") -> Dict[str, str]:
        """
        Create form for template variable input.
        
        Args:
            manager: Email template manager
            template_id: ID of template
            key_prefix: Unique key prefix for Streamlit components
            
        Returns:
            Dictionary of variable values
        """
        var_info = manager.get_template_variables_info(template_id)
        if not var_info:
            return {}
        
        variables = {}
        
        st.subheader("📝 Customize Your Email")
        
        # Required variables
        if var_info['required_variables']:
            st.write("**Required Information:**")
            for var in var_info['required_variables']:
                default_value = var_info['preview_variables'].get(var, '')
                variables[var] = st.text_input(
                    f"{var.replace('_', ' ').title()}",
                    value=default_value,
                    key=f"{key_prefix}_{var}",
                    help=f"Enter {var.replace('_', ' ')}"
                )
        
        # Optional variables in expander
        if var_info['optional_variables']:
            with st.expander("⚙️ Optional Details", expanded=False):
                for var in var_info['optional_variables']:
                    default_value = var_info['preview_variables'].get(var, '')
                    variables[var] = st.text_input(
                        f"{var.replace('_', ' ').title()}",
                        value=default_value,
                        key=f"{key_prefix}_{var}",
                        help=f"Enter {var.replace('_', ' ')} (optional)"
                    )
        
        return variables


# Global template manager instance
_template_manager = None
_manager_lock = threading.Lock()


def get_template_manager(templates_dir: Optional[str] = None) -> EmailTemplateManager:
    """Get global email template manager instance."""
    global _template_manager
    
    with _manager_lock:
        if _template_manager is None:
            _template_manager = EmailTemplateManager(templates_dir)
        return _template_manager



