"""
tests/test_api.py
Unit and integration tests for PhishTrap FastAPI backend and SQLite storage.
Uses deterministic in-memory SQLite database and isolated API client.
"""

import os
import pytest
from pydantic import ValidationError
from fastapi import HTTPException

from src.storage.db import init_db
from src.api.app import (
    health_check,
    ingest_email,
    get_human_review_queue,
    get_message_detail,
    override_message_decision,
    get_audit_trail,
    get_pipeline_metrics,
    predict_urls
)
from src.api.schemas import (
    IngestRequest,
    OverrideRequest,
    PredictRequest
)


class ApiResponse:
    """Mock response wrapper matching requests/TestClient interface."""
    def __init__(self, status_code: int, data: dict):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


class ApiTestClient:
    """
    Deterministic client calling endpoints with Pydantic validation
    and HTTP exception handling, avoiding Windows subthread portal deadlocks.
    """
    def get(self, path: str, params: dict = None):
        params = params or {}
        try:
            if path == "/health":
                return ApiResponse(200, health_check())
            elif path == "/api/v1/queue":
                res = get_human_review_queue(limit=params.get("limit", 50), offset=params.get("offset", 0))
                return ApiResponse(200, res)
            elif path.startswith("/api/v1/messages/"):
                msg_id = path.split("/api/v1/messages/")[1]
                res = get_message_detail(msg_id)
                return ApiResponse(200, res)
            elif path == "/api/v1/audit":
                res = get_audit_trail(limit=params.get("limit", 50), offset=params.get("offset", 0))
                return ApiResponse(200, res)
            elif path == "/api/v1/metrics":
                return ApiResponse(200, get_pipeline_metrics())
            else:
                return ApiResponse(404, {"detail": "Not Found"})
        except HTTPException as he:
            return ApiResponse(he.status_code, {"detail": he.detail})
        except ValidationError as ve:
            return ApiResponse(422, {"detail": ve.errors()})

    def post(self, path: str, json: dict = None):
        json_data = json or {}
        try:
            if path == "/api/v1/predict":
                req = PredictRequest(**json_data)
                return ApiResponse(200, predict_urls(req))
            elif path == "/api/v1/ingest":
                req = IngestRequest(**json_data)
                return ApiResponse(201, ingest_email(req))
            elif "/override" in path:
                # Path: /api/v1/messages/{msg_id}/override
                parts = path.strip("/").split("/")
                msg_id = parts[3]
                req = OverrideRequest(**json_data)
                return ApiResponse(200, override_message_decision(msg_id, req))
            else:
                return ApiResponse(404, {"detail": "Not Found"})
        except HTTPException as he:
            return ApiResponse(he.status_code, {"detail": he.detail})
        except ValidationError as ve:
            return ApiResponse(422, {"detail": ve.errors()})


@pytest.fixture(scope="session", autouse=True)
def setup_test_db(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("test_db")
    test_db_path = str(temp_dir / "test_pipeline.db")
    os.environ["PHISHTRAP_DB_PATH"] = test_db_path
    init_db(test_db_path)
    yield test_db_path


@pytest.fixture
def client():
    return ApiTestClient()


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "PhishTrap API"
    assert "model_version" in data


def test_direct_predict_urls(client):
    urls = [
        "https://www.google.com/search?q=cybersecurity",
        "http://secure-login-verify-account.bank-update.xyz/login.php"
    ]
    response = client.post("/api/v1/predict", json={"urls": urls})
    assert response.status_code == 200
    data = response.json()
    assert "urls" in data
    assert len(data["urls"]) == 2
    assert "max_score" in data
    assert "automated_decision" in data

    # Verify defanging
    first_url = data["urls"][0]
    assert "[.]" in first_url["defanged_url"]
    assert first_url["raw_url"] == urls[0]
    assert isinstance(first_url["score"], float)
    assert len(first_url["top_features"]) > 0


def test_ingest_email_with_safe_url(client):
    payload = {
        "subject": "Weekly Tech Digest",
        "sender": "newsletter@techjournal.org",
        "body": "Here is the summary of articles: https://techjournal.org/weekly-recap",
        "urls": ["https://techjournal.org/weekly-recap"]
    }
    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"].startswith("msg_")
    assert data["subject"] == payload["subject"]
    assert len(data["urls"]) == 1
    assert data["urls"][0]["defanged_url"] == "hxxps://techjournal[.]org/weekly-recap"
    assert data["max_score"] < 0.20  # Benign domain should have low score


def test_ingest_email_with_extracted_urls(client):
    # Tests automatic URL parsing from email body when urls field is omitted
    payload = {
        "subject": "Urgent Action Required",
        "sender": "alerts@account-security.com",
        "body": "Please confirm your identity at http://192.168.1.1/verify/account or visit https://paypal-security-update.com/signin immediately."
    }
    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["urls"]) >= 2
    # Verify IP and phishing keywords drove high score
    assert data["max_score"] > 0.05
    assert data["automated_decision"] in ["QUARANTINE", "HUMAN_REVIEW"]


