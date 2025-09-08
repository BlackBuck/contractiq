import asyncio
import io
import importlib.util
import os
import json

import pytest

from fastapi.testclient import TestClient


def load_main_module():
    # Load the backend app module directly from file to avoid package import issues
    path = os.path.join(os.path.dirname(__file__), "..", "app", "main.py")
    path = os.path.abspath(path)
    spec = importlib.util.spec_from_file_location("contract_main", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def client_and_module(tmp_path, monkeypatch):
    module = load_main_module()
    # Ensure upload dir is unique per test
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(module, "UPLOAD_DIR", str(upload_dir))
    # Ensure in-memory stores are clean
    module.CONTRACTS.clear()
    module.CONTRACT_FILES.clear()

    client = TestClient(module.app)
    return client, module


def test_upload_rejects_non_pdf(client_and_module):
    client, module = client_and_module
    files = {"file": ("test.txt", b"not a pdf", "text/plain")}
    resp = client.post("/contracts/upload", files=files)
    assert resp.status_code == 400
    assert resp.json()["detail"] == "Only PDF files are supported."


def test_upload_creates_contract_and_saves_file(monkeypatch, client_and_module):
    client, module = client_and_module

    # Prevent background processing from running during upload
    orig_proc = module.process_contract

    async def noop_process(contract_id, file_path):
        # leave the contract in 'pending' state
        module.CONTRACTS[contract_id]["status"] = "pending"

    monkeypatch.setattr(module, "process_contract", noop_process)

    # Upload a fake PDF (binary content is fine since we won't parse it here)
    files = {"file": ("sample.pdf", io.BytesIO(b"%PDF-1.4\n%fakepdf\n"), "application/pdf")}
    resp = client.post("/contracts/upload", files=files)
    assert resp.status_code == 200
    data = resp.json()
    assert "contract_id" in data
    contract_id = data["contract_id"]

    # Check status is present and pending
    status = client.get(f"/contracts/{contract_id}/status")
    assert status.status_code == 200
    body = status.json()
    assert body["contract_id"] == contract_id
    assert body["status"] in ("pending", "processing")

    # Ensure file exists on disk
    file_path = module.CONTRACT_FILES[contract_id]
    assert os.path.exists(file_path)

    # restore original processor
    monkeypatch.setattr(module, "process_contract", orig_proc)


def test_process_contract_flow_and_get_data(client_and_module):
    client, module = client_and_module

    # Upload a dummy pdf but avoid background processing for now
    orig_proc = module.process_contract

    async def noop_process(contract_id, file_path):
        module.CONTRACTS[contract_id]["status"] = "pending"

    module.process_contract = noop_process

    files = {"file": ("sample.pdf", io.BytesIO(b"%PDF-1.4\n%fakepdf\n"), "application/pdf")}
    resp = client.post("/contracts/upload", files=files)
    contract_id = resp.json()["contract_id"]
    file_path = module.CONTRACT_FILES[contract_id]

    # Now restore the real process_contract and monkeypatch external I/O
    module.process_contract = orig_proc

    async def fake_extract_text(pdf_path: str) -> str:
        return "This is a fake contract text describing parties and payment terms."

    async def fake_call_groq(contract_text: str, fields: str):
        # return different pieces depending on requested fields
        if "party_identification" in fields:
            return {
                "party_identification": {"name": "ACME Corp"},
                "account_information": {"billing": "123 Main St"},
                "financial_details": {"total": 1000},
                "confidence_scores": {"financial_completeness": 0.8}
            }
        else:
            return {
                "payment_structure": {"terms": "Net 30"},
                "revenue_classification": {"type": "recurring"},
                "service_level_agreements": {"uptime": "99.9"}
            }

    # monkeypatch the synchronous extractor and async call_groq
    # extract_text_from_pdf is synchronous in module; replace with a sync wrapper
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(module, "extract_text_from_pdf", lambda p: "fake text")
    monkeypatch.setattr(module, "call_groq", lambda text, fields: asyncio.get_event_loop().create_task(fake_call_groq(text, fields)).result() if False else fake_call_groq(text, fields))

    # Instead of fiddly event-loop tricks, call the coroutine directly
    asyncio.run(module.process_contract(contract_id, file_path))

    # After processing, status should be completed
    status = client.get(f"/contracts/{contract_id}/status")
    assert status.status_code == 200
    body = status.json()
    assert body["status"] == "completed"

    # Get data
    data_resp = client.get(f"/contracts/{contract_id}")
    assert data_resp.status_code == 200
    data = data_resp.json()
    assert data["contract_id"] == contract_id
    assert data["data"]["party_identification"]["name"] == "ACME Corp"
    assert "confidence_scores" in data

    # Download should return the uploaded file
    dl = client.get(f"/contracts/{contract_id}/download")
    assert dl.status_code == 200
    assert dl.headers.get("content-type") == "application/pdf"

    # cleanup monkeypatch
    monkeypatch.undo()


def test_helpers_compute_and_derive():
    # import helpers via fresh module load
    module = load_main_module()
    sample_extracted = {
        "financial_details": {"total": 200, "tax": 20},
        "party_identification": {"name": "Foo"},
        "payment_structure": "Net 30",
        "service_level_agreements": {},
        "account_information": None,
        "confidence_scores": {"payment_terms_clarity": 0.6}
    }
    scores, gaps = module.derive_confidence_and_gaps(sample_extracted)
    # Account information missing -> in gaps
    assert "account_information" in gaps
    # Payment terms clarity should at least be 0.6 (from LLM) or derived
    assert scores["payment_terms_clarity"] >= 0.6

    # compute score uses weights; use known scores to validate numeric
    test_scores = {
        "financial_completeness": 0.5,
        "party_identification": 1.0,
        "payment_terms_clarity": 0.2,
        "sla_definition": 0.0,
        "contact_information": 0.0,
    }
    total = module.compute_contract_score(test_scores)
    # Validate numeric range and rounding
    assert isinstance(total, float)
    assert 0.0 <= total <= 100.0
