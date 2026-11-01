"""
src/pipeline/orchestrator.py
Deterministic pipeline orchestrator coordinating the multi-agent workflow.
"""

import time
import sqlite3
from typing import List, Dict, Any, Optional, Union

from src.pipeline.contracts import EmailPayload, PipelineResult
from src.pipeline.agents import (
    ParserAgent,
    FeatureAgent,
    ClassifierAgent,
    TriageAgent,
    ActionAgent,
    AuditAgent
)


class PhishingPipelineOrchestrator:
    """
    Deterministic multi-agent orchestrator implementing the 6-agent PhishTrap pipeline:
      Email -> ParserAgent -> FeatureAgent -> ClassifierAgent -> TriageAgent -> ActionAgent -> AuditAgent
    """

    def __init__(self, t_low: float = 0.05, t_high: float = 0.85, model_artifact: dict = None):
        self.t_low = t_low
        self.t_high = t_high
        self.parser = ParserAgent()
        self.feature = FeatureAgent()
        self.classifier = ClassifierAgent(model_artifact)
        self.triage = TriageAgent()
        self.action = ActionAgent()
        self.audit = AuditAgent()

    def process_email(
        self,
        email_data: Union[EmailPayload, Dict[str, Any]],
        db_conn: Optional[sqlite3.Connection] = None
    ) -> PipelineResult:
        start_time = time.time()
        
        if isinstance(email_data, dict):
            email = EmailPayload(**email_data)
        else:
            email = email_data

        try:
            # 1. Parse Email -> Extract URLs
            parser_output = self.parser.process(email)

            # 2. Extract Lexical & Domain Features
            feature_output = self.feature.process(parser_output)

            # 3. Model Inference & Top Features
            classifier_output = self.classifier.process(parser_output, feature_output)

            # 4. Strict Triage Decision
            triage_output = self.triage.process(
                parser_output=parser_output,
                classifier_output=classifier_output,
                t_low=self.t_low,
                t_high=self.t_high
            )

            # 5. Execute Containment & SQLite Persistence
            action_output = self.action.process(
                email=email,
                parser_output=parser_output,
                classifier_output=classifier_output,
                triage_output=triage_output,
                db_conn=db_conn
            )

            # 6. Compliance & Audit Trace
            audit_output = self.audit.process(
                action_output=action_output,
                triage_output=triage_output,
                classifier_output=classifier_output
            )

            elapsed_ms = round((time.time() - start_time) * 1000, 2)

            return PipelineResult(
                message_id=parser_output.message_id,
                subject=email.subject,
                sender=email.sender,
                received_at=email.received_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                decision=triage_output.decision,
                current_status=action_output.final_status,
                max_score=triage_output.max_score,
                urls=classifier_output.scored_urls,
                parser_output=parser_output,
                triage_output=triage_output,
                action_output=action_output,
                execution_time_ms=elapsed_ms,
                error_occurred=False,
                error_message=None
            )

        except Exception as e:
            # Fail-safe handler: Any unhandled exception defaults to HUMAN_REVIEW, never ALLOW
            elapsed_ms = round((time.time() - start_time) * 1000, 2)
            msg_id = getattr(email, 'id', None) or "msg_unknown_err"

            # Create synthetic triage output for fallback
            from src.pipeline.contracts import TriageOutput, ParserOutput, ActionOutput
            fb_parser = ParserOutput(
                message_id=msg_id,
                parsed_urls=[],
                url_count=0,
                has_urls=False,
                is_malformed=True,
                parse_error=str(e)
            )
            fb_triage = TriageOutput(
                decision="HUMAN_REVIEW",
                max_score=0.0,
                t_low=self.t_low,
                t_high=self.t_high,
                rationale=f"UNHANDLED ERROR: {str(e)}. Defaulted to human review.",
                routed_to_human=True
            )
            fb_action = ActionOutput(
                message_id=msg_id,
                final_status="HUMAN_REVIEW",
                persisted=False,
                action_taken="Emergency fallback to human review queue."
            )

            return PipelineResult(
                message_id=msg_id,
                subject=getattr(email, 'subject', 'Error Message'),
                sender=getattr(email, 'sender', 'unknown'),
                received_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                decision="HUMAN_REVIEW",
                current_status="HUMAN_REVIEW",
                max_score=0.0,
                urls=[],
                parser_output=fb_parser,
                triage_output=fb_triage,
                action_output=fb_action,
                execution_time_ms=elapsed_ms,
                error_occurred=True,
                error_message=str(e)
            )

    def batch_process(
        self,
        emails: List[Union[EmailPayload, Dict[str, Any]]],
        db_conn: Optional[sqlite3.Connection] = None
    ) -> List[PipelineResult]:
        return [self.process_email(e, db_conn=db_conn) for e in emails]
