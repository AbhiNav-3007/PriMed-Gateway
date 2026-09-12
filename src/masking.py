"""
PrivMed Gateway — Masking & Date Shifting Engine Module
Implements consistent typed pseudonymization and relative date shifting.
"""

from typing import List, Dict, Tuple, Any
from datetime import datetime, timedelta
import re
from src.detection import EntitySpan

class DateShifter:
    """Consistently shifts dates by a fixed day offset to preserve clinical intervals."""

    def __init__(self, shift_days: int = 100):
        self.shift_days = shift_days

    def shift_date_string(self, date_str: str) -> str:
        """Parses common date formats and shifts them by shift_days."""
        # Simple date pattern matches
        formats = [
            "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d",
            "%m-%d-%Y", "%d-%m-%Y", "%Y-%m-%d",
            "%b %d, %Y", "%B %d, %Y", "%d %b %Y", "%d %B %Y"
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str.strip(), fmt)
                shifted_dt = dt + timedelta(days=self.shift_days)
                return shifted_dt.strftime(fmt)
            except ValueError:
                continue
        # Fallback if non-standard date format
        return f"SHIFTED_{date_str}"


class MaskingEngine:
    """Applies consistent typed pseudonymization and manages in-memory mapping dictionaries."""

    # Standard placeholder prefixes by entity label
    PREFIX_MAP = {
        "PATIENT": "PATIENT_NAME",
        "DOCTOR": "PROVIDER_NAME",
        "LOCATION": "LOCATION",
        "DATE": "DATE",
        "PHONE": "PHONE",
        "EMAIL": "EMAIL",
        "MRN": "MRN",
        "SSN": "SSN",
        "IP_ADDRESS": "IP_ADDRESS",
        "URL": "URL",
        "AGE": "AGE"
    }

    def __init__(self, enable_date_shifting: bool = False, date_shift_days: int = 100):
        self.enable_date_shifting = enable_date_shifting
        self.date_shifter = DateShifter(shift_days=date_shift_days)

    def mask(self, text: str, entities: List[EntitySpan]) -> Tuple[str, Dict[str, str]]:
        """
        Replaces entity spans in text with consistent placeholders.
        Returns (masked_text, mapping_dict).
        """
        if not entities:
            return text, {}

        # 1. First Pass: Assign placeholders in forward reading order (start index 0 -> end)
        forward_sorted = sorted(entities, key=lambda e: e.start)
        value_to_placeholder: Dict[str, str] = {}
        placeholder_to_value: Dict[str, str] = {}
        type_counters: Dict[str, int] = {}

        for entity in forward_sorted:
            entity_val = entity.text.strip()
            prefix = self.PREFIX_MAP.get(entity.label, entity.label)

            if entity_val not in value_to_placeholder:
                type_counters[prefix] = type_counters.get(prefix, 0) + 1
                placeholder = f"<{prefix}_{type_counters[prefix]:03d}>"
                value_to_placeholder[entity_val] = placeholder

                # Apply date shifting to mapping value if enabled
                if entity.label == "DATE" and self.enable_date_shifting:
                    shifted_val = self.date_shifter.shift_date_string(entity_val)
                    placeholder_to_value[placeholder] = shifted_val
                else:
                    placeholder_to_value[placeholder] = entity_val

        # 2. Second Pass: Perform text replacement at exact span bounds in reverse order
        reverse_sorted = sorted(entities, key=lambda e: e.start, reverse=True)
        masked_text = text

        for entity in reverse_sorted:
            entity_val = entity.text.strip()
            placeholder = value_to_placeholder.get(entity_val, value_to_placeholder.get(entity.text))
            if placeholder:
                masked_text = masked_text[:entity.start] + placeholder + masked_text[entity.end:]

        return masked_text, placeholder_to_value
