# PrivMed Gateway — Stage 1: Dataset Inspection & Discovery Report

## 1. Candidate Dataset Overview

- **Dataset Name**: `Marawanelbalal/synthetic-pii-phi-v2`
- **Source**: Hugging Face Datasets Hub (`https://huggingface.co/datasets/Marawanelbalal/synthetic-pii-phi-v2`)
- **License**: Open / Permissive (Synthetic Data for Research & Educational Use)
- **Modality**: Text with entity annotations / token-level tags
- **Primary Purpose**: Training token classification NER models to identify personal and health identifiers in synthetic clinical narratives.

---

## 2. Key Dataset Characteristics

1. **Synthetic Nature**: 100% synthetically generated to avoid real patient data leakage risks.
2. **Clinical & PII Text Diversity**: Contains synthetic doctor-patient notes, admission summaries, and administrative records.
3. **Annotation Format**: Spans and token-level tags (Names, Dates, Locations, Phone Numbers, Social Security Numbers, Email Addresses, MRNs).

---

## 3. Pre-Training Analysis & Considerations

- **Taxonomy Alignment**: Synthetic PII/PHI datasets cover standard categories (Names, Dates, Addresses, Phone, SSN, MRN) but do not naturally contain non-narrative or technical patterns (IP addresses, URLs, device serial numbers, vehicle plates).
- **Hybrid Strategy Mandate**: We will train the Transformer NER model on narrative entities (Names, Dates, Locations, Medical Record Numbers, Phone/Email) while using deterministic regex engines for explicit patterns (IPs, URLs, SSNs, Account Numbers).
