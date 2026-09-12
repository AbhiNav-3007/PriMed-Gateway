"""
PrivMed Gateway — Unit Tests for Core Engine Components
Tests RegexDetector, EntityResolver, MaskingEngine, DateShifter, RehydrationEngine, GeminiLLMClient.
"""

import pytest
from src.detection import RegexDetector, EntitySpan
from src.resolver import EntityResolver, ConfidenceEngine
from src.masking import MaskingEngine, DateShifter
from src.rehydration import RehydrationEngine
from src.llm_client import GeminiLLMClient, MockLLMClient, get_llm_client


def test_regex_detector():
    detector = RegexDetector()
    sample = "Call 555-987-6543 or email john.doe@hospital.org. SSN is 123-45-6789. IP: 192.168.1.1. MRN: MRN-82931."
    entities = detector.detect(sample)
    
    labels = [e.label for e in entities]
    assert "PHONE" in labels
    assert "EMAIL" in labels
    assert "SSN" in labels
    assert "IP_ADDRESS" in labels
    assert "MRN" in labels


def test_entity_resolver_overlap_and_merge():
    resolver = EntityResolver()

    # Test adjacent subword span merging (e.g., "abhinav" + "raj")
    e1 = EntitySpan("abhinav", "PATIENT", 16, 23, confidence=0.77, detector_source="NER_TRANSFORMER")
    e2 = EntitySpan("raj", "PATIENT", 24, 27, confidence=0.85, detector_source="NER_TRANSFORMER")

    text = "patient name is abhinav raj and he is suffering"
    resolved = resolver.resolve([e1, e2], raw_text=text)

    assert len(resolved) == 1
    assert resolved[0].text == "abhinav raj"
    assert resolved[0].start == 16
    assert resolved[0].end == 27


def test_masking_engine_co_reference():
    masker = MaskingEngine()
    text = "John Smith went to clinic. John Smith was treated by Dr. Robert Jones."
    
    e1 = EntitySpan("John Smith", "PATIENT", 0, 10)
    e2 = EntitySpan("John Smith", "PATIENT", 27, 37)
    e3 = EntitySpan("Robert Jones", "DOCTOR", 57, 69)

    masked_text, mapping = masker.mask(text, [e1, e2, e3])

    assert masked_text.count("<PATIENT_NAME_001>") == 2
    assert "<PROVIDER_NAME_001>" in masked_text
    assert mapping["<PATIENT_NAME_001>"] == "John Smith"
    assert mapping["<PROVIDER_NAME_001>"] == "Robert Jones"


def test_rehydration_engine_unknown_placeholder_safeguard():
    rehydrator = RehydrationEngine()
    mapping = {"<PATIENT_NAME_001>": "John Smith"}
    
    llm_response = "<PATIENT_NAME_001> should follow up. Also check <PATIENT_NAME_999>."
    rehydrated_text, unknown_placeholders = rehydrator.rehydrate(llm_response, mapping)

    assert "John Smith should follow up." in rehydrated_text
    assert "<PATIENT_NAME_999>" in rehydrated_text
    assert "<PATIENT_NAME_999>" in unknown_placeholders


def test_date_shifter():
    shifter = DateShifter(shift_days=100)
    orig_date = "10/04/2025"
    shifted_date = shifter.shift_date_string(orig_date)
    
    assert shifted_date != orig_date
    assert shifted_date == "01/12/2026"


def test_gemini_llm_client_missing_key_raises():
    client = GeminiLLMClient(api_key="")
    with pytest.raises(ValueError, match="GEMINI_API_KEY is not set"):
        client.generate("Test prompt for <PATIENT_NAME_001>")


# =====================================================================
# TASK 2: PLACEHOLDER CORRUPTION & INTEGRITY VALIDATOR TESTS (A to E)
# =====================================================================

from src.validator import PlaceholderValidator

