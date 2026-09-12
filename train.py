"""
PrivMed Gateway — Model Training & Fine-Tuning Script (train.py)
Designed for execution on Kaggle / Google Colab Free T4 GPU.
"""

import os
import argparse
import json
import torch
import numpy as np
from datasets import load_dataset
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    TrainingArguments,
    Trainer,
    DataCollatorForTokenClassification
)
from seqeval.metrics import precision_score, recall_score, f1_score, classification_report


def count_parameters(model):
    """Calculates exact total and trainable parameters of PyTorch model."""
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return total_params, trainable_params


def parse_args():
    parser = argparse.ArgumentParser(description="PrivMed Gateway Transformer NER Fine-Tuning")
    parser.add_argument("--model_name", type=str, default="dslim/bert-base-NER", help="Pretrained base model name")
    parser.add_argument("--dataset_name", type=str, default="Marawanelbalal/synthetic-pii-phi-v2", help="Hugging Face dataset name")
    parser.add_argument("--output_dir", type=str, default="./model_output", help="Output directory for fine-tuned model")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--batch_size", type=int, default=16, help="Batch size per GPU")
    parser.add_argument("--learning_rate", type=float, default=3e-5, help="Learning rate")
    parser.add_argument("--max_length", type=int, default=256, help="Maximum token sequence length")
    return parser.parse_args()


def main():
    args = parse_args()

    print("=" * 60)
    print("PRIVMED GATEWAY — TRANSFORMER NER FINE-TUNING PIPELINE")
    print(f"Base Model: {args.model_name}")
    print(f"Dataset:    {args.dataset_name}")
    print("=" * 60)

    # 1. Load Tokenizer & Model
    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    
    # Load label map
    label_map_path = "data/label_map.json"
    if os.path.exists(label_map_path):
        with open(label_map_path, "r", encoding="utf-8") as f:
            label_data = json.load(f)
        label_to_id = label_data["label_to_id"]
        id_to_label = {int(k): v for k, v in label_data["id_to_label"].items()}
    else:
        # Fallback standard labels
        label_to_id = {"O": 0, "B-PATIENT": 1, "I-PATIENT": 2, "B-LOCATION": 3, "I-LOCATION": 4, "B-DATE": 5, "I-DATE": 6}
        id_to_label = {v: k for k, v in label_to_id.items()}

    model = AutoModelForTokenClassification.from_pretrained(
        args.model_name,
        num_labels=len(label_to_id),
        id2label=id_to_label,
        label2id=label_to_id,
        ignore_mismatched_sizes=True
    )

    # 2. Calculate Exact Parameter Count (MANDATORY REQUIREMENT)
    total_params, trainable_params = count_parameters(model)
    print(f"\n[EXACT PARAMETER COUNT]")
    print(f"  Total Parameters:     {total_params:,}")
    print(f"  Trainable Parameters: {trainable_params:,}")
    print(f"  Parameter Limit Check: {'PASS (<= 1B)' if total_params <= 1_000_000_000 else 'FAIL (> 1B)'}\n")

    print("[Info] Training setup complete. Upload this script to Kaggle/Colab for GPU acceleration.")

if __name__ == "__main__":
    main()
