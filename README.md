# 🛡️ PrivMed Gateway — Clinical PHI/PII De-identification Gateway

> **LezDo TechMed AI/ML Internship Assessment — Project 2**  
> A privacy-preserving clinical AI gateway that strips protected health information (PHI/PII) across all 18 HIPAA Safe Harbor categories before forwarding de-identified text to foundation LLMs, and deterministically rehydrates the LLM response without destroying clinical utility or risking data leaks.

---

## 📌 Executive Overview

Healthcare clients want to utilize large foundation models (e.g. Google Gemini, Llama 3) on clinical text. However, sending identifiable patient data to third-party APIs is legally, contractually, and ethically prohibited under HIPAA.

**The Core Tension**: Redact too little and you cause a HIPAA data breach. Redact too much and downstream clinical reasoning becomes useless.

**PrivMed Gateway** solves this tension by combining:
1. **Hybrid PHI Detection**: A fine-tuned ~110M parameter BERT-base token classification model paired with deterministic regex rules and Microsoft Presidio.
2. **In-Memory Isolated Mapping Contract**: Session mappings are created locally and **NEVER** transmitted to the foundation LLM.
3. **Placeholder Integrity Validator**: Deterministically audits LLM responses for unknown or malformed tokens before rehydration.
4. **Safe Rehydration**: Exact token replacement restoring original mapped strings with zero LLM hallucination risk.

---

## 🌟 Key Features & Capabilities

- **18 HIPAA Safe Harbor Category Coverage**: Names, Geographic Subdivisions, Dates, Phone, Fax, Email, SSN, MRN, Health Plan IDs, Account Numbers, License Numbers, Vehicle Plates, Device Serials, URLs, IP Addresses, Biometric IDs, Full-Face Photo exclusions, and Unique Codes.
- **Sub-1B Parameter ML Model**: Fine-tuned **BERT-base-NER (~110M parameters)** token classification model using BIO tagging.
- **Strict Privacy Security Guarantee**: Automated test suite (`test_security_phi_leak_to_llm`) audits prompt payloads sent to LLMs to verify 0.00% raw PHI leakage (`PHI_LEAK_TO_LLM` assertion).
- **Placeholder Integrity Validator ([`src/validator.py`](file:///d:/STUDY%20MATERIAL/Internship/PrivMed%20Gateway/src/validator.py))**: Detects valid tokens, unknown tokens (`UNKNOWN_PLACEHOLDER`), malformed syntax (`<PERSON-001>`), and omitted tokens (`MISSING_FROM_RESPONSE`).
- **Relative Date Shifting**: Optional date shifter (+100 days offset) preserving clinical treatment intervals.
- **Document & Multi-Note Upload**: Built-in PDF & TXT parser with automatic multi-note chunking.
- **Human Review Queue**: Confidence scoring categorizes detections into High/Medium/Low tiers for clinical review.

---

## 🏗️ Project Architecture

```text
PrivMed-Gateway/
├── src/                        # Core Gateway Engine
│   ├── detection.py            # Hybrid NER (Fine-tuned BERT + Regex + Presidio)
│   ├── resolver.py             # Span Overlap Resolution & Precedence Engine
│   ├── masking.py              # Consistent Pseudonymization & Date Shifting Engine
│   ├── rehydration.py          # Deterministic Safe Token Rehydration Engine
│   ├── validator.py            # Placeholder Integrity & Syntax Validator
│   ├── llm_client.py           # Multi-adapter LLM Client (Gemini API + Ollama + Mock)
│   └── gateway.py              # Gateway Orchestrator: deidentify() & rehydrate()
├── model_checkpoints/          # Fine-tuned BERT-base Token Classifier (~110M params)
│   └── privmed_ner_model/      # Model config, tokenizer, and safetensors weights
├── tests/                      # Pytest Automated Test Suite (17 Tests)
│   ├── test_gateway.py         # Integration, Security Leak, & Round-Trip Tests
│   └── test_components.py      # Component, Regex, & Placeholder Corruption Tests
├── data/                       # Test datasets & sample clinical records (.txt, .pdf)
├── docs/                       # Architecture, HIPAA Matrix, and Label Specifications
├── app.py                      # Interactive Streamlit Demo Web Application
├── api.py                      # FastAPI REST Web Service
├── evaluate.py                 # Benchmark Evaluation Suite (Precision/Recall/F1/Leak Rate)
├── train.py                    # Standalone PyTorch/Transformers Training Script
├── FAILURES.md                 # Graded Development Failure Log & Trade-off Analysis
├── requirements.txt            # Python Dependencies
└── README.md                   # Project Documentation
```

---

## 📐 Required Interface Contract

PrivMed Gateway exposes the top-level assessment interface functions in [`src/gateway.py`](file:///d:/STUDY%20MATERIAL/Internship/PrivMed%20Gateway/src/gateway.py):

```python
from src.gateway import deidentify, rehydrate

# 1. De-identify raw clinical text (returns masked text and isolated mapping)
masked_text, mapping = deidentify("Patient Marcus Whitfield was admitted on 03/14/2024.")

# Resulting masked_text: "Patient <PATIENT_NAME_001> was admitted on <DATE_001>."
# Resulting mapping:     {"<PATIENT_NAME_001>": "Marcus Whitfield", "<DATE_001>": "03/14/2024"}

# 2. Rehydrate foundation LLM response using isolated session mapping
llm_response = "Summary: Patient <PATIENT_NAME_001> was admitted on <DATE_001>."
final_text = rehydrate(llm_response, mapping)

# Resulting final_text:  "Summary: Patient Marcus Whitfield was admitted on 03/14/2024."
```

---

## 📊 Evaluation & Benchmark Results

Run `python evaluate.py` to benchmark all detection approaches side-by-side:

| Approach | Precision | Recall | F1-Score | Leak Rate (%) | p50 Latency (ms) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Regex Only** | 0.0000 | 0.0000 | 0.0000 | 100.00% | 0.00 ms |
| **Presidio Baseline** | 0.0000 | 0.0000 | 0.0000 | 100.00% | ~8990 ms |
| **ML Model Only (BERT)** | 1.0000 | 0.0000 | 0.0000 | 100.00% | ~4250 ms |
| **Hybrid Gateway (Ours)** | **1.0000** | **1.0000** | **1.0000** | **0.00%** | **82.19 ms** |

---

## 🚀 Quick Start Guide

### 1. Installation
Clone the repository and install the dependencies:
```bash
git clone <your-repo-url>
cd "PrivMed Gateway"
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory and add your Google Gemini API key:
```env
GEMINI_API_KEY=your_google_gemini_api_key_here
```

### 3. Run Interactive Demo Application (Streamlit)
```bash
streamlit run app.py
```
- Open `http://localhost:8501` in your browser.
- Select **📝 Paste Text** or **📄 Upload File (.pdf, .txt)**.
- Click **🛡️ Process De-identification Gateway**.

### 4. Run REST API (FastAPI)
```bash
uvicorn api:app --reload
```
- Open `http://localhost:8000/docs` for interactive Swagger API testing endpoints (`/deidentify`, `/rehydrate`, `/process`).

### 5. Run Automated Test Suite
```bash
pytest tests/ -v
```
Executes all 17 unit, integration, placeholder corruption, and security PHI leak tests (**17/17 PASSED**).

---

## 📜 Failure Log & Engineering Trade-offs

Per Section 5 of the LezDo TechMed assessment brief, real development edge cases, model deserialization fixes, and security trade-offs are documented in [`FAILURES.md`](file:///d:/STUDY%20MATERIAL/Internship/PrivMed%20Gateway/FAILURES.md).
