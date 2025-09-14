"""
Root Configuration Module for Resume Customizer Application
Contains all application-wide configuration constants and settings
"""

import os
from typing import Dict, List, Any

# Environment detection
def is_production() -> bool:
    """Check if running in production environment"""
    return os.getenv('ENVIRONMENT', 'development').lower() == 'production'

def is_debug() -> bool:
    """Check if debug mode is enabled"""
    return os.getenv('DEBUG', 'false').lower() in ['true', '1', 'yes']

# Document processing configuration
DOC_CONFIG = {
    "max_project_title_length": 100,
    "default_filename": "resume.docx",
    "supported_formats": ['.docx', '.doc', '.pdf'],
    "max_file_size_mb": 10,
    "processing_timeout_seconds": 300,
    "temp_dir": "temp_uploads",
    "output_dir": "processed_resumes"
}

# Text parsing configuration
PARSING_CONFIG = {
    "tech_name_exclude_words": [
        "and", "or", "with", "using", "including", "such", "as", "like", 
        "for", "in", "on", "at", "by", "from", "to", "of", "the", "a", "an",
        "experience", "knowledge", "skills", "proficient", "familiar",
        "years", "year", "months", "month", "strong", "good", "excellent"
    ],
    "project_exclude_keywords": [
        "education", "school", "university", "college", "degree", "certification",
        "contact", "phone", "email", "address", "linkedin", "github",
        "summary", "objective", "profile", "about", "skills", "technologies"
    ],
    "section_headers": {
        "experience": ["experience", "work experience", "employment", "career", "professional experience"],
        "education": ["education", "academic background", "qualifications", "degrees"],
        "skills": ["skills", "technical skills", "technologies", "competencies", "expertise"],
        "projects": ["projects", "key projects", "notable projects", "personal projects"],
        "certifications": ["certifications", "certificates", "licenses", "credentials"]
    },
    "bullet_point_indicators": ["•", "◦", "▪", "▫", "‣", "⁃", "-", "*"],
    "min_bullet_length": 10,
    "max_bullet_length": 500,
    "tech_stack_patterns": [
        r'\b(?:Python|Java|JavaScript|TypeScript|C\+\+|C#|Go|Rust|Ruby|PHP|Swift|Kotlin)\b',
        r'\b(?:React|Angular|Vue|Django|Flask|Spring|Express|Laravel|Rails)\b',
        r'\b(?:MySQL|PostgreSQL|MongoDB|Redis|Elasticsearch|SQLite)\b',
        r'\b(?:AWS|Azure|GCP|Docker|Kubernetes|Jenkins|Git|Linux)\b'
    ]
}

# Email configuration
EMAIL_CONFIG = {
    "smtp_servers": [
        "smtp.gmail.com",
        "smtp.outlook.com", 
        "smtp.yahoo.com",
        "smtp.mail.yahoo.com",
        "smtp.aol.com",
        "smtp.zoho.com",
        "smtp.icloud.com",
        "localhost"
    ],
    "default_ports": {
        "smtp.gmail.com": 587,
        "smtp.outlook.com": 587,
        "smtp.yahoo.com": 587,
        "smtp.mail.yahoo.com": 587,
        "smtp.aol.com": 587,
        "smtp.zoho.com": 587,
        "smtp.icloud.com": 587,
        "localhost": 25
    },
    "timeout_seconds": 30,
    "max_attachment_size_mb": 25,
    "retry_attempts": 3,
    "retry_delay_seconds": 5
}

# Application settings
APP_CONFIG = {
    "app_name": "Resume Customizer",
    "version": "2.0.0",
    "max_concurrent_uploads": 5,
    "session_timeout_minutes": 60,
    "cache_ttl_seconds": 3600,
    "log_level": "INFO",
    "enable_analytics": True,
    "enable_performance_monitoring": True
}

# UI Configuration
UI_CONFIG = {
    "page_title": "Resume Customizer - AI-Powered Resume Enhancement",
    "page_icon": "📄",
    "layout": "wide",
    "sidebar_state": "expanded",
    "theme": {
        "primary_color": "#1f77b4",
        "background_color": "#ffffff",
        "secondary_background_color": "#f0f2f6",
        "text_color": "#262730"
    },
    "max_upload_size_mb": 200,
    "allowed_file_types": ["docx", "doc", "pdf"]
}

# Database configuration (imported from database.config)
try:
    from database.config import (
        get_smtp_servers, get_default_email_subject, 
        get_default_email_body, get_email_config
    )
    DATABASE_INTEGRATION_AVAILABLE = True
except ImportError:
    DATABASE_INTEGRATION_AVAILABLE = False
    
    def get_smtp_servers():
        return EMAIL_CONFIG["smtp_servers"]
    
    def get_default_email_subject():
        return "Resume Application - {job_title} at {company_name}"
    
    def get_default_email_body():
        return """Dear Hiring Manager,

I hope this email finds you well. I am writing to express my interest in the {job_title} position at {company_name}.

Please find my resume attached for your review. I have customized it specifically for this role, highlighting my relevant experience and skills that align with your requirements.

I would welcome the opportunity to discuss how my background and enthusiasm can contribute to your team's success.

Thank you for your time and consideration.

Best regards,
[Your Name]
[Your Contact Information]"""
    
    def get_email_config():
        return EMAIL_CONFIG

