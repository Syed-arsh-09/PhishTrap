"""
src/pipeline/agents.py
Deterministic agents with explicit typed contracts for the PhishTrap architecture.
"""

import time
import uuid
import sqlite3
from typing import List, Optional
from scipy.sparse import hstack
import tldextract

from src.features.defang import extract_urls_from_text, defang_url
from src.features.lexical import (
    normalize_url,
    extract_lexical_features,
    batch_extract_features,
    FEATURE_NAMES
)
from src.api.inference import get_model_artifact, explain_url_features
from src.storage.db import get_db_context
from src.storage.repositories import MessageRepository
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
    AuditOutput
)

_extractor = tldextract.TLDExtract(suffix_list_urls=None, include_psl_private_domains=True)


class ParserAgent:
    """Agent responsible for parsing raw email payload and extracting embedded URLs."""

    def process(self, email: EmailPayload) -> ParserOutput:
        message_id = email.id or f"msg_{uuid.uuid4().hex[:12]}"
        
        try:
            raw_urls = extract_urls_from_text(email.body)
        except Exception as e:
            return ParserOutput(
                message_id=message_id,
                parsed_urls=[],
                url_count=0,
                has_urls=False,
                is_malformed=True,
                parse_error=f"Malformed email body: {str(e)}"
            )

        parsed_urls: List[ParsedURL] = []
        for raw_u in raw_urls:
            norm_u, host, reg_dom, pq = normalize_url(raw_u)
            if norm_u is None:
                norm_u = raw_u.strip()
                ext = _extractor(norm_u)
                host = ext.fqdn or "unknown"
                reg_dom = ext.top_domain_under_public_suffix or host
                pq = ""

            parsed_urls.append(
                ParsedURL(
                    raw_url=raw_u,
                    defanged_url=defang_url(raw_u),
                    normalized_url=norm_u,
                    host=host,
                    registered_domain=reg_dom,
                    path_query=pq or ""
                )
            )

        return ParserOutput(
            message_id=message_id,
            parsed_urls=parsed_urls,
            url_count=len(parsed_urls),
            has_urls=len(parsed_urls) > 0,
            is_malformed=False,
            parse_error=None
        )


class FeatureAgent:
    """Agent responsible for deterministic lexical and domain feature extraction."""

    def process(self, parser_output: ParserOutput) -> FeatureOutput:
        extracted: List[ExtractedFeatures] = []
        for p in parser_output.parsed_urls:
            feats = extract_lexical_features(p.normalized_url, p.host, p.path_query)
            extracted.append(
                ExtractedFeatures(
                    raw_url=p.raw_url,
                    defanged_url=p.defanged_url,
                    normalized_url=p.normalized_url,
                    host=p.host,
                    registered_domain=p.registered_domain,
                    lexical_dict=feats
                )
            )

        return FeatureOutput(
            features=extracted,
            feature_count=len(extracted)
        )


class ClassifierAgent:
    """Agent responsible for model scoring, n-gram TF-IDF projection, and explainability."""

    def __init__(self, model_artifact: dict = None):
        self.artifact = model_artifact

    def _get_artifact(self) -> dict:
        if self.artifact is None:
            self.artifact = get_model_artifact()
        return self.artifact

    def process(self, parser_output: ParserOutput, feature_output: FeatureOutput) -> ClassifierOutput:
        if not parser_output.has_urls:
            return ClassifierOutput(
                scored_urls=[],
                max_score=0.0,
                model_version="hybrid_v1",
                scoring_error=None
            )

        try:
            artifact = self._get_artifact()
            scaler = artifact["scaler"]
            tfidf = artifact["tfidf"]
            model = artifact["model"]
            version = artifact.get("version", "1.0.0")

            # Extract features in batch
            tuple_data = [
                (f.normalized_url, f.host, p.path_query)
                for f, p in zip(feature_output.features, parser_output.parsed_urls)
            ]
            df_lex = batch_extract_features(tuple_data)
            X_lex = df_lex.values
            X_lex_scaled = scaler.transform(df_lex)

            normalized_strings = [p.normalized_url for p in parser_output.parsed_urls]
            X_tfidf = tfidf.transform(normalized_strings)

            X_comb = hstack([X_lex_scaled, X_tfidf])
            probs = model.predict_proba(X_comb)[:, 1]
            lex_coefs = model.coef_[0][:len(FEATURE_NAMES)]

            scored_urls: List[ScoredURL] = []
            for i, p in enumerate(parser_output.parsed_urls):
                score = float(round(probs[i], 4))
                top_features = explain_url_features(
                    feature_values=X_lex[i],
                    scaled_features=X_lex_scaled[i],
                    lex_coefs=lex_coefs,
                    feature_names=FEATURE_NAMES,
                    top_k=3
                )
                scored_urls.append(
                    ScoredURL(
                        raw_url=p.raw_url,
                        defanged_url=p.defanged_url,
                        normalized_url=p.normalized_url,
                        registered_domain=p.registered_domain,
                        score=score,
                        top_features=top_features
                    )
                )

            max_score = max(u.score for u in scored_urls) if scored_urls else 0.0

            return ClassifierOutput(
                scored_urls=scored_urls,
                max_score=max_score,
                model_version=version,
                scoring_error=None
            )

        except Exception as e:
            return ClassifierOutput(
                scored_urls=[],
                max_score=0.0,
                model_version="error",
                scoring_error=f"Model scoring failure: {str(e)}"
            )


