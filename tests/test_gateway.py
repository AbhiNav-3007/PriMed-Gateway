"""
PrivMed Gateway — Gateway Interface & Round-Trip End-to-End Tests
"""

import pytest
from src.gateway import PrivMedGateway, deidentify, rehydrate


def test_top_level_callable_interface():
    sample = "Patient John Smith was admitted on 10/04/2025. Phone: 555-987-6543."
    
    # Required callable interface test 1: deidentify(text) -> (masked_text, mapping)
    masked_text, mapping = deidentify(sample)

    assert "John Smith" not in masked_text
    assert "555-987-6543" not in masked_text
    assert len(mapping) > 0

    # Required callable interface test 2: rehydrate(response, mapping) -> text
    john_placeholder = [k for k, v in mapping.items() if v == "John Smith"][0]
    llm_response = f"Recommendation for {john_placeholder}: Continue regimen."
    rehydrated_text = rehydrate(llm_response, mapping)

    assert "John Smith" in rehydrated_text


def test_full_gateway_round_trip():
    gateway = PrivMedGateway(use_mock_llm=True)
    text = "Patient Sarah Connor was prescribed medication on 05/12/2025."

    result = gateway.process_round_trip(text)

    assert result["raw_phi_sent_to_llm"] is False
    assert result["original_text"] == text
    assert len(result["entities"]) > 0
    assert "Sarah Connor" not in result["masked_text"]
    assert "Sarah Connor" in result["final_response"]


def test_security_phi_leak_to_llm():
    """Security Test: Asserts zero raw PHI mapped values leak into the prompt payload sent to LLM."""
    gateway = PrivMedGateway(use_mock_llm=True)
    sample = "Patient Marcus Whitfield was admitted on 03/14/2024. Phone: 987-654-3210. Attending: Dr. Sarah Johnson."
    
    result = gateway.process_round_trip(sample)
    prompt_sent = result["prompt_sent_to_llm"]

    # Verify that raw PHI sent flag is false
    assert result["raw_phi_sent_to_llm"] is False, "PHI_LEAK_TO_LLM: Raw PHI sent flag triggered"

    # Explicitly check that every mapped original value is absent from prompt_sent
    for placeholder, original_val in result["mapping"].items():
        if len(original_val) > 2:
            assert original_val.lower() not in prompt_sent.lower(), f"PHI_LEAK_TO_LLM: Mapped value '{original_val}' found in LLM prompt payload!"


def test_controlled_clinical_sample():
    """Controlled clinical sample round-trip test."""
    gateway = PrivMedGateway(use_mock_llm=True)
    sample = (
        "Patient Marcus Whitfield was admitted on 03/14/2024. "
        "His phone number is 987-654-3210. "
        "He was seen by Dr. Sarah Johnson."
    )
    result = gateway.process_round_trip(sample)

    assert "Marcus Whitfield" not in result["masked_text"]
    assert "987-654-3210" not in result["masked_text"]
    assert "Sarah Johnson" not in result["masked_text"]
    assert len(result["mapping"]) >= 3
    assert result["validation_report"]["is_valid"] is True
