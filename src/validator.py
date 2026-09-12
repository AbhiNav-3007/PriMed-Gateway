"""
PrivMed Gateway — Placeholder Integrity Validator Module
Provides deterministic validation of placeholders between masked input, LLM output, and mapping dictionary.
"""

import re
from typing import Dict, List, Set, Any, Tuple

class PlaceholderValidator:
    """
    Validates placeholder syntax, integrity, and preservation across de-identification round-trips.
    """

    # Standard valid placeholder syntax: <TYPE_001>
    VALID_PLACEHOLDER_REGEX = re.compile(r'<[A-Z_]+_\d{3}>')

    # Common malformed placeholder patterns (missing brackets, dashes instead of underscores, etc.)
    MALFORMED_REGEXES = [
        re.compile(r'<[A-Z_]+-\d{3}>'),                  # <PERSON-001>
        re.compile(r'(?<!<)\b[A-Z_]+_\d{3}\b(?!>)'),    # PERSON_001 (without angle brackets)
        re.compile(r'<[A-Z_]+\d{3}>'),                   # <PERSON001>
    ]

    def extract_placeholders(self, text: str) -> List[str]:
        """Extracts all valid placeholders in text in order of appearance."""
        if not text:
            return []
        return self.VALID_PLACEHOLDER_REGEX.findall(text)

    def extract_malformed_placeholders(self, text: str, valid_mapping: Dict[str, str]) -> List[str]:
        """Identifies potentially corrupted/malformed placeholders that do not match standard syntax."""
        if not text:
            return []
        
        malformed: List[str] = []
        valid_keys = set(valid_mapping.keys())

        for reg in self.MALFORMED_REGEXES:
            for match in reg.findall(text):
                # Ensure it's not actually a valid placeholder
                if match not in valid_keys and match not in malformed:
                    malformed.append(match)
        return malformed

    def validate(self, masked_input: str, llm_response: str, mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Performs full deterministic placeholder integrity check.
        Returns a structured validation report dictionary.
        """
        input_placeholders = self.extract_placeholders(masked_input)
        output_placeholders = self.extract_placeholders(llm_response)

        input_set = set(input_placeholders)
        output_set = set(output_placeholders)
        valid_keys = set(mapping.keys())

        # 1. Known vs Unknown Placeholders
        known_placeholders = [p for p in output_placeholders if p in valid_keys]
        unknown_placeholders = [p for p in output_placeholders if p not in valid_keys]

        # 2. Missing Placeholders (present in input but omitted in summary/output)
        missing_placeholders = [p for p in input_placeholders if p not in output_set]

        # 3. Malformed Placeholders
        malformed_placeholders = self.extract_malformed_placeholders(llm_response, mapping)

        return {
            "input_placeholders": input_placeholders,
            "output_placeholders": output_placeholders,
            "known_placeholders": known_placeholders,
            "unknown_placeholders": list(set(unknown_placeholders)),
            "missing_placeholders": list(set(missing_placeholders)),
            "malformed_placeholders": malformed_placeholders,
            "is_valid": len(unknown_placeholders) == 0 and len(malformed_placeholders) == 0,
            "input_sequence": input_placeholders,
            "output_sequence": output_placeholders
        }
