"""
PrivMed Gateway — Entity Resolver & Confidence Engine Module
Handles span overlap resolution, word boundary alignment, subword merging, and detector precedence.
"""

import re
from typing import List, Dict, Any, Tuple
from src.detection import EntitySpan

class EntityResolver:
    """Combines detections from ML NER, Regex, and Presidio to yield non-overlapping resolved entities."""

    PRECEDENCE = {
        "SSN": 10,
        "EMAIL": 9,
        "PHONE": 9,
        "IP_ADDRESS": 9,
        "URL": 9,
        "MRN": 8,
        "DATE": 7,
        "PATIENT": 6,
        "DOCTOR": 6,
        "LOCATION": 5,
        "AGE": 5
    }

    NON_PHI_WORDS = {"TELEMETRY", "RECORDED", "TELEMET", "IP", "MRN", "TWO WEEKS", "DAYS", "HIS", "WAS", "IS", "WITH", "SUFFERING", "HAS"}

    def __init__(self, confidence_threshold: float = 0.50):
        self.confidence_threshold = confidence_threshold

    def _get_precedence(self, entity: EntitySpan) -> int:
        base_score = self.PRECEDENCE.get(entity.label, 1)
        if entity.detector_source == "REGEX":
            base_score += 2
        return base_score

    def _expand_to_word_boundary(self, text: str, start: int, end: int) -> Tuple[int, int, str]:
        """Expands character offsets to complete surrounding word boundaries to prevent subword truncation."""
        if not text:
            return start, end, text[start:end]
        
        while start > 0 and (text[start-1].isalnum() or text[start-1] in "-_"):
            start -= 1
        while end < len(text) and (text[end].isalnum() or text[end] in "-_"):
            end += 1
        return start, end, text[start:end]

    def _merge_adjacent_spans(self, entities: List[EntitySpan], raw_text: str = "") -> List[EntitySpan]:
        """Merges adjacent entity spans of the exact same label if separated only by whitespace."""
        if not entities or len(entities) < 2:
            return entities

        entities.sort(key=lambda e: e.start)
        merged: List[EntitySpan] = []

        i = 0
        while i < len(entities):
            current = entities[i]
            
            while i + 1 < len(entities):
                next_e = entities[i + 1]
                # If same label and separated only by spaces/hyphens
                gap_text = raw_text[current.end:next_e.start] if raw_text else " "
                if current.label == next_e.label and gap_text.strip() == "":
                    # Expand current entity to include next_e
                    current.end = next_e.end
                    current.text = raw_text[current.start:current.end] if raw_text else f"{current.text} {next_e.text}"
                    current.confidence = max(current.confidence, next_e.confidence)
                    i += 1
                else:
                    break
            
            merged.append(current)
            i += 1

        return merged

    def resolve(self, entity_list: List[EntitySpan], raw_text: str = "") -> List[EntitySpan]:
        """
        Resolves overlapping and duplicate spans across multiple detector outputs.
        Returns a sorted list of non-overlapping resolved EntitySpan objects.
        """
        filtered = []
        for e in entity_list:
            if e.confidence < self.confidence_threshold:
                continue
            if e.text.strip().upper() in self.NON_PHI_WORDS:
                continue

            # Align offsets to full surrounding word boundaries
            if raw_text and e.detector_source == "NER_TRANSFORMER":
                w_start, w_end, w_text = self._expand_to_word_boundary(raw_text, e.start, e.end)
                if w_text.strip().upper() in self.NON_PHI_WORDS:
                    continue
                e.start, e.end, e.text = w_start, w_end, w_text

            filtered.append(e)

        if not filtered:
            return []

        # Sort candidates by start offset, then longest span length, then precedence
        sorted_candidates = sorted(
            filtered,
            key=lambda e: (e.start, -(e.end - e.start), -self._get_precedence(e))
        )

        resolved: List[EntitySpan] = []

        for current in sorted_candidates:
            overlap = False
            for existing in resolved:
                if max(current.start, existing.start) < min(current.end, existing.end):
                    overlap = True
                    curr_len = current.end - current.start
                    exist_len = existing.end - existing.start
                    curr_prec = self._get_precedence(current)
                    exist_prec = self._get_precedence(existing)

                    if (curr_prec > exist_prec) or (curr_prec == exist_prec and curr_len > exist_len):
                        resolved.remove(existing)
                        resolved.append(current)
                    break
            
            if not overlap:
                resolved.append(current)

        # Merge adjacent spans of same entity type (e.g. "abhinav" + "raj" -> "abhinav raj")
        merged = self._merge_adjacent_spans(resolved, raw_text=raw_text)
        merged.sort(key=lambda e: e.start)
        return merged


class ConfidenceEngine:
    """Categorizes resolved entities into High, Medium, or Low confidence tiers."""

    @staticmethod
    def get_confidence_tier(confidence: float, detector_source: str) -> str:
        if detector_source == "REGEX":
            return "HIGH"
        if confidence >= 0.90:
            return "HIGH"
        elif confidence >= 0.60:
            return "MEDIUM"
        else:
            return "LOW"
