"""
src/pipeline/__init__.py
Multi-agent pipeline package for PhishTrap.
"""

from src.pipeline.contracts import (
    EmailPayload,
    ParsedURL,
    ParserOutput,
    ExtractedFeatures,
    FeatureOutput,
    ScoredURL,
    ClassifierOutput,
    TriageOutput,
    ActionOutput,
    AuditOutput,
    PipelineResult
)
from src.pipeline.agents import (
    ParserAgent,
    FeatureAgent,
    ClassifierAgent,
    TriageAgent,
    ActionAgent,
    AuditAgent
)
from src.pipeline.orchestrator import PhishingPipelineOrchestrator

__all__ = [
    "EmailPayload",
    "ParsedURL",
    "ParserOutput",
    "ExtractedFeatures",
    "FeatureOutput",
    "ScoredURL",
    "ClassifierOutput",
    "TriageOutput",
    "ActionOutput",
    "AuditOutput",
    "PipelineResult",
    "ParserAgent",
    "FeatureAgent",
    "ClassifierAgent",
    "TriageAgent",
    "ActionAgent",
    "AuditAgent",
    "PhishingPipelineOrchestrator"
]

