"""
PrivMed Gateway — Detection Engine Module
Includes Regex Detector, Transformer NER Inference Detector, and Presidio Baseline Detector.
"""

import os
import re
from typing import List, Dict, Any, Tuple

class EntitySpan:
    """Represents a detected PHI/PII entity span in text."""
    def __init__(self, text: str, label: str, start: int, end: int, confidence: float = 1.0, detector_source: str = "REGEX"):
        self.text = text
        self.label = label
        self.start = start
        self.end = end
        self.confidence = confidence
        self.detector_source = detector_source

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "label": self.label,
            "start": self.start,
            "end": self.end,
            "confidence": self.confidence,
            "detector_source": self.detector_source
        }

    def __repr__(self):
        return f"<EntitySpan {self.label}: '{self.text}' [{self.start}:{self.end}] (conf={self.confidence:.2f}, source={self.detector_source})>"


class RegexDetector:
    """Deterministic Regex & Rule-based Detector for structured identifiers."""

    PATTERNS = {
        "EMAIL": r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b',
        "PHONE": r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b',
        "SSN": r'\b\d{3}-\d{2}-\d{4}\b',
        "IP_ADDRESS": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        "URL": r'\bhttps?://[^\s/$.?#].[^\s]*\b',
        "MRN": r'\bMRN[-\s:]*\d+[A-Za-z0-9-]*\b',
        "DATE": r'\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})\b'
    }

    def __init__(self):
        self.compiled_patterns = {label: re.compile(pat, re.IGNORECASE) for label, pat in self.PATTERNS.items()}

    def detect(self, text: str) -> List[EntitySpan]:
        entities = []
        for label, pattern in self.compiled_patterns.items():
            for match in pattern.finditer(text):
                entity = EntitySpan(
                    text=match.group(0),
                    label=label,
                    start=match.start(),
                    end=match.end(),
                    confidence=1.0,
                    detector_source="REGEX"
                )
                entities.append(entity)
        return entities


class PresidioDetector:
    """Baseline Detector using Microsoft Presidio Analyzer."""

    def __init__(self):
        self.analyzer = None
        self._initialized = False

    def _lazy_init(self):
        if not self._initialized:
            try:
                from presidio_analyzer import AnalyzerEngine
                self.analyzer = AnalyzerEngine()
                self._initialized = True
            except Exception as e:
                self._initialized = False

    def detect(self, text: str) -> List[EntitySpan]:
        self._lazy_init()
        if not self.analyzer:
            return []
        
        try:
            results = self.analyzer.analyze(text=text, language="en")
            entities = []
            for res in results:
                entities.append(EntitySpan(
                    text=text[res.start:res.end],
                    label=res.entity_type,
                    start=res.start,
                    end=res.end,
                    confidence=res.score,
                    detector_source="PRESIDIO"
                ))
            return entities
        except Exception:
            return []


class TransformerNERDetector:
    """Transformer Token-Classification Model Detector (≤1B parameters)."""

    STOP_WORDS = {"TELEMETRY", "TELEMETRY IP", "TELEMET", "RECORDED", "REC", "IP", "MRN", "IS", "HIS", "ON", "IN", "AT", "TWO", "WEEKS", "DAYS", "WITH", "SUFFERING", "HAS"}

    def __init__(self, model_name_or_path: str = "./model_checkpoint/privmed_ner_model/privmed_ner_model"):
        # Auto-detect local custom checkpoint paths
        candidate_paths = [
            "./model_checkpoint/privmed_ner_model/privmed_ner_model",
            "./model_checkpoint/privmed_ner_model",
            "./model_checkpoints/privmed_ner_model",
            "dslim/bert-base-NER"
        ]
        
        chosen_path = "dslim/bert-base-NER"
        for cp in candidate_paths:
            if os.path.exists(cp):
                chosen_path = cp
                break
        
        self.model_name_or_path = chosen_path
        self.pipeline = None
        self._loaded = False

    def load_model(self):
        if not self._loaded:
            try:
                from transformers import AutoModelForTokenClassification, AutoTokenizer, pipeline
                tokenizer = AutoTokenizer.from_pretrained(
                    self.model_name_or_path,
                    use_fast=True,
                    local_files_only=True
                )
                model = AutoModelForTokenClassification.from_pretrained(
                    self.model_name_or_path,
                    local_files_only=True,
                    ignore_mismatched_sizes=True
                )
                self.pipeline = pipeline(
                    "ner",
                    model=model,
                    tokenizer=tokenizer,
                    aggregation_strategy="simple"
                )
                self._loaded = True
                print(f"[TransformerNERDetector] Loaded fine-tuned model from: {self.model_name_or_path}")
            except Exception as e:
                raise RuntimeError(
                    f"[TransformerNERDetector] Failed to load model from '{self.model_name_or_path}': {e}"
                )

    def detect(self, text: str) -> List[EntitySpan]:
        if not self._loaded:
            self.load_model()
        if not self.pipeline:
            return []

        try:
            raw_predictions = self.pipeline(text)
            entities = []
            for pred in raw_predictions:
                word = pred["word"].replace("##", "").strip()
                score = float(pred["score"])
                
                if score < 0.60 or word.upper() in self.STOP_WORDS or len(word) < 2:
                    continue

                label = pred.get("entity_group", pred.get("entity", "O")).upper()
                
                if label in ["PER", "PERSON", "PATIENT"]:
                    start_idx = pred["start"]
                    pre_text = text[max(0, start_idx-15):start_idx].upper()
                    if "DR." in pre_text or "DOCTOR" in pre_text:
                        mapped_label = "DOCTOR"
                    else:
                        mapped_label = "PATIENT"
                elif label in ["LOC", "LOCATION"]:
                    mapped_label = "LOCATION"
                elif label in ["ORG", "ORGANIZATION"]:
                    mapped_label = "LOCATION"
                elif label in ["DATE", "AGE", "EMAIL", "PHONE", "MRN", "SSN"]:
                    mapped_label = label
                else:
                    continue

                entities.append(EntitySpan(
                    text=word,
                    label=mapped_label,
                    start=pred["start"],
                    end=pred["end"],
                    confidence=score,
                    detector_source="NER_TRANSFORMER"
                ))
            return entities
        except Exception as e:
            print(f"[TransformerNERDetector] Inference error: {e}")
            return []
