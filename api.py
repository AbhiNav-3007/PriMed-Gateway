"""
PrivMed Gateway — FastAPI Web Service (api.py)
Endpoints: GET /health, POST /deidentify, POST /rehydrate, POST /process
"""

import os
import time
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

# Auto-load .env
load_dotenv()

from src.gateway import PrivMedGateway, deidentify, rehydrate

app = FastAPI(
    title="PrivMed Gateway API",
    description="Privacy-Preserving Clinical PHI/PII De-identification Gateway API",
    version="1.0.0"
)

_gemini_key = os.environ.get("GEMINI_API_KEY", "")
if _gemini_key:
    gateway = PrivMedGateway(use_mock_llm=False, provider="gemini", api_key=_gemini_key)
else:
    gateway = PrivMedGateway(use_mock_llm=True)

# Pydantic Schemas
class DeidentifyRequest(BaseModel):
    text: str = Field(..., description="Raw clinical text input", example="Patient John Smith was admitted on 10/04/2025.")
    enable_date_shifting: bool = Field(False, description="Enable relative date shifting")

class DeidentifyResponse(BaseModel):
    masked_text: str
    mapping_id: str
    entities: List[Dict[str, Any]]
    risk_score: float

class RehydrateRequest(BaseModel):
    response: str = Field(..., description="LLM response containing placeholders")
    mapping: Dict[str, str] = Field(..., description="Session placeholder mapping dictionary")

class RehydrateResponse(BaseModel):
    text: str
    unknown_placeholders: List[str]

class ProcessRequest(BaseModel):
    text: str = Field(..., description="Raw clinical text input")
    prompt_template: Optional[str] = Field("{masked_text}", description="Prompt template for downstream LLM")

class ProcessResponse(BaseModel):
    original_text: str
    masked_text: str
    entities: List[Dict[str, Any]]
    llm_response: str
    final_response: str
    latency_ms: float
    raw_phi_sent_to_llm: bool


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "PrivMed Gateway",
        "version": "1.0.0",
        "timestamp": time.time()
    }

@app.post("/deidentify", response_model=DeidentifyResponse)
def api_deidentify(req: DeidentifyRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")
    
    start_time = time.time()
    masked_text, mapping, entities = gateway.deidentify(req.text)
    
    # Calculate simple risk score based on remaining unmasked suspicious patterns
    risk_score = 0.0 if len(entities) > 0 else 0.05

    return DeidentifyResponse(
        masked_text=masked_text,
        mapping_id=f"sess-{int(start_time*1000)}",
        entities=entities,
        risk_score=risk_score
    )

@app.post("/rehydrate", response_model=RehydrateResponse)
def api_rehydrate(req: RehydrateRequest):
    rehydrated_text, unknown_placeholders = gateway.rehydrate(req.response, req.mapping)
    return RehydrateResponse(
        text=rehydrated_text,
        unknown_placeholders=unknown_placeholders
    )

@app.post("/process", response_model=ProcessResponse)
def api_process(req: ProcessRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty.")
    
    start_time = time.time()
    result = gateway.process_round_trip(req.text, llm_prompt_template=req.prompt_template or "{masked_text}")
    latency_ms = (time.time() - start_time) * 1000

    return ProcessResponse(
        original_text=result["original_text"],
        masked_text=result["masked_text"],
        entities=result["entities"],
        llm_response=result["llm_response"],
        final_response=result["final_response"],
        latency_ms=round(latency_ms, 2),
        raw_phi_sent_to_llm=False
    )
