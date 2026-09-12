"""
PrivMed Gateway — Primary Gateway Interface Module
Exposes top-level deidentify() and rehydrate() gateway functions.
"""

from typing import Tuple, Dict, List, Any
from src.detection import RegexDetector, TransformerNERDetector, PresidioDetector, EntitySpan
from src.resolver import EntityResolver, ConfidenceEngine
from src.masking import MaskingEngine
from src.rehydration import RehydrationEngine
from src.llm_client import get_llm_client, BaseLLMClient

class PrivMedGateway:
    """Orchestrates hybrid PHI detection, resolution, masking, LLM execution, and rehydration."""

    def __init__(self, enable_date_shifting: bool = False, date_shift_days: int = 100, use_mock_llm: bool = True, provider: str = "mock", api_key: str = ""):
        self.regex_detector = RegexDetector()
        self.ner_detector = TransformerNERDetector()
        self.presidio_detector = PresidioDetector()
        self.resolver = EntityResolver(confidence_threshold=0.50)
        self.masker = MaskingEngine(enable_date_shifting=enable_date_shifting, date_shift_days=date_shift_days)
        self.rehydrator = RehydrationEngine()
        self.llm_client = get_llm_client(provider=provider, use_mock=use_mock_llm, api_key=api_key)

    def deidentify(self, text: str) -> Tuple[str, Dict[str, str], List[Dict[str, Any]]]:
        """
        Detects PHI, resolves spans, applies consistent pseudonymization.
        Returns (masked_text, mapping_dict, detected_entities_metadata).
        """
        if not text:
            return "", {}, []

        # 1. Run hybrid detectors in parallel
        regex_entities = self.regex_detector.detect(text)
        ner_entities = self.ner_detector.detect(text)
        presidio_entities = self.presidio_detector.detect(text)

        all_candidates = regex_entities + ner_entities + presidio_entities

        # 2. Resolve overlaps and word boundaries
        resolved_entities = self.resolver.resolve(all_candidates, raw_text=text)

        # 3. Apply pseudonymization and build mapping
        masked_text, mapping = self.masker.mask(text, resolved_entities)

        entities_meta = [
            {
                "text": e.text,
                "label": e.label,
                "start": e.start,
                "end": e.end,
                "confidence": e.confidence,
                "confidence_tier": ConfidenceEngine.get_confidence_tier(e.confidence, e.detector_source),
                "source": e.detector_source
            }
            for e in resolved_entities
        ]

        return masked_text, mapping, entities_meta

    def rehydrate(self, response: str, mapping: Dict[str, str]) -> Tuple[str, List[str]]:
        """Rehydrates LLM response back to original values using mapping."""
        return self.rehydrator.rehydrate(response, mapping)

    def process_round_trip(self, text: str, llm_prompt_template: str = None) -> Dict[str, Any]:
        """Executes complete end-to-end round trip with placeholder integrity validation and security checks."""
        masked_text, mapping, entities_meta = self.deidentify(text)

        system_instruction = (
            "You are processing de-identified clinical text.\n"
            "The text contains placeholders representing protected identifiers (e.g. <PATIENT_NAME_000>, <DATE_000>, <MRN_000>).\n"
            "You MUST preserve placeholders exactly.\n"
            "Do not modify placeholder names or numbers.\n"
            "Do not invent placeholders.\n"
            "Do not replace placeholders with real names, dates, addresses, phone numbers, IDs, or other identifiers.\n"
            "Do not infer or reconstruct original protected information.\n"
            "Do not reveal PHI.\n"
            "If a placeholder is needed in your response, copy it character-for-character exactly as provided.\n\n"
            "De-identified Clinical Input:\n"
        )

        if llm_prompt_template:
            formatted_prompt = llm_prompt_template.format(masked_text=masked_text)
        else:
            formatted_prompt = f"{system_instruction}{masked_text}"

        # Security Audit: Verify NO raw PHI value from mapping was included in the LLM prompt
        phi_leak_detected = False
        leaked_values = []
        for placeholder, original_val in mapping.items():
            if len(original_val) > 2 and original_val.lower() in formatted_prompt.lower():
                phi_leak_detected = True
                leaked_values.append(original_val)

        llm_response = self.llm_client.generate(formatted_prompt)

        # Placeholder Integrity Validation
        from src.validator import PlaceholderValidator
        validator = PlaceholderValidator()
        validation_report = validator.validate(masked_input=masked_text, llm_response=llm_response, mapping=mapping)

        final_rehydrated, unknown_placeholders = self.rehydrate(llm_response, mapping)

        return {
            "original_text": text,
            "masked_text": masked_text,
            "entities": entities_meta,
            "mapping": mapping,
            "prompt_sent_to_llm": formatted_prompt,
            "llm_response": llm_response,
            "final_response": final_rehydrated,
            "unknown_placeholders": validation_report["unknown_placeholders"],
            "missing_placeholders": validation_report["missing_placeholders"],
            "malformed_placeholders": validation_report["malformed_placeholders"],
            "validation_report": validation_report,
            "raw_phi_sent_to_llm": phi_leak_detected,
            "leaked_values": leaked_values
        }


_default_gateway = None

def _get_default_gateway() -> PrivMedGateway:
    global _default_gateway
    if _default_gateway is None:
        _default_gateway = PrivMedGateway(use_mock_llm=True)
    return _default_gateway

def deidentify(text: str) -> Tuple[str, Dict[str, str]]:
    """
    Assessment required interface:
    deidentify(text) -> (masked_text, mapping)
    """
    gw = _get_default_gateway()
    masked_text, mapping, _ = gw.deidentify(text)
    return masked_text, mapping

def rehydrate(response: str, mapping: Dict[str, str]) -> str:
    """
    Assessment required interface:
    rehydrate(response, mapping) -> text
    """
    gw = _get_default_gateway()
    rehydrated_text, _ = gw.rehydrate(response, mapping)
    return rehydrated_text
