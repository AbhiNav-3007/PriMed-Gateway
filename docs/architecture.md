# PrivMed Gateway — System Architecture & Data Flow

## 1. Overview

**PrivMed Gateway** is a privacy-preserving clinical AI gateway operating as a security boundary between application clients sending clinical text and downstream foundation Large Language Models (LLMs).

---

## 2. High-Level Architecture Diagram

```
                              ┌──────────────────────┐
                              │     USER / APP       │
                              └──────────┬───────────┘
                                         │
                                         │ Raw Clinical Text
                                         ▼
                              ┌──────────────────────┐
                              │       FastAPI        │
                              │     API Gateway      │
                              │       (api.py)       │
                              └──────────┬───────────┘
                                         │
                                         ▼
                    ┌─────────────────────────────────────────┐
                    │      PHI DE-IDENTIFICATION GATEWAY      │
                    │            (src/gateway.py)             │
                    └──────────────────┬──────────────────────┘
                                       │
                    ┌──────────────────┴──────────────────┐
                    │                                     │
                    ▼                                     ▼
          ┌───────────────────┐                 ┌───────────────────┐
          │  Fine-tuned NER   │                 │ Regex & Presidio  │
          │  Transformer      │                 │ Rule Detector     │
          │(src/detection.py) │                 │(src/detection.py) │
          └─────────┬─────────┘                 └─────────┬─────────┘
                    │                                     │
                    └──────────────────┬──────────────────┘
                                       ▼
                              ┌───────────────────┐
                              │  Entity Resolver  │
                              │  & Confidence     │
                              │ (src/resolver.py) │
                              └─────────┬─────────┘
                                        │
                         ┌──────────────┴──────────────┐
                         │                             │
                         ▼                             ▼
                  HIGH CONFIDENCE                 UNCERTAIN
                         │                             │
                         ▼                             ▼
                    AUTO MASK                    REVIEW QUEUE
                         │
                         ▼
                ┌───────────────────┐
                │ Masking Engine    │
                │ & Date Shifter    │
                │ (src/masking.py)  │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │ De-identified     │
                │ Clinical Text     │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │ Foundation LLM    │
                │ (src/llm_client)  │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │ Rehydration Engine│
                │(src/rehydration)  │
                └─────────┬─────────┘
                          │
                          ▼
                ┌───────────────────┐
                │ Final Response    │
                └───────────────────┘
```

---

## 3. End-to-End Data Flow

1. **Input Ingestion & Validation**: Raw text received via `deidentify(text)` or FastAPI `POST /process`.
2. **Parallel Detection**:
   - Transformer NER predicts token-level BIO tags for narrative entity types.
   - Regex engine scans text for structured identifier patterns (phone, email, SSN, MRN, IP, URLs, dates).
3. **Entity Resolution**: Overlapping spans are resolved using precedence rules, duplicate spans merged, and confidence scores calculated.
4. **Masking & Secure Mapping**:
   - Entities replaced with consistent placeholders (`<PATIENT_NAME_001>`).
   - Relative date shifting applied if enabled.
   - Mapping dictionary stored strictly in memory inside gateway instance.
5. **LLM Execution**: De-identified text forwarded to local Ollama / small LLM model.
6. **Rehydration**: LLM response placeholders validated and rehydrated back to original identifiers using session mapping. Unknown placeholders are safely preserved or flagged.
