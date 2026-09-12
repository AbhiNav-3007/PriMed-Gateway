# PrivMed Gateway — 18 HIPAA Safe Harbor Category Coverage Matrix

This document maps all 18 HIPAA Safe Harbor categories to their specific detection strategy within the **PrivMed Gateway** hybrid architecture.

| # | HIPAA Safe Harbor Category | Detection Strategy | ML NER Support | Regex / Rule Support | Modality / Handling Notes |
|---|----------------------------|--------------------|----------------|----------------------|---------------------------|
| 1 | **Names** | Hybrid (ML + Rules) | **Yes** (`PATIENT`, `DOCTOR`) | Yes (Contextual titles `Dr.`, `Mr.`) | Full names, surnames, nicknames in narrative. |
| 2 | **Geographic Subdivisions < State** | Hybrid (ML + Rules) | **Yes** (`LOCATION`, `ADDRESS`) | Yes (Zip codes, street patterns) | Cities, counties, street addresses, zip codes. |
| 3 | **Dates (Birth, Admission, Discharge, Age >89)** | Hybrid (ML + Date Shifter) | **Yes** (`DATE`) | Yes (Regex date parsers `MM/DD/YYYY`, relative dates) | Full dates & ages >89. Supported by relative date shifting engine. |
| 4 | **Telephone Numbers** | Hybrid (Regex + ML) | Yes (`PHONE`) | **Yes** (`\d{3}[-\.\s]??\d{3}[-\.\s]??\d{4}`) | Standard US/international phone formats. |
| 5 | **Fax Numbers** | Hybrid (Regex + ML) | Yes (`PHONE`/`FAX`) | **Yes** (`FAX:\s*...`) | Contextual keyword detection + phone regex. |
| 6 | **Email Addresses** | Hybrid (Regex + ML) | Yes (`EMAIL`) | **Yes** (`[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}`) | Standard RFC email patterns. |
| 7 | **Social Security Numbers (SSN)** | Deterministic Regex | Optional (`SSN`) | **Yes** (`\b\d{3}-\d{2}-\d{4}\b`) | Strict SSN pattern validation. |
| 8 | **Medical Record Numbers (MRN)** | Hybrid (ML + Regex) | **Yes** (`MRN`) | **Yes** (`MRN[-\s]?\d+`) | Common clinical MRN headers and number formats. |
| 9 | **Health Plan Beneficiary Numbers** | Deterministic Regex | Optional | **Yes** (Member/Group ID patterns) | Structured insurance & policy identifiers. |
| 10 | **Account Numbers** | Deterministic Regex | Optional | **Yes** (Account # patterns) | Financial & clinical billing account numbers. |
| 11 | **Certificate / License Numbers** | Deterministic Regex | Optional | **Yes** (License # patterns) | Medical license & state registration IDs. |
| 12 | **Vehicle Identifiers & License Plates** | Deterministic Regex | Optional | **Yes** (Plate / VIN patterns) | VIN numbers & vehicle plate patterns. |
| 13 | **Device Identifiers & Serial Numbers** | Deterministic Regex | Optional | **Yes** (Serial # patterns) | Pacemaker, pump, and device serial numbers. |
| 14 | **URLs (Web Address)** | Deterministic Regex | Optional | **Yes** (`https?://\S+`) | Web links and portal URLs. |
| 15 | **IP Addresses** | Deterministic Regex | Optional | **Yes** (`\b\d{1,3}(\.\d{1,3}){3}\b`) | IPv4 and IPv6 network addresses. |
| 16 | **Biometric Identifiers** | Textual Representation | N/A | **Yes** (Textual fingerprint/gene refs) | Plain-text references only; media scans outside scope. |
| 17 | **Full-Face Photos / Images** | Explicit Documented Exclusion | N/A | N/A | Non-text modality; documented as out-of-scope for text gateway. |
| 18 | **Other Unique Identifying Numbers** | Contextual Rules | Yes | **Yes** (General ID patterns) | Any unique alphanumeric codes matching contextual headers. |

---

## Technical Summary of Coverage

- **ML NER Supported Categories**: Names, Geographic Subdivisions, Dates, Phone Numbers, Email, MRNs.
- **Regex / Deterministic Supported Categories**: SSNs, Fax, URLs, IPs, Health Plan #, Account #, License #, Vehicle IDs, Device Serials, Biometric Text refs.
- **Explicit Non-Text Exclusions**: Full-face images / raw binary media (Explicitly documented as non-text modality).
