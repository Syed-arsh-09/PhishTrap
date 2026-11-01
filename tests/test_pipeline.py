"""
tests/test_pipeline.py
Unit and integration tests for the PhishTrap multi-agent pipeline and safety invariants.
"""

import os
import pytest
from src.storage.db import init_db, get_db_connection
from src.pipeline.contracts import (
    EmailPayload,
    ParserOutput,
    ParsedURL,
    ClassifierOutput
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


@pytest.fixture(scope="session", autouse=True)
def setup_pipeline_test_db(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("pipeline_db")
    test_db_path = str(temp_dir / "test_pipeline.db")
    os.environ["PHISHTRAP_DB_PATH"] = test_db_path
    init_db(test_db_path)
    yield test_db_path


def test_parser_agent_with_urls():
    agent = ParserAgent()
    email = EmailPayload(
        id="test_parse_01",
        subject="Meeting link",
        sender="bob@work.com",
        body="Join via https://meet.google.com/abc-def-ghi or check http://intranet.local/docs."
    )
    output = agent.process(email)
    assert output.message_id == "test_parse_01"
    assert output.has_urls is True
    assert output.url_count == 2
    assert output.is_malformed is False
    assert output.parsed_urls[0].defanged_url.startswith("hxxps://")
    assert "[.]" in output.parsed_urls[0].defanged_url


def test_parser_agent_without_urls():
    agent = ParserAgent()
    email = EmailPayload(
        id="test_parse_02",
        subject="Coffee chat",
        sender="alice@work.com",
        body="Let's grab a coffee at 2 PM today in the cafeteria."
    )
    output = agent.process(email)
    assert output.has_urls is False
    assert output.url_count == 0
    assert len(output.parsed_urls) == 0


def test_feature_agent():
    parser = ParserAgent()
    feature = FeatureAgent()
    email = EmailPayload(
        id="test_feat_01",
        subject="Login update",
        sender="support@bank.com",
        body="Sign in at https://secure.banking-portal.com/login?step=1"
    )
    p_out = parser.process(email)
    f_out = feature.process(p_out)

    assert f_out.feature_count == 1
    feat = f_out.features[0].lexical_dict
    assert "url_len" in feat
    assert "kw_count" in feat
    assert feat["kw_count"] >= 2  # secure, banking, login


def test_classifier_agent():
    parser = ParserAgent()
    feature = FeatureAgent()
    classifier = ClassifierAgent()
    email = EmailPayload(
        id="test_class_01",
        subject="Security warning",
        sender="security@service.xyz",
        body="Immediate action: http://verify-login-update.pages.dev/banking/signin.html"
    )
    p_out = parser.process(email)
    f_out = feature.process(p_out)
    c_out = classifier.process(p_out, f_out)

    assert len(c_out.scored_urls) == 1
    assert 0.0 <= c_out.max_score <= 1.0
    assert len(c_out.scored_urls[0].top_features) > 0


def test_triage_agent_thresholds():
    triage = TriageAgent()
    dummy_parser = ParserOutput(
        message_id="msg_dummy",
        parsed_urls=[
            ParsedURL(
                raw_url="http://test.com",
                defanged_url="hxxp://test[.]com",
                normalized_url="test.com",
                host="test.com",
                registered_domain="test.com",
                path_query=""
            )
        ],
        url_count=1,
        has_urls=True
    )

    # 1. High score -> QUARANTINE
    c_high = ClassifierOutput(scored_urls=[], max_score=0.92, model_version="v1")
    t_high = triage.process(dummy_parser, c_high, t_low=0.05, t_high=0.85)
    assert t_high.decision == "QUARANTINE"
    assert t_high.routed_to_human is False

    # 2. Low score -> ALLOW
    c_low = ClassifierOutput(scored_urls=[], max_score=0.02, model_version="v1")
    t_low_out = triage.process(dummy_parser, c_low, t_low=0.05, t_high=0.85)
    assert t_low_out.decision == "ALLOW"
    assert t_low_out.routed_to_human is False

    # 3. Mid score -> HUMAN_REVIEW
    c_mid = ClassifierOutput(scored_urls=[], max_score=0.45, model_version="v1")
    t_mid = triage.process(dummy_parser, c_mid, t_low=0.05, t_high=0.85)
    assert t_mid.decision == "HUMAN_REVIEW"
    assert t_mid.routed_to_human is True


def test_triage_agent_safety_invariant_on_errors():
    """
    CRITICAL CONSTRAINT: Pipeline errors must default to HUMAN_REVIEW, never ALLOW.
    """
    triage = TriageAgent()

    # 1. Malformed parser error
    malformed_parser = ParserOutput(
        message_id="msg_err_1",
        parsed_urls=[],
        url_count=0,
        has_urls=False,
        is_malformed=True,
        parse_error="Corrupt encoding in MIME part"
    )
    c_empty = ClassifierOutput(scored_urls=[], max_score=0.0, model_version="v1")
    t_res1 = triage.process(malformed_parser, c_empty)
    assert t_res1.decision == "HUMAN_REVIEW"
    assert "SAFETY OVERRIDE" in t_res1.rationale

    # 2. Classifier scoring error
    valid_parser = ParserOutput(
        message_id="msg_err_2",
        parsed_urls=[],
        url_count=1,
        has_urls=True
    )
    c_error = ClassifierOutput(
        scored_urls=[],
        max_score=0.0,
        model_version="v1",
        scoring_error="Vector dimension mismatch"
    )
    t_res2 = triage.process(valid_parser, c_error)
    assert t_res2.decision == "HUMAN_REVIEW"
    assert "SAFETY OVERRIDE" in t_res2.rationale


def test_orchestrator_end_to_end_benign():
    orchestrator = PhishingPipelineOrchestrator()
    email = EmailPayload(
        id="e2e_benign_01",
        subject="Engineering Wiki",
        sender="admin@internal-tools.org",
        body="Check the style guide here: https://wikipedia.org/wiki/Phishing"
    )
    result = orchestrator.process_email(email)
    assert result.error_occurred is False
    assert result.decision in ["ALLOW", "HUMAN_REVIEW"]
    assert result.current_status == result.decision
    assert result.execution_time_ms > 0


def test_orchestrator_end_to_end_phishing():
    orchestrator = PhishingPipelineOrchestrator()
    email = EmailPayload(
        id="e2e_phish_01",
        subject="URGENT ACCOUNT VERIFICATION",
        sender="security@bank-alert.xyz",
        body="Immediate action required: http://paypal-verification-update.secure-login-account.pages.dev/banking/signin.php?token=9281"
    )
    result = orchestrator.process_email(email)
    assert result.error_occurred is False
    assert result.max_score >= 0.85
    assert result.decision == "QUARANTINE"
    assert result.current_status == "QUARANTINE"


def test_orchestrator_unhandled_exception_fallback(monkeypatch):
    """
    Verifies that an unhandled crash in any agent is caught by the orchestrator
    and safely routed to HUMAN_REVIEW.
    """
    orchestrator = PhishingPipelineOrchestrator()
    
    # Intentionally monkeypatch parser to raise an unexpected runtime error
    def broken_process(email):
        raise RuntimeError("Simulated catastrophic parser explosion")
    
    monkeypatch.setattr(orchestrator.parser, "process", broken_process)
    
    email = EmailPayload(
        id="e2e_crash_01",
        subject="Test Crash",
        sender="test@test.com",
        body="Crash test payload"
    )
    result = orchestrator.process_email(email)
    
    assert result.error_occurred is True
    assert result.decision == "HUMAN_REVIEW"
    assert result.current_status == "HUMAN_REVIEW"
    assert "Simulated catastrophic parser explosion" in result.error_message
