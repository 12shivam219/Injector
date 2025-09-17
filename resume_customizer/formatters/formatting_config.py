"""
Configuration system for resume formatting rules.
Allows customization of bullet points, spacing, and other formatting options.
"""
from typing import Dict, List, Any, Optional
import json
import os
from dataclasses import dataclass, field, asdict
from infrastructure.utilities.logger import get_logger

logger = get_logger()

@dataclass
class BulletConfig:
    """Configuration for bullet point formatting."""
    preferred_markers: List[str] = field(default_factory=lambda: ['•', '-', '●'])
    default_marker: str = '- '
    indent_spaces: int = 2
    preserve_original_formatting: bool = True
    capitalize_first_letter: bool = True
    end_with_period: bool = False

@dataclass
class SpacingConfig:
    """Configuration for paragraph spacing."""
    before_paragraph: float = 0.0
    after_paragraph: float = 6.0
    line_spacing: float = 1.15

@dataclass
class FormattingConfig:
    """Master configuration for all formatting options."""
    bullet_config: BulletConfig = field(default_factory=BulletConfig)
    spacing_config: SpacingConfig = field(default_factory=SpacingConfig)
    max_bullet_points_per_project: int = 5
    enforce_consistent_bullets: bool = True
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'FormattingConfig':
        """Load configuration from a JSON file."""
        try:
            if os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    config_dict = json.load(f)
                
                # Create config objects from dict
                bullet_config = BulletConfig(**config_dict.get('bullet_config', {}))
                spacing_config = SpacingConfig(**config_dict.get('spacing_config', {}))
                
                return cls(
                    bullet_config=bullet_config,
                    spacing_config=spacing_config,
                    max_bullet_points_per_project=config_dict.get('max_bullet_points_per_project', 5),
                    enforce_consistent_bullets=config_dict.get('enforce_consistent_bullets', True)
                )
            else:
                logger.warning(f"Config file {filepath} not found, using defaults")
                return cls()
        except Exception as e:
            logger.error(f"Error loading config from {filepath}: {e}")
            return cls()
    
    def save_to_file(self, filepath: str) -> bool:
        """Save configuration to a JSON file."""
        try:
            # Convert to dictionary
            config_dict = {
                'bullet_config': asdict(self.bullet_config),
                'spacing_config': asdict(self.spacing_config),
                'max_bullet_points_per_project': self.max_bullet_points_per_project,
                'enforce_consistent_bullets': self.enforce_consistent_bullets
            }
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Write to file
            with open(filepath, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            logger.info(f"Configuration saved to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving config to {filepath}: {e}")
            return False


# Default configuration file path
DEFAULT_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'formatting_config.json')

# Singleton instance
_config_instance = None

def get_formatting_config(config_path: str = DEFAULT_CONFIG_PATH) -> FormattingConfig:
    """Get the formatting configuration singleton."""
    global _config_instance
    
    if _config_instance is None:
        _config_instance = FormattingConfig.load_from_file(config_path)
    
    return _config_instance

def reset_formatting_config() -> None:
    """Reset the formatting configuration to defaults."""
    global _config_instance
    _config_instance = FormattingConfig()