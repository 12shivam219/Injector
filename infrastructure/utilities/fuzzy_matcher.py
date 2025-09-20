"""
Utility module for fuzzy string matching operations.
Provides configurable fuzzy matching functionality for company names and other text.
"""

from typing import Optional, Tuple
from rapidfuzz import fuzz, process
import re
import json
from pathlib import Path

class FuzzyMatcher:
    """
    A utility class for performing fuzzy string matching with configurable thresholds
    and matching strategies.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the FuzzyMatcher with configuration settings.
        
        Args:
            config_path (str, optional): Path to the formatting_config.json file.
                                      If None, uses default config.
        """
        self.config = self._load_config(config_path)
        self.threshold = self.config["fuzzy_matching"]["company_name_threshold"]
        self.use_token_set = self.config["fuzzy_matching"]["use_token_set_ratio"]
        self.ignore_case = self.config["fuzzy_matching"]["ignore_case"]
        self.ignore_punctuation = self.config["fuzzy_matching"]["ignore_punctuation"]
    
    def _load_config(self, config_path: Optional[str] = None) -> dict:
        """
        Load configuration from the specified path or use defaults.
        
        Args:
            config_path (str, optional): Path to configuration file
            
        Returns:
            dict: Configuration dictionary
        """
        default_config = {
            "fuzzy_matching": {
                "enabled": True,
                "company_name_threshold": 85,
                "use_token_set_ratio": True,
                "ignore_case": True,
                "ignore_punctuation": True
            }
        }
        
        if not config_path:
            config_path = Path(__file__).parent.parent / "config" / "formatting_config.json"
        
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
                # Ensure fuzzy_matching section exists
                if "fuzzy_matching" not in config:
                    config["fuzzy_matching"] = default_config["fuzzy_matching"]
                return config
        except (FileNotFoundError, json.JSONDecodeError):
            return default_config
    
    def _preprocess_text(self, text: str) -> str:
        """
        Preprocess text according to configuration settings.
        
        Args:
            text (str): Input text to preprocess
            
        Returns:
            str: Preprocessed text
        """
        if not text:
            return ""
            
        result = text
        
        if self.ignore_case:
            result = result.lower()
            
        if self.ignore_punctuation:
            # Remove punctuation and standardize spacing
            result = re.sub(r'[^\w\s]', ' ', result)
            result = re.sub(r'\s+', ' ', result).strip()
            
        return result
    
    def compare_strings(self, str1: str, str2: str) -> Tuple[bool, float]:
        """
        Compare two strings using fuzzy matching.
        
        Args:
            str1 (str): First string to compare
            str2 (str): Second string to compare
            
        Returns:
            Tuple[bool, float]: (is_match, similarity_score)
        """
        if not str1 or not str2:
            return False, 0.0
            
        # Preprocess strings according to config
        processed_str1 = self._preprocess_text(str1)
        processed_str2 = self._preprocess_text(str2)
        
        # Choose matching algorithm based on config
        if self.use_token_set:
            score = fuzz.token_set_ratio(processed_str1, processed_str2)
        else:
            score = fuzz.ratio(processed_str1, processed_str2)
            
        is_match = score >= self.threshold
        return is_match, score
    
    def find_best_match(self, query: str, choices: list[str]) -> Tuple[Optional[str], float]:
        """
        Find the best matching string from a list of choices.
        
        Args:
            query (str): String to match against
            choices (list[str]): List of possible matches
            
        Returns:
            Tuple[Optional[str], float]: (best_match, score) or (None, 0.0) if no matches
        """
        if not query or not choices:
            return None, 0.0
            
        processed_query = self._preprocess_text(query)
        processed_choices = [self._preprocess_text(choice) for choice in choices]
        
        # Choose matching algorithm based on config
        matcher = fuzz.token_set_ratio if self.use_token_set else fuzz.ratio
        
        # Find best match using process.extractOne
        result = process.extractOne(
            processed_query,
            processed_choices,
            scorer=matcher
        )
        
        if not result or result[1] < self.threshold:
            return None, 0.0
            
        # Return original string (not preprocessed) and score
        best_match_index = processed_choices.index(result[0])
        return choices[best_match_index], result[1]