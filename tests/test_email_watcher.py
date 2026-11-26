"""
tests/test_email_watcher.py
Unit tests for the inbound email gateway and MIME email parser.
"""

import pytest
from scripts.email_watcher import (
    decode_mime_header,
    parse_email_message,
    query_phishtrap
)


def test_decode_mime_header():
    # Plain ascii
    assert decode_mime_header("Simple Subject") == "Simple Subject"
    # None or empty
    assert decode_mime_header(None) == ""
    # RFC 2047 encoded header (=?UTF-8?B?...?=)
    encoded = "=?UTF-8?B?8J+UuSBBbGVydDogU3VzcGljaW91cyBBY3Rpdml0eQ==?="
    decoded = decode_mime_header(encoded)
    assert "Alert: Suspicious Activity" in decoded


def test_parse_email_message_plain():
    raw_rfc822 = (
        b"From: security@company.com\r\n"
        b"To: user@company.com\r\n"
        b"Subject: Please verify https://python.org\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n"
        b"\r\n"
        b"Hello, check out https://python.org/downloads for new releases."
    )
    parsed = parse_email_message(raw_rfc822)
    assert parsed["sender"] == "security@company.com"
    assert "https://python.org" in parsed["subject"]
    assert any("python.org" in u for u in parsed["urls"])


def test_parse_email_message_html_hidden_href():
    raw_html = (
        b"From: hr@portal.net\r\n"
        b"Subject: Payroll Review\r\n"
        b"Content-Type: text/html; charset=utf-8\r\n"
        b"\r\n"
        b"<html><body>Click <a href=\"http://secure-login-paypa1.pages.dev/auth\">here</a> to verify.</body></html>"
    )
    parsed = parse_email_message(raw_html)
    assert "http://secure-login-paypa1.pages.dev/auth" in parsed["urls"]


def test_query_phishtrap_engine():
    res = query_phishtrap(
        api_url="http://localhost:8000/api/v1/ingest",
        subject="Suspicious alert",
        sender="attacker@fake.xyz",
        body="Verify your account now",
        urls=["http://secure-login-paypa1.pages.dev/update-account-token"],
        use_local_fallback=True
    )
    assert res is not None
    assert "automated_decision" in res
    assert res["automated_decision"] in ("QUARANTINE", "AUTO_QUARANTINE")
    assert res["max_score"] >= 0.85