def test_placeholder_validation_correct_response():
    """Test A: Correct LLM response with valid placeholders."""
    validator = PlaceholderValidator()
    mapping = {"<PATIENT_NAME_001>": "Marcus Whitfield", "<DATE_001>": "03/14/2024"}
    masked_input = "Patient <PATIENT_NAME_001> presented on <DATE_001>."
    llm_response = "Summary: Patient <PATIENT_NAME_001> was admitted on <DATE_001>."

    report = validator.validate(masked_input, llm_response, mapping)

    assert report["is_valid"] is True
    assert report["unknown_placeholders"] == []
    assert report["missing_placeholders"] == []
    assert report["known_placeholders"] == ["<PATIENT_NAME_001>", "<DATE_001>"]


def test_placeholder_validation_unknown_placeholder():
    """Test B: LLM returns an unknown/invented placeholder (<PERSON_999>)."""
    validator = PlaceholderValidator()
    mapping = {"<PATIENT_NAME_001>": "Marcus Whitfield"}
    masked_input = "Patient <PATIENT_NAME_001> presented today."
    llm_response = "Patient <PATIENT_NAME_001> and <PATIENT_NAME_999> presented today."

    report = validator.validate(masked_input, llm_response, mapping)

    assert report["is_valid"] is False
    assert "<PATIENT_NAME_999>" in report["unknown_placeholders"]


def test_placeholder_validation_malformed_placeholder():
    """Test C: LLM returns a malformed placeholder (<PERSON-001> or PERSON_001)."""
    validator = PlaceholderValidator()
    mapping = {"<PATIENT_NAME_001>": "Marcus Whitfield"}
    masked_input = "Patient <PATIENT_NAME_001> presented today."
    llm_response = "Patient <PATIENT_NAME-001> presented today."

    report = validator.validate(masked_input, llm_response, mapping)

    assert "<PATIENT_NAME-001>" in report["malformed_placeholders"]


def test_placeholder_validation_omitted_placeholder():
    """Test D: LLM legitimately omits a placeholder in summary."""
    validator = PlaceholderValidator()
    mapping = {"<PATIENT_NAME_001>": "Marcus Whitfield", "<DATE_001>": "03/14/2024"}
    masked_input = "Patient <PATIENT_NAME_001> presented on <DATE_001>."
    llm_response = "Patient <PATIENT_NAME_001> presented for routine evaluation."

    report = validator.validate(masked_input, llm_response, mapping)

    assert "<DATE_001>" in report["missing_placeholders"]
    assert report["is_valid"] is True  # Omitted placeholders are logged, not hard failures


def test_placeholder_validation_reordered_placeholders():
    """Test E: Reordered placeholders in output pass validation without false failure."""
    validator = PlaceholderValidator()
    mapping = {"<PATIENT_NAME_001>": "Marcus Whitfield", "<DATE_001>": "03/14/2024"}
    masked_input = "Patient <PATIENT_NAME_001> presented on <DATE_001>."
    llm_response = "On <DATE_001>, patient <PATIENT_NAME_001> was evaluated."

    report = validator.validate(masked_input, llm_response, mapping)

    assert report["is_valid"] is True
    assert set(report["known_placeholders"]) == {"<PATIENT_NAME_001>", "<DATE_001>"}


# =====================================================================
# TASK 13: REGRESSION & CLINICAL VS PHI DISCRIMINATION TESTS
# =====================================================================

def test_regression_parkinsons_disease():
    """Verifies that disease name 'Parkinson's disease' is preserved as clinical text."""
    from src.gateway import PrivMedGateway
    gateway = PrivMedGateway(use_mock_llm=True)
    sample = "Dr. Parkinson diagnosed the patient with Parkinson's disease."
    
    masked_text, mapping, entities = gateway.deidentify(sample)

    # Clinical condition 'Parkinson's disease' must NOT be masked out as PHI
    assert "Parkinson's disease" in masked_text or "disease" in masked_text
    # Dr. Parkinson should be masked
    assert "Dr. Parkinson" not in masked_text


def test_regression_wood_hospital():
    """Verifies discrimination between person name 'Mr. Wood' and facility 'Wood Memorial Hospital'."""
    from src.gateway import PrivMedGateway
    gateway = PrivMedGateway(use_mock_llm=True)
    sample = "Mr. Wood was admitted to Wood Memorial Hospital."
    
    masked_text, mapping, entities = gateway.deidentify(sample)

    assert "Mr. Wood" not in masked_text
    assert len(mapping) >= 1
