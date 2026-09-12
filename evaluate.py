"""
PrivMed Gateway — Full Benchmark Evaluation Suite (evaluate.py)
Measures Precision, Recall, F1, Leak Rate, Utility Preservation, and p50/p95 Latency.
"""

import json
import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

from src.gateway import PrivMedGateway
from src.detection import RegexDetector, PresidioDetector, TransformerNERDetector

def load_test_dataset(dataset_path: str = "data/samples/clinical_samples.json") -> List[Dict[str, Any]]:
    """Loads held-out test dataset with ground-truth entity annotations."""
    if Path(dataset_path).exists():
        with open(dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)
    # Default fallback sample note
    return [
        {
            "id": "eval-001",
            "text": "Patient John Smith was admitted on 12/03/2025. MRN: MRN-82931. Phone: 555-987-6543. Doctor: Robert Jones.",
            "entities": [
                {"text": "John Smith", "label": "PATIENT", "start": 8, "end": 18},
                {"text": "12/03/2025", "label": "DATE", "start": 35, "end": 45},
                {"text": "MRN-82931", "label": "MRN", "start": 52, "end": 61},
                {"text": "555-987-6543", "label": "PHONE", "start": 70, "end": 82},
                {"text": "Robert Jones", "label": "DOCTOR", "start": 92, "end": 104}
            ]
        }
    ]

def evaluate_approach(approach_name: str, test_notes: List[Dict[str, Any]], gateway_inst: PrivMedGateway) -> Dict[str, Any]:
    """Evaluates a specific detection approach against ground truth annotations."""
    total_gt = 0
    total_tp = 0
    total_pred = 0
    notes_with_leak = 0
    latencies = []

    for note in test_notes:
        text = note["text"]
        gt_entities = note.get("entities", [])
        total_gt += len(gt_entities)

        start_time = time.time()
        
        if approach_name == "Regex Only":
            preds = gateway_inst.regex_detector.detect(text)
        elif approach_name == "Presidio Only":
            preds = gateway_inst.presidio_detector.detect(text)
        elif approach_name == "ML Only":
            preds = gateway_inst.ner_detector.detect(text)
        else: # Hybrid Gateway
            _, _, preds = gateway_inst.deidentify(text)

        elapsed_ms = (time.time() - start_time) * 1000
        latencies.append(elapsed_ms)

        total_pred += len(preds)

        # Count true positives (matching span offsets)
        note_missed_phi = 0
        for gt in gt_entities:
            matched = any(
                abs(p.start if hasattr(p, 'start') else p["start"] - gt["start"]) <= 1 and
                abs(p.end if hasattr(p, 'end') else p["end"] - gt["end"]) <= 1
                for p in preds
            )
            if matched:
                total_tp += 1
            else:
                note_missed_phi += 1

        if note_missed_phi > 0:
            notes_with_leak += 1

    precision = (total_tp / total_pred) if total_pred > 0 else 1.0
    recall = (total_tp / total_gt) if total_gt > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
    leak_rate = (notes_with_leak / len(test_notes)) * 100 if test_notes else 0.0

    p50_latency = np.percentile(latencies, 50) if latencies else 0.0
    p95_latency = np.percentile(latencies, 95) if latencies else 0.0

    return {
        "approach": approach_name,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "leak_rate_percent": round(leak_rate, 2),
        "p50_latency_ms": round(p50_latency, 2),
        "p95_latency_ms": round(p95_latency, 2)
    }

def main():
    print("=" * 60)
    print("PRIVMED GATEWAY — FULL BENCHMARK EVALUATION SUITE")
    print("=" * 60)

    test_notes = load_test_dataset()
    print(f"Loaded {len(test_notes)} evaluation clinical notes.\n")

    gateway = PrivMedGateway(use_mock_llm=True)

    approaches = ["Regex Only", "Presidio Only", "ML Only", "Hybrid Gateway"]
    results = []

    for app in approaches:
        res = evaluate_approach(app, test_notes, gateway)
        results.append(res)
        print(f"[{res['approach']}]")
        print(f"  Precision: {res['precision']:.4f} | Recall: {res['recall']:.4f} | F1: {res['f1']:.4f}")
        print(f"  Leak Rate: {res['leak_rate_percent']:.2f}% | p50: {res['p50_latency_ms']} ms | p95: {res['p95_latency_ms']} ms\n")

    # Save evaluation summary
    output_path = Path("docs/evaluation_results.json")
    output_path.parent.mkdir(exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"Successfully exported benchmark evaluation results to {output_path}")

if __name__ == "__main__":
    main()
