"""
PrivMed Gateway — Rehydration Engine Module
Restores original entity identifiers from LLM responses with unknown placeholder safeguards.
"""

import re
from typing import Dict, Tuple, List

from src.validator import PlaceholderValidator

class RehydrationEngine:
    """Rehydrates placeholders in LLM response text back to original values using session mappings."""

    def __init__(self):
        self.validator = PlaceholderValidator()

    def rehydrate(self, llm_response: str, mapping: Dict[str, str], masked_input: str = "") -> Tuple[str, List[str]]:
        """
        Replaces known placeholders in llm_response with their exact original mapped values.
        Returns (rehydrated_text, list_of_unknown_placeholders).
        """
        if not llm_response or not mapping:
            return llm_response, []

        rehydrated_text = llm_response

        # Extract all placeholders matching standard syntax
        found_placeholders = self.validator.extract_placeholders(llm_response)
        unique_placeholders = set(found_placeholders)

        unknown_placeholders: List[str] = []

        # Replace only known placeholders with their EXACT mapped original string value
        for placeholder in unique_placeholders:
            if placeholder in mapping:
                original_value = mapping[placeholder]
                # Safe exact token string replacement
                rehydrated_text = rehydrated_text.replace(placeholder, original_value)
            else:
                # Safeguard: Unknown / invented placeholder is NEVER guessed or replaced
                unknown_placeholders.append(placeholder)
                print(f"[RehydrationEngine] WARNING: Unknown placeholder '{placeholder}' detected in LLM response.")

        return rehydrated_text, unknown_placeholders
