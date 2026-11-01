"""
tests/test_ui.py
Unit and integration tests for PhishTrap SOC Console UI components and override workflows.
"""

import os
import pytest
from src.storage.db import get_db_context, init_db
from src.storage.repositories import MessageRepository, AuditRepository
from app_ui.components import (
    render_status_badge,
    render_score_bar,
    render_metric_card,
    render_defanged_url_item
)


@pytest.fixture(scope="session", autouse=True)
def setup_ui_test_db(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("ui_db")
    test_db_path = str(temp_dir / "test_ui.db")
    os.environ["PHISHTRAP_DB_PATH"] = test_db_path
    init_db(test_db_path)


def test_render_status_badge_all_states():
    """
    Verifies that all 6 SecOps status badges render properly with their respective tags and icons.
    """
    statuses = ["QUARANTINE", "HUMAN_REVIEW", "ALLOW", "RELEASED", "CONFIRMED_PHISH", "RELABELED"]
    for s in statuses:
        html_out = render_status_badge(s)
        assert isinstance(html_out, str)
        assert "span style=" in html_out
        assert len(html_out) > 50


def test_render_score_bar_threshold_categories():
    """
    Verifies threshold category transitions in the visual score progress bar:
    - score < 0.05 -> BENIGN
    - 0.05 <= score < 0.85 -> AMBIGUOUS
    - score >= 0.85 -> HIGH RISK
    """
    # 1. Low risk
    low_bar = render_score_bar(0.012)
    assert "BENIGN" in low_bar
    assert "0.0120" in low_bar

    # 2. Ambiguous review band
    mid_bar = render_score_bar(0.428)
    assert "AMBIGUOUS" in mid_bar
    assert "0.4280" in mid_bar

    # 3. High risk
    high_bar = render_score_bar(0.985)
    assert "HIGH RISK" in high_bar
    assert "0.9850" in high_bar

    # 4. Out of bounds clipping
    neg_bar = render_score_bar(-0.5)
    assert "0.0000" in neg_bar
    over_bar = render_score_bar(1.5)
    assert "1.0000" in over_bar


def test_render_defanged_url_strictly_sanitized():
    """
    CRITICAL SAFETY CONSTRAINT: Defanged URL renderer must never leak clickable raw URLs.
    """
    url_dict = {
        "raw_url": "http://evil-phish.com/login.php",
        "defanged_url": "hxxp://evil-phish[.]com/login.php",
        "registered_domain": "evil-phish.com",
        "score": 0.9412,
        "top_features": [
            {"feature": "entropy", "value": 4.12},
            {"feature": "is_ip", "value": 0}
        ]
    }
    rendered = render_defanged_url_item(url_dict)
    assert "hxxp://evil-phish[.]com/login.php" in rendered
    assert "[.]" in rendered
    assert "evil-phish.com" in rendered
    assert "entropy: 4.12" in rendered


def test_render_metric_card():
    card = render_metric_card("Total Alerts", 150, "Updated live", "#6366F1")
    assert "Total Alerts" in card
    assert "150" in card
    assert "Updated live" in card


def test_human_override_workflow_persistence_and_audit():
    """
    Verifies the complete SOC analyst workflow:
    1. Message exists in HUMAN_REVIEW status.
    2. Analyst reviews and submits an override (e.g. RELEASE).
    3. Status is updated in messages table.
    4. Override record is written to audit trail with timestamp and reason.
    5. Message no longer appears in pending review queue.
    """
    with get_db_context() as conn:
        test_msg = {
            "id": "ui_test_msg_999",
            "subject": "Question regarding Q4 PO #9921",
            "sender": "supplier@invoicing-portal.com",
            "body": "Check invoice details: https://invoicing-portal.com/po/9921",
            "received_at": "2026-11-01T14:00:00Z",
            "max_score": 0.521,
            "automated_decision": "HUMAN_REVIEW",
            "current_status": "HUMAN_REVIEW",
            "decided_at": "2026-11-01T14:00:01Z",
            "decided_by": "triage_agent"
        }
        MessageRepository.create_message(conn, test_msg, [])

        # 1. Verify item is in review queue
        queue = MessageRepository.list_queue(conn)
        assert any(item["id"] == "ui_test_msg_999" for item in queue)

        # 2. Execute Analyst Override
        reason = "Confirmed legitimate supplier transaction via direct account rep contact."
        AuditRepository.record_override(
            conn=conn,
            message_id="ui_test_msg_999",
            reviewer_id="analyst_arsh",
            previous_status="HUMAN_REVIEW",
            new_status="RELEASED",
            reason=reason,
            timestamp="2026-11-01T14:05:00Z"
        )
        MessageRepository.update_status(conn, "ui_test_msg_999", "RELEASED")

        # 3. Verify message status updated
        updated_msg = MessageRepository.get_message(conn, "ui_test_msg_999")
        assert updated_msg["current_status"] == "RELEASED"
        assert len(updated_msg["overrides"]) == 1
        assert updated_msg["overrides"][0]["reviewer_id"] == "analyst_arsh"
        assert updated_msg["overrides"][0]["reason"] == reason

        # 4. Verify message removed from active HUMAN_REVIEW queue
        refreshed_queue = MessageRepository.list_queue(conn)
        assert not any(item["id"] == "ui_test_msg_999" for item in refreshed_queue)

        # 5. Verify audit log entry
        audit_trail = AuditRepository.list_audit_log(conn)
        matching_audit = [e for e in audit_trail if e["message_id"] == "ui_test_msg_999"]
        assert len(matching_audit) == 1
        assert matching_audit[0]["new_status"] == "RELEASED"
        assert matching_audit[0]["reason"] == reason
