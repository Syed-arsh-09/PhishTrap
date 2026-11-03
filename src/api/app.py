"""
src/api/app.py
FastAPI REST application for Real-Time Phishing Detection & HITL Override.
"""

import os
import time
import uuid
import logging
import contextlib
from typing import List
from fastapi import FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.features.defang import extract_urls_from_text
from src.storage.db import init_db, get_db_context
from src.storage.repositories import MessageRepository, AuditRepository
from src.api.inference import score_urls, get_model_artifact
from src.api.schemas import (
    IngestRequest,
    MessageResponse,
    OverrideRequest,
    OverrideResponse,
    AuditLogResponse,
    MetricsResponse,
    PredictRequest,
    PredictResponse
)


logger = logging.getLogger(__name__)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Initializes SQLite schema and warms up model cache on boot."""
    init_db()
    try:
        get_model_artifact()
    except Exception as e:
        logger.warning("Model artifact could not be loaded at startup: %s", e)
    yield


# Initialize FastAPI application
app = FastAPI(
    title="PhishTrap API",
    description="Real-Time Phishing Detection Pipeline with Human-in-the-Loop Override",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local development (e.g. Vite on port 5173 or other frontend ports)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["System"])
def health_check():
    """Health check endpoint providing model status and timestamp."""
    try:
        artifact = get_model_artifact()
        model_version = artifact.get("version", "unknown")
        model_status = "loaded"
    except Exception:
        model_version = "unavailable"
        model_status = "error"

    return {
        "status": "healthy",
        "service": "PhishTrap API",
        "model_status": model_status,
        "model_version": model_version,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


@app.post(
    "/api/v1/ingest",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Ingestion & Pipeline"]
)
def ingest_email(request: IngestRequest):
    """
    Ingests an email message, extracts URLs, computes lexical & n-gram features,
    determines automated triage routing (ALLOW, QUARANTINE, or HUMAN_REVIEW),
    and persists the record with full URL breakdown.
    """
    received_at = request.received_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    # 1. Determine URLs to evaluate
    if request.urls is not None:
        urls_to_score = request.urls
    else:
        urls_to_score = extract_urls_from_text(request.body)

    # 2. Score URLs through hybrid classifier
    scored_urls, max_score, decision = score_urls(urls_to_score)

    # 3. Create message record
    message_id = f"msg_{uuid.uuid4().hex[:12]}"
    decided_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    
    message_dict = {
        "id": message_id,
        "subject": request.subject,
        "sender": request.sender,
        "body": request.body,
        "received_at": received_at,
        "max_score": max_score,
        "automated_decision": decision,
        "current_status": decision,
        "decided_at": decided_at,
        "decided_by": "hybrid_classifier_v1"
    }

    with get_db_context() as conn:
        saved_msg = MessageRepository.create_message(conn, message_dict, scored_urls)

    return saved_msg


@app.get(
    "/api/v1/queue",
    response_model=List[MessageResponse],
    tags=["Review Queue"]
)
def get_human_review_queue(
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset")
):
    """
    Lists emails currently pending human review (current_status = HUMAN_REVIEW),
    prioritized by descending phishing probability score.
    """
    actual_limit = int(getattr(limit, "default", limit))
    actual_offset = int(getattr(offset, "default", offset))
    with get_db_context() as conn:
        queue = MessageRepository.list_queue(conn, limit=actual_limit, offset=actual_offset)
    return queue


@app.get(
    "/api/v1/messages/{message_id}",
    response_model=MessageResponse,
    tags=["Messages"]
)
def get_message_detail(message_id: str):
    """
    Retrieves full message details, defanged links, explainability scores,
    and complete override history.
    """
    with get_db_context() as conn:
        msg = MessageRepository.get_message(conn, message_id)
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Message with ID '{message_id}' not found."
        )
    return msg


@app.post(
    "/api/v1/messages/{message_id}/override",
    response_model=OverrideResponse,
    tags=["Review Queue"]
)
def override_message_decision(message_id: str, request: OverrideRequest):
    """
    Submits a Human-in-the-Loop SecOps analyst decision override.
    Actions:
      - RELEASE: Releases quarantined or held email (sets status to RELEASED).
      - CONFIRM_PHISH: Confirms threat (sets status to CONFIRMED_PHISH).
      - RELABEL: Corrections for false predictions (sets status to RELABELED).
    Requires a non-empty audit rationale.
    """
    status_map = {
        "RELEASE": "RELEASED",
        "CONFIRM_PHISH": "CONFIRMED_PHISH",
        "RELABEL": "RELABELED"
    }
    new_status = status_map[request.action]
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    with get_db_context() as conn:
        msg = MessageRepository.get_message(conn, message_id)
        if not msg:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Message with ID '{message_id}' not found."
            )

        previous_status = msg["current_status"]
        if previous_status == new_status:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Message is already in '{new_status}' status."
            )

        # Record audit override
        override_record = AuditRepository.record_override(
            conn=conn,
            message_id=message_id,
            reviewer_id=request.reviewer_id,
            previous_status=previous_status,
            new_status=new_status,
            reason=request.reason,
            timestamp=timestamp
        )

        # Update message current status
        MessageRepository.update_status(conn, message_id, new_status)

    return {
        "message": f"Successfully updated status from {previous_status} to {new_status}",
        "override": override_record,
        "updated_status": new_status
    }


@app.get(
    "/api/v1/audit",
    response_model=AuditLogResponse,
    tags=["Audit & Compliance"]
)
def get_audit_trail(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0)
):
    """
    Returns the historical audit trail of all SecOps analyst overrides,
    including timestamps, justifications, and associated message metadata.
    """
    actual_limit = int(getattr(limit, "default", limit))
    actual_offset = int(getattr(offset, "default", offset))
    with get_db_context() as conn:
        entries = AuditRepository.list_audit_log(conn, limit=actual_limit, offset=actual_offset)
    return {
        "total_entries": len(entries),
        "entries": entries
    }


@app.get(
    "/api/v1/metrics",
    response_model=MetricsResponse,
    tags=["Metrics & Reporting"]
)
def get_pipeline_metrics():
    """
    Returns live pipeline summary counters, triage breakdown, queue depth,
    and analyst override totals.
    """
    with get_db_context() as conn:
        metrics = MessageRepository.get_metrics_summary(conn)
    return metrics


@app.post(
    "/api/v1/predict",
    response_model=PredictResponse,
    tags=["Inference"]
)
def predict_urls(request: PredictRequest):
    """
    Direct stateless inference endpoint to evaluate arbitrary URLs.
    Returns defanged URLs, probability scores, top features, and triage decision.
    """
    scored_urls, max_score, decision = score_urls(request.urls)
    return {
        "urls": scored_urls,
        "max_score": max_score,
        "automated_decision": decision
    }


# Mount compiled React SPA frontend if available
FRONTEND_DIST = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))
if os.path.exists(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