class TriageAgent:
    """Agent executing strict dual-threshold routing policy with failure safety."""

    def process(
        self,
        parser_output: ParserOutput,
        classifier_output: ClassifierOutput,
        t_low: float = 0.05,
        t_high: float = 0.85
    ) -> TriageOutput:
        # Mandatory Safety Invariant: Any error routes to HUMAN_REVIEW, never ALLOW
        if parser_output.is_malformed:
            return TriageOutput(
                decision="HUMAN_REVIEW",
                max_score=0.0,
                t_low=t_low,
                t_high=t_high,
                rationale=f"SAFETY OVERRIDE: {parser_output.parse_error}. Deferred to human review.",
                routed_to_human=True
            )

        if classifier_output.scoring_error:
            return TriageOutput(
                decision="HUMAN_REVIEW",
                max_score=0.0,
                t_low=t_low,
                t_high=t_high,
                rationale=f"SAFETY OVERRIDE: {classifier_output.scoring_error}. Deferred to human review.",
                routed_to_human=True
            )

        # Clean text with zero URLs
        if not parser_output.has_urls:
            return TriageOutput(
                decision="ALLOW",
                max_score=0.0,
                t_low=t_low,
                t_high=t_high,
                rationale="Zero embedded URLs detected. Clean text cleared.",
                routed_to_human=False
            )

        # Threshold evaluation
        max_score = classifier_output.max_score
        if max_score >= t_high:
            return TriageOutput(
                decision="QUARANTINE",
                max_score=max_score,
                t_low=t_low,
                t_high=t_high,
                rationale=f"Max phishing probability ({max_score:.4f}) >= high threshold ({t_high}). Auto-quarantined.",
                routed_to_human=False
            )
        elif max_score < t_low:
            return TriageOutput(
                decision="ALLOW",
                max_score=max_score,
                t_low=t_low,
                t_high=t_high,
                rationale=f"Max phishing probability ({max_score:.4f}) < low threshold ({t_low}). Safe traffic cleared.",
                routed_to_human=False
            )
        else:
            return TriageOutput(
                decision="HUMAN_REVIEW",
                max_score=max_score,
                t_low=t_low,
                t_high=t_high,
                rationale=f"Ambiguous risk score ({max_score:.4f}) in triage band [{t_low}, {t_high}). Routed to SOC analyst.",
                routed_to_human=True
            )


class ActionAgent:
    """Agent executing database persistence and automated containment actions."""

    def process(
        self,
        email: EmailPayload,
        parser_output: ParserOutput,
        classifier_output: ClassifierOutput,
        triage_output: TriageOutput,
        db_conn: Optional[sqlite3.Connection] = None
    ) -> ActionOutput:
        message_id = parser_output.message_id
        decision = triage_output.decision
        received_at = email.received_at or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        decided_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        message_dict = {
            "id": message_id,
            "subject": email.subject,
            "sender": email.sender,
            "body": email.body,
            "received_at": received_at,
            "max_score": triage_output.max_score,
            "automated_decision": decision,
            "current_status": decision,
            "decided_at": decided_at,
            "decided_by": classifier_output.model_version
        }

        urls_data = [
            {
                "raw_url": u.raw_url,
                "defanged_url": u.defanged_url,
                "normalized_url": u.normalized_url,
                "registered_domain": u.registered_domain,
                "score": u.score,
                "top_features": u.top_features
            }
            for u in classifier_output.scored_urls
        ]

        # Persist to database
        if db_conn is not None:
            MessageRepository.create_message(db_conn, message_dict, urls_data)
        else:
            with get_db_context() as conn:
                MessageRepository.create_message(conn, message_dict, urls_data)

        action_desc = {
            "QUARANTINE": "Message quarantined in security sandbox.",
            "ALLOW": "Message released to user inbox.",
            "HUMAN_REVIEW": "Message placed in SOC analyst review queue."
        }.get(decision, "Action completed.")

        return ActionOutput(
            message_id=message_id,
            final_status=decision,
            persisted=True,
            action_taken=action_desc
        )


class AuditAgent:
    """Agent producing structured compliance logs and explainability telemetry."""

    def process(
        self,
        action_output: ActionOutput,
        triage_output: TriageOutput,
        classifier_output: ClassifierOutput
    ) -> AuditOutput:
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        details = {
            "status": action_output.final_status,
            "max_score": triage_output.max_score,
            "rationale": triage_output.rationale,
            "scored_urls_count": len(classifier_output.scored_urls),
            "top_threat_url": classifier_output.scored_urls[0].defanged_url if classifier_output.scored_urls else None
        }

        return AuditOutput(
            message_id=action_output.message_id,
            timestamp=timestamp,
            action=f"AUTOMATED_{action_output.final_status}",
            details=details
        )
