"""
Prepare Dataset & Label Mapping Script for PrivMed Gateway
Dataset Candidate: Marawanelbalal/synthetic-pii-phi-v2
"""

import os
import json
from pathlib import Path

# Label Mapping Taxonomy definition mapping dataset labels to internal gateway schema
LABEL_TAXONOMY = {
    "O": 0,
    "B-PATIENT": 1,
    "I-PATIENT": 2,
    "B-DOCTOR": 3,
    "I-DOCTOR": 4,
    "B-LOCATION": 5,
    "I-LOCATION": 6,
    "B-DATE": 7,
    "I-DATE": 8,
    "B-PHONE": 9,
    "I-PHONE": 10,
    "B-EMAIL": 11,
    "I-EMAIL": 12,
    "B-MRN": 13,
    "I-MRN": 14,
    "B-AGE": 15,
    "I-AGE": 16,
    "B-SSN": 17,
    "I-SSN": 18
}

ID_TO_LABEL = {v: k for k, v in LABEL_TAXONOMY.items()}

def save_label_map(output_dir: str = "data"):
    """Saves machine-readable label map to data/label_map.json."""
    os.makedirs(output_dir, exist_ok=True)
    mapping_data = {
        "label_to_id": LABEL_TAXONOMY,
        "id_to_label": ID_TO_LABEL,
        "num_labels": len(LABEL_TAXONOMY)
    }
    output_path = Path(output_dir) / "label_map.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapping_data, f, indent=2)
    print(f"Successfully saved label map to {output_path} ({len(LABEL_TAXONOMY)} labels).")

if __name__ == "__main__":
    print("Executing PrivMed Gateway Dataset Preparation & Label Taxonomy Generator...")
    save_label_map()
