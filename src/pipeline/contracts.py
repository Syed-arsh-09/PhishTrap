"""
src/pipeline/contracts.py
Strongly-typed input/output contracts for the PhishTrap multi-agent pipeline.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class EmailPayload(BaseModel):
    """Raw email message ingested into the pipeline."""
    id: Optional[str] = None
    subject: str = Field(..., min_length=1)
    sender: str = Field(..., min_length=1)
    body: str = Field(..., min_length=1)
    received_at: Optional[str] = None


class ParsedURL(BaseModel):
    """Structured decomposition of an individual URL found in an email."""
    raw_url: str
    defanged_url: str
    normalized_url: str
    host: str
    registered_domain: str
    path_query: str


class ParserOutput(BaseModel):
    """Contract emitted by ParserAgent."""
    message_id: str
    parsed_urls: List[ParsedURL]
    url_count: int
    has_urls: bool
    is_malformed: bool = False
    parse_error: Optional[str] = None


class ExtractedFeatures(BaseModel):
    """Lexical and structural vector for a single URL."""
    raw_url: str
    defanged_url: str
    normalized_url: str
    host: str
    registered_domain: str
    lexical_dict: Dict[str, float]


class FeatureOutput(BaseModel):
    """Contract emitted by FeatureAgent."""
    features: List[ExtractedFeatures]
    feature_count: int


class ScoredURL(BaseModel):
    """Scored URL artifact with linear model explainability tags."""
    raw_url: str
    defanged_url: str
    normalized_url: str
    registered_domain: str
    score: float
    top_features: List[str] = []


class ClassifierOutput(BaseModel):
    """Contract emitted by ClassifierAgent."""
    scored_urls: List[ScoredURL]
    max_score: float
    model_version: str
    scoring_error: Optional[str] = None


class TriageOutput(BaseModel):
    """Contract emitted by TriageAgent."""
    decision: str  # ALLOW | QUARANTINE | HUMAN_REVIEW
    max_score: float
    t_low: float
    t_high: float
    rationale: str
    routed_to_human: bool


class ActionOutput(BaseModel):
    """Contract emitted by ActionAgent."""
    message_id: str
    final_status: str
    persisted: bool
    action_taken: str


class AuditOutput(BaseModel):
    """Contract emitted by AuditAgent."""
    message_id: str
    timestamp: str
    action: str
    details: Dict[str, Any]


class PipelineResult(BaseModel):
    """Consolidated end-to-end outcome across all agents in the pipeline."""
    message_id: str
    subject: str
    sender: str
    received_at: str
    decision: str
    current_status: str
    max_score: float
    urls: List[ScoredURL]
    parser_output: ParserOutput
    triage_output: TriageOutput
    action_output: ActionOutput
    execution_time_ms: float
    error_occurred: bool = False
    error_message: Optional[str] = None