def reload_config():
    """Reload configuration from environment variables"""
    global DOC_CONFIG, PARSING_CONFIG, EMAIL_CONFIG, APP_CONFIG, UI_CONFIG
    
    # Reload environment-dependent settings
    if 'MAX_FILE_SIZE_MB' in os.environ:
        DOC_CONFIG['max_file_size_mb'] = int(os.environ['MAX_FILE_SIZE_MB'])
    
    if 'PROCESSING_TIMEOUT' in os.environ:
        DOC_CONFIG['processing_timeout_seconds'] = int(os.environ['PROCESSING_TIMEOUT'])
    
    if 'LOG_LEVEL' in os.environ:
        APP_CONFIG['log_level'] = os.environ['LOG_LEVEL']
    
    if 'ENABLE_ANALYTICS' in os.environ:
        APP_CONFIG['enable_analytics'] = os.environ['ENABLE_ANALYTICS'].lower() in ['true', '1', 'yes']
    
    print("✅ Configuration reloaded from environment variables")

def create_env_template():
    """Create a template .env file with all configuration options"""
    template_content = """# Resume Customizer Configuration Template
# Copy this file to .env and update the values

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=resume_customizer
DB_USER=postgres
DB_PASSWORD=your_password_here

# Application Settings
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
ENABLE_ANALYTICS=true

# File Processing
MAX_FILE_SIZE_MB=10
PROCESSING_TIMEOUT=300

# Email Configuration (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_USER=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Security (Optional)
SECRET_KEY=your_secret_key_here
ENCRYPTION_KEY=your_encryption_key_here
"""
    
    try:
        with open('.env.template', 'w') as f:
            f.write(template_content)
        print("✅ .env template created successfully!")
        return True
    except Exception as e:
        print(f"❌ Failed to create .env template: {e}")
        return False

def get_config_summary():
    """Get a summary of current configuration"""
    return {
        "environment": "production" if is_production() else "development",
        "debug_mode": is_debug(),
        "database_integration": DATABASE_INTEGRATION_AVAILABLE,
        "max_file_size_mb": DOC_CONFIG["max_file_size_mb"],
        "supported_formats": DOC_CONFIG["supported_formats"],
        "smtp_servers_count": len(EMAIL_CONFIG["smtp_servers"]),
        "app_version": APP_CONFIG["version"]
    }

# Error and success message definitions
ERROR_MESSAGES = {
    "invalid_tech_stack_format": """❌ Input format error! Please use one of these 3 supported formats:

**FORMAT 1:** Tech Stack (no colon) + Tabbed Bullet Points
```
Java
•\tPoint with tab indentation
•\tAnother point with tab
```

**FORMAT 2:** Tech Stack with Colon + Tabbed Bullet Points
```
Java:
•\tPoint with tab indentation  
•\tAnother point with tab
```

**FORMAT 3:** Tech Stack (no colon) + Regular Bullet Points
```
Java
• Point with regular bullet (no tab)
• Another point with regular bullet
```

You can mix different formats in the same input. Each tech stack should be separated by a blank line.""",
    
    "empty_parse_results": """⚠️ No valid points detected in your input. Please ensure you're using one of the 3 supported formats above with:
- Tech stack name on its own line
- Bullet points (• symbol) below the tech name
- Each tech stack separated by blank lines""",
    
    "point_distribution_failed": "❌ Cannot distribute points because no valid tech stack data was found. Please check your input format.",
    
    "no_tech_stacks": "❌ No tech stacks found in the input for file: {filename}. Please add tech stack data using the supported formats.",
    
    "no_projects": "❌ No projects found in resume: {filename}. Please ensure your resume has clear project sections with 'Responsibilities:' headings.",
    
    "parsing_exception": "❌ Error parsing your input: {error}\n\nPlease use one of the 3 supported formats shown above.",
    
    "smtp_connection_failed": "Failed to connect to SMTP server: {error}",
    "custom_smtp_error": "Custom SMTP configuration error: {error}"
}

SUCCESS_MESSAGES = {
    "resume_processed": "✅ Resume processed successfully! Added {points_count} points across {projects_count} projects.",
    "email_sent": "✅ Email sent successfully to {recipient}",
    "bulk_processing_complete": "✅ Bulk processing complete! Processed {count} resumes successfully.",
    "preview_generated": "✅ Preview generated successfully with {points_count} new points."
}

# Export commonly used configurations
__all__ = [
    'DOC_CONFIG', 'PARSING_CONFIG', 'EMAIL_CONFIG', 'APP_CONFIG', 'UI_CONFIG',
    'ERROR_MESSAGES', 'SUCCESS_MESSAGES',
    'is_production', 'is_debug', 'reload_config', 'create_env_template',
    'get_smtp_servers', 'get_default_email_subject', 'get_default_email_body',
    'get_email_config', 'get_config_summary', 'DATABASE_INTEGRATION_AVAILABLE'
]
