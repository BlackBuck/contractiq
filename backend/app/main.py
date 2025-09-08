import logging
# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("contract_parser")

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ValidationError
from typing import List, Optional, Dict, Any, Tuple
import uuid
import os
import shutil
import asyncio
import httpx
import pdfplumber
import json
import re
from json_repair import repair_json

app = FastAPI()

# Allow CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for demo (replace with DB in production)
CONTRACTS = {}
CONTRACT_FILES = {}

UPLOAD_DIR = "uploaded_contracts"
os.makedirs(UPLOAD_DIR, exist_ok=True)

class ContractStatus(BaseModel):
    contract_id: str
    status: str  # pending, processing, completed, failed
    progress: int
    error: Optional[str] = None

class ContractData(BaseModel):
    contract_id: str
    data: Dict[str, Any]
    confidence_scores: Dict[str, float]
    gaps: List[str]
    score: float = 0.0

class ContractListItem(BaseModel):
    contract_id: str
    status: str
    created_at: str
    score: Optional[float] = None

# Optional: typed extraction model
class ExtractedContract(BaseModel):
    # The LLM can return nested objects for these fields; accept dicts or raw values
    party_identification: Optional[Dict[str, Any]]
    account_information: Optional[Dict[str, Any]]
    financial_details: Optional[Dict[str, Any]]
    payment_structure: Optional[Dict[str, Any]]
    revenue_classification: Optional[Dict[str, Any]]
    service_level_agreements: Optional[Dict[str, Any]]
    confidence_scores: Optional[Dict[str, float]] = {}
    gaps: Optional[List[str]] = []

def compute_contract_score(confidence_scores: dict) -> float:
    # Weighted Scoring System (0-100 points)
    weights = {
        "financial_completeness": 30,
        "party_identification": 25,
        "payment_terms_clarity": 20,
        "sla_definition": 15,
        "contact_information": 10
    }
    score = 0.0
    for key, weight in weights.items():
        value = confidence_scores.get(key, 0)
        score += value * weight
    return round(score, 2)


def derive_confidence_and_gaps(extracted: Dict[str, Any]) -> Tuple[Dict[str, float], List[str]]:
    """Derive a normalized set of confidence scores (0-1) and list of gaps from the extracted JSON.

    Rules (heuristic):
    - Map extraction fields to scoring categories defined in the README.
    - If a field is missing or null -> score 0 and mark as a gap.
    - If a field is present:
      - If string and non-empty -> score 0.9
      - If dict -> score = non-empty-value-count / max(1, total-keys) (clamped to 1.0)
    - If the LLM already returned a confidence for a particular category, take the max(llm_score, derived_score).
    """
    # Mapping from scoring keys to extraction keys
    mapping = {
        "financial_completeness": "financial_details",
        "party_identification": "party_identification",
        "payment_terms_clarity": "payment_structure",
        "sla_definition": "service_level_agreements",
        "contact_information": "account_information",
    }

    llm_conf = extracted.get("confidence_scores") or {}
    scores: Dict[str, float] = {}
    gaps: List[str] = []

    for score_key, field_key in mapping.items():
        val = extracted.get(field_key)
        derived = 0.0
        if val is None:
            derived = 0.0
            gaps.append(field_key)
        elif isinstance(val, str):
            derived = 0.9 if val.strip() else 0.0
        elif isinstance(val, dict):
            if not val:
                derived = 0.0
                gaps.append(field_key)
            else:
                non_empty = sum(1 for v in val.values() if v not in (None, "", [], {}))
                total_keys = max(1, len(val))
                derived = min(1.0, non_empty / total_keys)
        else:
            # fallback for lists or other types: presence => medium confidence
            try:
                derived = 0.8 if val else 0.0
            except Exception:
                derived = 0.0

        # combine with any LLM-provided confidence (prefer higher)
        llm_val = None
        try:
            llm_val = float(llm_conf.get(score_key)) if score_key in llm_conf else None
        except Exception:
            llm_val = None
        final_score = derived if llm_val is None else max(derived, llm_val)
        # clamp
        final_score = max(0.0, min(1.0, final_score))
        scores[score_key] = round(final_score, 3)

    return scores, gaps

def extract_text_from_pdf(pdf_path: str) -> str:
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text

def ensure_json_prompt(contract_text: str, fields: str) -> str:
    # Build prompt for a specific group of fields
    return f"""
Extract the following fields from the contract text.
Return a JSON object with these keys:
{fields}.
For each field, if data is missing, set its value to null or an empty list/object as appropriate.
Also include a 'confidence_scores' object (field: score 0-1), and a 'gaps' array listing missing critical fields.
Return ONLY valid JSON. No markdown, no explanations, no backticks.

Contract text:
{contract_text}
"""

def _extract_json_from_text(text: str) -> Dict[str, Any]:
    """Helper: find first JSON object in text and parse/repair it."""
    if not text:
        raise ValueError("No response text to parse from LLM.")
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        logger.info("LLM returned response, attempting to parse JSON.")
        return json.loads(text)
    except Exception as e:
        logger.warning(f"Invalid JSON from LLM, trying repair: {e}")
        fixed = repair_json(text)
        return json.loads(fixed)


