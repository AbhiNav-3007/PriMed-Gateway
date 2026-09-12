# PrivMed Gateway — Architectural Decision Log (ADR)

This document tracks all major technical and architectural decisions made throughout the development of **PrivMed Gateway**. Each decision includes the context, chosen option, rationale, alternatives considered, and interview defense keypoints.

---

## ADR-001: Hybrid Detection Gateway Architecture (ML + Regex + Presidio Baseline)

- **Date**: 2026-09-12
- **Status**: Approved
- **Context**: The assessment requires detecting PHI/PII across all 18 HIPAA Safe Harbor categories without relying solely on standard token classification (which cannot naturally detect structured IDs like IP, SSN, URLs without dedicated data, or non-text modalities).
- **Decision**: Implement a **Hybrid Gateway Architecture**:
  1. Fine-tuned Transformer Token-Classification model (≤1B parameters) for narrative entities (Names, Locations, Organizations, Occupations).
  2. Deterministic Regex & Rule-based Detectors for structured patterns (SSN, Phone, Email, IP, URL, MRN, Dates).
  3. Microsoft Presidio as an independent baseline comparison framework.
  4. Entity Resolver with multi-source confidence merging.
- **Rationale**: Combining ML and deterministic rules guarantees maximum Recall (minimizing false negatives/privacy breaches) while accurately covering all Safe Harbor categories.
- **Interview Defense Note**: "Rather than forcing an NER model to detect explicit patterns like IP addresses or SSNs, we used regex rules for structured patterns and reserve the transformer model for contextual narrative entities. This hybrid design maximizes overall recall and precision."

---

## ADR-002: Consistent Typed Pseudonymization vs Generic Redaction

- **Date**: 2026-09-12
- **Status**: Approved
- **Context**: Replacing PHI with generic `[REDACTED]` destroys co-reference resolution and temporal/clinical relationship understanding for downstream LLMs.
- **Decision**: Adopt **Consistent Typed Pseudonymization** (`<PATIENT_NAME_001>`, `<LOCATION_001>`, `<DATE_001>`).
- **Rationale**: Repeated mentions of the same patient (e.g. "John Smith ... Mr. Smith") map to the exact same key (`<PATIENT_NAME_001>`), preserving context for downstream LLM reasoning while allowing seamless round-trip rehydration.
- **Interview Defense Note**: "Generic redaction (`[REDACTED]`) breaks entity resolution for foundation models. Consistent pseudonymization preserves entity identity across long clinical notes while keeping sensitive values strictly inside the gateway."

---

## ADR-003: Simplified Flat Repository Layout

- **Date**: 2026-09-12
- **Status**: Approved
- **Context**: Deeply nested multi-layered folder structures introduce cognitive friction and unnecessary complexity for a single-engineer assignment.
- **Decision**: Use a flat, intuitive structure (`src/` for core modules, `api.py` for FastAPI, `app.py` for Streamlit, `train.py` for training, `evaluate.py` for benchmarks).
- **Rationale**: Keeps the codebase clean, readable, and 100% focused on key assessment deliverables.
- **Interview Defense Note**: "We designed a modular Python package in `src/` where each module maps 1:1 to a gateway component, avoiding unnecessary abstraction layers."
