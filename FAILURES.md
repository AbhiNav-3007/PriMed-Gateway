# PrivMed Gateway — Development Failures, Edge Cases & Trade-offs (FAILURES.md)

> **Document Purpose**: This engineering document records technical failure modes, architectural trade-offs, edge cases, and lessons learned during the development and hardening of PrivMed Gateway.


---

## 1. Architectural & Model Failures

### 1.1 Model Version Mismatch & Custom Pipeline Deserialization Failure
- **Symptom**: Fine-tuning BERT-base Token Classification on Kaggle (`transformers v5.0.0`) caused `transformers.pipeline("ner", model=...)` to throw `cannot import name 'pipeline' from 'transformers'` when loaded locally on `transformers v4.37.2`.
- **Root Cause**: HuggingFace `pipeline()` auto-detection relies on version-specific model config keys that failed schema validation across major library versions.
- **Resolution**: Replaced high-level `pipeline()` auto-loader with direct instantiation using `AutoTokenizer` and `AutoModelForTokenClassification.from_pretrained(..., ignore_mismatched_sizes=True)`.

### 1.2 Unbracketed Placeholder Regex Collision Trap
- **Symptom**: `PlaceholderValidator` flagged valid bracketed tokens like `<PATIENT_NAME_001>` as malformed placeholders.
- **Root Cause**: The unbracketed regex `\b[A-Z_]+_\d{3}\b` matched the inner string `PATIENT_NAME_001` inside `<PATIENT_NAME_001>` because regex word-boundaries (`\b`) match right between non-word `<` and word-character `P`.
- **Resolution**: Updated the regex with negative lookbehind and lookahead assertions: `(?<!<)\b[A-Z_]+_\d{3}\b(?!>)`.

---

## 2. LLM & Rehydration Failures

### 2.1 System Instruction Example Placeholder Collision
- **Symptom**: When running offline mock LLM integration, `<PATIENT_NAME_001>` was flagged as an `UNKNOWN_PLACEHOLDER`.
- **Root Cause**: `MockLLMClient` echoed the prompt preamble containing example placeholders (`(e.g. <PATIENT_NAME_001>)`), causing the validator to scan example text as unmapped output tokens.
- **Resolution**: Updated prompt preambles to use `_000` index convention (`<PATIENT_NAME_000>`) so system examples never collide with 1-indexed document placeholders (`001`, `002`).

### 2.2 Gemini Model Version Deprecation (404 Error)
- **Symptom**: Calls to Google Gemini API returned `HTTP 404: models/gemini-1.5-flash is not found for API version v1beta`.
- **Root Cause**: Google deprecated `gemini-1.5-flash` endpoint URLs on v1beta Generative Language API.
- **Resolution**: Updated `GeminiLLMClient` model endpoint to `gemini-3.6-flash`.

---

## 3. Trade-offs & Limitations

### 3.1 Surface Form Disambiguation vs False Merges
- **Trade-off**: When a document contains `"Marcus Whitfield"`, `"Marcus D."`, and `"Whitfield"`, attempting heuristic fuzzy matching risks incorrectly merging two distinct individuals (e.g. father and son or doctor and patient sharing a surname).
- **Decision**: PrivMed Gateway maintains strict exact-string mapping consistency (`value_to_placeholder`). Distinct surface forms remain separate unless identity is guaranteed by explicit entity spans.

### 3.2 Recall Asymmetry in PHI Redaction
- **Trade-off**: A false negative (missing PHI) is a HIPAA compliance breach, while a false positive (over-redacting clinical text) reduces utility.
- **Decision**: Weighted candidate precedence (Regex = 10, Transformer = 6, Presidio = 5) and confidence thresholds to heavily favor high recall for sensitive categories (SSN, Phone, MRN, Email).
