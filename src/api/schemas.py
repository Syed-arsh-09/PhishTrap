"""
src/api/schemas.py
Pydantic schemas for PhishTrap REST API contracts.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class IngestRequest(BaseModel):
    subject: str = Field(..., description="Email subject line", min_length=1)
    sender: str = Field(..., description="Email sender address or identifier", min_length=1)
    body: str = Field(..., description="Email body content", min_length=1)
    urls: Optional[List[str]] = Field(None, description="Optional explicit URLs. If omitted, extracted from body.")
    received_at: Optional[str] = Field(None, description="ISO-8601 timestamp. Defaults to current UTC time.")


class ExtractedUrlResponse(BaseModel):
    raw_url: str
    defanged_url: str
    normalized_url: str
    registered_domain: str
    score: float
    top_features: List[str] = []


class OverrideRecord(BaseModel):
    id: int
    message_id: str
    reviewer_id: str
    previous_status: str
    new_status: str
    reason: str
    timestamp: str


class MessageResponse(BaseModel):
    id: str
    subject: str
    sender: str
    body: str
    received_at: str
    max_score: float
    automated_decision: str
    current_status: str
    decided_at: str
    decided_by: str
    urls: List[ExtractedUrlResponse] = []
    overrides: List[OverrideRecord] = []


class OverrideRequest(BaseModel):
    reviewer_id: str = Field(..., min_length=2, description="Identifier of the SecOps analyst")
    action: str = Field(
        ...,
        pattern="^(RELEASE|CONFIRM_PHISH|RELABEL)$",
        description="Override action: RELEASE, CONFIRM_PHISH, or RELABEL"
    )
    reason: str = Field(..., min_length=5, description="Mandatory justification for human audit trail")


class OverrideResponse(BaseModel):
    message: str
    override: OverrideRecord
    updated_status: str


class AuditLogResponse(BaseModel):
    total_entries: int
    entries: List[Dict[str, Any]]


class MetricsResponse(BaseModel):
    total_messages: int
    automated_decisions: Dict[str, int]
    current_status_distribution: Dict[str, int]
    human_review_queue_depth: int
    total_overrides: int
    override_breakdown: Dict[str, int]


class PredictRequest(BaseModel):
    urls: List[str] = Field(..., min_length=1, description="List of raw URLs to evaluate")


class PredictResponse(BaseModel):
    urls: List[ExtractedUrlResponse]
    max_score: float
    automated_decision: str
