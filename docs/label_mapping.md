# PrivMed Gateway — Stage 3: Label Taxonomy & BIO Mapping Design

This document details the internal Named Entity Recognition (NER) label taxonomy, BIO token representation, and how entities map to HIPAA Safe Harbor categories.

---

## 1. BIO Labeling Scheme Explanation

We use the standard **BIO (Beginning, Inside, Outside)** token labeling format for token classification:
- **`B-<ENTITY>`**: Indicates the **Beginning** token of a PHI entity span (e.g. "John" in "John Smith").
- **`I-<ENTITY>`**: Indicates an **Inside** token continuing a multi-token PHI entity span (e.g. "Smith" in "John Smith").
- **`O`**: Indicates tokens **Outside** any PHI entity (regular clinical text).

---

## 2. Label Map Schema (`label_map.json`)

| ID | BIO Label | Entity Description | Target HIPAA Category |
|---|---|---|---|
| 0 | `O` | Non-PHI Clinical Text | None |
| 1 | `B-PATIENT` | Beginning of Patient Name | 1. Names |
| 2 | `I-PATIENT` | Inside of Patient Name | 1. Names |
| 3 | `B-DOCTOR` | Beginning of Healthcare Provider Name | 1. Names |
| 4 | `I-DOCTOR` | Inside of Healthcare Provider Name | 1. Names |
| 5 | `B-LOCATION` | Beginning of Address/City/Zip | 2. Geographic Subdivisions |
| 6 | `I-LOCATION` | Inside of Address/City/Zip | 2. Geographic Subdivisions |
| 7 | `B-DATE` | Beginning of Date/DOB/Admission | 3. Dates & Ages >89 |
| 8 | `I-DATE` | Inside of Date/DOB/Admission | 3. Dates & Ages >89 |
| 9 | `B-PHONE` | Beginning of Phone Number | 4. Telephone Numbers |
| 10 | `I-PHONE` | Inside of Phone Number | 4. Telephone Numbers |
| 11 | `B-EMAIL` | Beginning of Email Address | 6. Email Addresses |
| 12 | `I-EMAIL` | Inside of Email Address | 6. Email Addresses |
| 13 | `B-MRN` | Beginning of Medical Record Number | 8. Medical Record Numbers |
| 14 | `I-MRN` | Inside of Medical Record Number | 8. Medical Record Numbers |
| 15 | `B-AGE` | Beginning of Patient Age (>89) | 3. Dates & Ages >89 |
| 16 | `I-AGE` | Inside of Patient Age (>89) | 3. Dates & Ages >89 |
| 17 | `B-SSN` | Beginning of Social Security Number | 7. Social Security Numbers |
| 18 | `I-SSN` | Inside of Social Security Number | 7. Social Security Numbers |

Total Labels: **19**

---

## 3. Subword Alignment Strategy (Fast Tokenizer Offset Mapping)

Transformer tokenizers (WordPiece / Byte-Pair Encoding) split words into subwords (e.g. `Parkinson` → `Park`, `##in`, `##son`).
Our alignment rule:
- Assign the target BIO label (e.g., `B-PATIENT`) to the **first subword** of an entity.
- Assign `I-PATIENT` or `-100` (PyTorch CrossEntropy loss ignore index) to subsequent subwords so loss is calculated accurately without label noise.