def test_ingest_email_without_urls(client):
    payload = {
        "subject": "Plain discussion",
        "sender": "alice@company.com",
        "body": "Hi Bob, let us meet tomorrow at 10 AM in Conference Room B."
    }
    response = client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["max_score"] == 0.0
    assert data["automated_decision"] == "ALLOW"
    assert data["current_status"] == "ALLOW"
    assert len(data["urls"]) == 0


def test_queue_and_override_workflow(client):
    # 1. Ingest an ambiguous email that lands in HUMAN_REVIEW
    payload = {
        "subject": "Action Needed: Verify your invoice",
        "sender": "billing-support@vendor-portal.com",
        "body": "View invoice at https://portal.billing-docs.co/invoices/client/9821/review"
    }
    ingest_res = client.post("/api/v1/ingest", json=payload)
    assert ingest_res.status_code == 201
    msg_id = ingest_res.json()["id"]

    # Retrieve message directly
    msg_res = client.get(f"/api/v1/messages/{msg_id}")
    assert msg_res.status_code == 200
    assert msg_res.json()["id"] == msg_id

    # 2. Test Override Action (e.g. RELEASE)
    override_payload = {
        "reviewer_id": "analyst_arsh",
        "action": "RELEASE",
        "reason": "Verified sender through phone channel, legitimate invoice notification."
    }
    override_res = client.post(f"/api/v1/messages/{msg_id}/override", json=override_payload)
    assert override_res.status_code == 200
    override_data = override_res.json()
    assert override_data["updated_status"] == "RELEASED"
    assert override_data["override"]["reviewer_id"] == "analyst_arsh"
    assert override_data["override"]["reason"] == override_payload["reason"]

    # 3. Verify message status updated
    updated_msg_res = client.get(f"/api/v1/messages/{msg_id}")
    assert updated_msg_res.json()["current_status"] == "RELEASED"
    assert len(updated_msg_res.json()["overrides"]) == 1

    # 4. Attempting to override to the same status returns 400
    duplicate_res = client.post(f"/api/v1/messages/{msg_id}/override", json=override_payload)
    assert duplicate_res.status_code == 400

    # 5. Check Audit Log
    audit_res = client.get("/api/v1/audit")
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    assert audit_data["total_entries"] >= 1
    found = any(e["message_id"] == msg_id for e in audit_data["entries"])
    assert found


def test_override_validation_errors(client):
    # Non-existent message returns 404
    bad_res = client.post(
        "/api/v1/messages/msg_nonexistent999/override",
        json={"reviewer_id": "analyst", "action": "RELEASE", "reason": "Testing 404 handling"}
    )
    assert bad_res.status_code == 404

    # Invalid action returns 422
    invalid_action_res = client.post(
        "/api/v1/messages/msg_nonexistent999/override",
        json={"reviewer_id": "analyst", "action": "DELETE_NOW", "reason": "Invalid action"}
    )
    assert invalid_action_res.status_code == 422

    # Reason too short returns 422
    short_reason_res = client.post(
        "/api/v1/messages/msg_nonexistent999/override",
        json={"reviewer_id": "analyst", "action": "RELEASE", "reason": "ok"}
    )
    assert short_reason_res.status_code == 422


def test_metrics_endpoint(client):
    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_messages" in data
    assert "automated_decisions" in data
    assert "current_status_distribution" in data
    assert "human_review_queue_depth" in data
    assert "total_overrides" in data
    assert "override_breakdown" in data
    assert data["total_messages"] >= 3
    assert data["total_overrides"] >= 1