async def call_groq(contract_text: str, fields: str) -> Dict[str, Any]:
    """Call the Groq API (OpenAI-compatible chat completions) to extract JSON from contract text."""
    prompt = ensure_json_prompt(contract_text, fields)
    url = "https://api.groq.com/openai/v1/chat/completions"
    api_key = os.environ.get("GROQ_API_KEY")
    # don't print the key; log prompt size and a short snippet for debugging
    try:
        logger.debug(f"Groq prompt length: {len(prompt)}")
        logger.debug(f"Groq prompt snippet: {prompt[:200]!r}")
    except Exception:
        pass
    if not api_key:
        logger.error("GROQ_API_KEY not set in environment")
        raise RuntimeError("GROQ_API_KEY not configured")

    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    logger.info("Calling Groq API for contract extraction...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json=payload, headers=headers)
        # If Groq returns an error (e.g. 400), log the full body to help debug
        if resp.status_code < 200 or resp.status_code >= 300:
            body = None
            try:
                body = resp.json()
            except Exception:
                try:
                    body = resp.text
                except Exception:
                    body = "(could not read response body)"
            logger.error(f"Groq API returned status {resp.status_code}: {body}")
            raise RuntimeError(f"Groq API returned status {resp.status_code}")
        data = resp.json()
        # OpenAI-compatible response: choices[0].message.content
        text = None
        try:
            text = data.get("choices", [])[0].get("message", {}).get("content")
        except Exception:
            text = data.get("choices", [])[0].get("text") if data.get("choices") else None
        if not text:
            # fallback: check common keys
            text = data.get("response") or data.get("message") or data.get("content")
        if not text:
            logger.error("No response from Groq LLM.")
            raise ValueError("No response from LLM.")
        return _extract_json_from_text(text)

async def process_contract(contract_id: str, file_path: str):
    CONTRACTS[contract_id]["status"] = "processing"
    CONTRACTS[contract_id]["progress"] = 10
    try:
        contract_text = extract_text_from_pdf(file_path)
        CONTRACTS[contract_id]["progress"] = 40

        # Hybrid: split fields into two groups for reliability
        fields1 = "party_identification, account_information, financial_details"
        fields2 = "payment_structure, revenue_classification, service_level_agreements"

        extracted1 = await call_groq(contract_text, fields1)
        extracted2 = await call_groq(contract_text, fields2)

        # Merge the two dicts
        combined = {**extracted1, **extracted2}

        # Validate using Pydantic (optional but recommended)
        try:
            validated = ExtractedContract(**combined)
            extracted = validated.dict()
        except ValidationError as ve:
            logger.warning(f"Validation error: {ve}")
            extracted = combined

        # Derive confidence scores and gaps from the extracted structure
        derived_scores, derived_gaps = derive_confidence_and_gaps(extracted)
        # Merge or prefer existing keys
        merged_conf = {**derived_scores, **(extracted.get("confidence_scores") or {})}
        extracted["confidence_scores"] = merged_conf
        extracted["gaps"] = derived_gaps or extracted.get("gaps", [])

        # Compute score
        score = compute_contract_score(merged_conf)
        extracted["score"] = score

        CONTRACTS[contract_id]["data"] = extracted
        CONTRACTS[contract_id]["status"] = "completed"
        CONTRACTS[contract_id]["progress"] = 100
    except Exception as e:
        CONTRACTS[contract_id]["status"] = "failed"
        CONTRACTS[contract_id]["error"] = str(e)
        CONTRACTS[contract_id]["progress"] = 100

@app.post("/contracts/upload")
async def upload_contract(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    contract_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{contract_id}.pdf")
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    CONTRACTS[contract_id] = {
        "status": "pending",
        "progress": 0,
        "data": None,
        "error": None,
        "created_at": "2025-09-07T00:00:00Z"
    }
    CONTRACT_FILES[contract_id] = file_path
    background_tasks.add_task(process_contract, contract_id, file_path)
    return {"contract_id": contract_id}

@app.get("/contracts/{contract_id}/status", response_model=ContractStatus)
async def get_contract_status(contract_id: str):
    contract = CONTRACTS.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")
    return ContractStatus(
        contract_id=contract_id,
        status=contract["status"],
        progress=contract["progress"],
        error=contract["error"]
    )

@app.get("/contracts/{contract_id}", response_model=ContractData)
async def get_contract_data(contract_id: str):
    contract = CONTRACTS.get(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found.")
    if contract["status"] != "completed":
        raise HTTPException(status_code=400, detail="Contract processing not complete.")
    data = contract["data"]
    return ContractData(
        contract_id=contract_id,
        data={k: data.get(k) for k in [
            "party_identification", "account_information", "financial_details",
            "payment_structure", "revenue_classification", "service_level_agreements"
        ]},
        confidence_scores=data.get("confidence_scores", {}),
        gaps=data.get("gaps", []),
        score=data.get("score", 0.0)
    )

@app.get("/contracts", response_model=List[ContractListItem])
async def list_contracts(status: Optional[str] = None):
    items = []
    for cid, c in CONTRACTS.items():
        if status and c["status"] != status:
            continue
        score = None
        if c["data"]:
            score = c["data"].get("score")
        items.append(ContractListItem(
            contract_id=cid,
            status=c["status"],
            created_at=c["created_at"],
            score=score
        ))
    return items

@app.get("/contracts/{contract_id}/download")
async def download_contract(contract_id: str):
    file_path = CONTRACT_FILES.get(contract_id)
    if not file_path or not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(file_path, media_type="application/pdf", filename=f"{contract_id}.pdf")
