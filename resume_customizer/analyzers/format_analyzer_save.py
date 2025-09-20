def save_format(self, session, name: str, description: str, patterns: Dict[str, Any]) -> str:
    """Save format patterns to database"""
    try:
        format_model = ResumeFormat(
            name=name,
            description=description,
            name_pattern=patterns.get('name_pattern'),
            email_pattern=patterns.get('email_pattern'),
            phone_pattern=patterns.get('phone_pattern'),
            section_patterns=patterns.get('section_patterns'),
            company_patterns=patterns.get('company_patterns'),
            title_patterns=patterns.get('title_patterns'),
            version='1.0'  # Set default version
        )
        
        session.add(format_model)
        session.commit()
        return str(format_model.id)
    except Exception as e:
        session.rollback()
        self.logger.error(f"Error saving format: {str(e)}")
        raise