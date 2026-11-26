"""
scripts/email_watcher.py
Real-time Inbound Email Gateway & Mailbox Watcher for PhishTrap.

Connects to any IMAP mailbox (Gmail, Outlook, Yahoo, or corporate IMAP),
intercepts incoming unread emails, passes them through the PhishTrap
multi-agent phishing detection pipeline (via REST API /api/v1/ingest),
and automatically routes/quarantines threats before users click them.

Features:
  - IMAP SSL polling with configurable frequency.
  - Multipart MIME parsing (extracts both plain text and HTML hidden href links).
  - Dual-threshold automated triage actions:
      * AUTO_QUARANTINE (p >= 0.85): Moves threat to Spam/Trash.
      * HUMAN_REVIEW (0.05 <= p < 0.85): Logs to SecOps review queue for analyst review.
      * AUTO_ALLOW (p < 0.05): Leaves safe email in primary inbox.
  - Safe --dry-run mode to audit decisions without moving emails.
  - Built-in --simulate mode for instant end-to-end testing without credentials.
"""

import os
import sys
import re
import time
import email
import imaplib
import argparse
import logging
from email.header import decode_header
from typing import Dict, List, Tuple, Optional, Any

import requests

# Ensure project root is available on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.features.defang import extract_urls_from_text, defang_url

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("PhishTrap-Gateway")

HREF_REGEX = re.compile(r'href=[\'"]([^\'"]+)[\'"]', re.IGNORECASE)


def decode_mime_header(header_value: Optional[str]) -> str:
    """Safely decodes RFC 2047 MIME headers into a clean unicode string."""
    if not header_value:
        return ""
    try:
        decoded_fragments = decode_header(header_value)
        parts = []
        for text, encoding in decoded_fragments:
            if isinstance(text, bytes):
                encoding = encoding or "utf-8"
                try:
                    parts.append(text.decode(encoding, errors="replace"))
                except (LookupError, UnicodeDecodeError):
                    parts.append(text.decode("latin-1", errors="replace"))
            else:
                parts.append(str(text))
        return " ".join(parts).strip()
    except Exception:
        return str(header_value)


def parse_email_message(raw_bytes: bytes) -> Dict[str, Any]:
    """
    Parses raw RFC 822 email bytes into structured metadata and extracted URLs.
    Extracts text from both text/plain and HTML (including href targets).
    """
    msg = email.message_from_bytes(raw_bytes)

    subject = decode_mime_header(msg.get("Subject"))
    sender = decode_mime_header(msg.get("From"))
    date_str = msg.get("Date", "")

    body_plain_parts = []
    body_html_parts = []
    extracted_urls = []

    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))

            # Skip attachments
            if "attachment" in content_disposition:
                continue

            charset = part.get_content_charset() or "utf-8"
            payload = part.get_payload(decode=True)
            if not payload:
                continue

            try:
                decoded_text = payload.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                decoded_text = payload.decode("latin-1", errors="replace")

            if content_type == "text/plain":
                body_plain_parts.append(decoded_text)
            elif content_type == "text/html":
                body_html_parts.append(decoded_text)
                # Catch hidden href links in HTML tags
                html_links = HREF_REGEX.findall(decoded_text)
                extracted_urls.extend(html_links)
    else:
        content_type = msg.get_content_type()
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            try:
                decoded_text = payload.decode(charset, errors="replace")
            except (LookupError, UnicodeDecodeError):
                decoded_text = payload.decode("latin-1", errors="replace")

            if content_type == "text/html":
                body_html_parts.append(decoded_text)
                html_links = HREF_REGEX.findall(decoded_text)
                extracted_urls.extend(html_links)
            else:
                body_plain_parts.append(decoded_text)

    # Combine text body
    full_body = "\n".join(body_plain_parts) if body_plain_parts else "\n".join(body_html_parts)

    # Extract URLs from plain text body
    text_urls = extract_urls_from_text(full_body)
    all_urls = list(dict.fromkeys(extracted_urls + text_urls))  # Deduplicate while preserving order

    return {
        "subject": subject or "[No Subject]",
        "sender": sender or "unknown@sender",
        "date": date_str,
        "body": full_body,
        "urls": all_urls
    }


def query_phishtrap(api_url: str, subject: str, sender: str, body: str, urls: List[str], use_local_fallback: bool = True) -> Optional[Dict[str, Any]]:
    """
    Sends extracted email metadata to PhishTrap.
    Attempts REST API via HTTP; if unreachable and local fallback is enabled,
    directly executes the in-process PhishTrap ingestion engine.
    """
    payload = {
        "subject": subject,
        "sender": sender,
        "body": body if body.strip() else (urls[0] if urls else "No content"),
        "urls": urls if urls else None
    }
    try:
        resp = requests.post(api_url, json=payload, timeout=5)
        if resp.status_code in (200, 201):
            return resp.json()
        logger.error("PhishTrap API returned HTTP %s: %s", resp.status_code, resp.text)
    except requests.exceptions.RequestException as e:
        if not use_local_fallback:
            logger.error("Failed to connect to PhishTrap API at %s: %s", api_url, e)
            return None
        logger.info("REST API at %s unreachable; utilizing in-process PhishTrap engine.", api_url)
        try:
            from src.api.app import ingest_email
            from src.api.schemas import IngestRequest
            req = IngestRequest(
                subject=subject,
                sender=sender,
                body=payload["body"],
                urls=payload["urls"]
            )
            return ingest_email(req)
        except Exception as local_err:
            logger.error("Local engine execution failed: %s", local_err)
            return None
    return None


def quarantine_email(
    mail: imaplib.IMAP4_SSL,
    email_uid: bytes,
    spam_folder: str = "[Gmail]/Spam",
    dry_run: bool = False
) -> bool:
    """Moves a confirmed phishing threat out of INBOX and into the Spam/Trash folder."""
    if dry_run:
        logger.info("[DRY RUN] Would move UID %s to %s", email_uid.decode(), spam_folder)
        return True

    try:
        # Copy to Spam folder
        res, _ = mail.uid("COPY", email_uid, spam_folder)
        if res == "OK":
            # Mark original in Inbox as Deleted
            mail.uid("STORE", email_uid, "+FLAGS", "(\\Deleted)")
            mail.expunge()
            logger.info("Successfully moved threat UID %s to %s", email_uid.decode(), spam_folder)
            return True
        else:
            # Fallback if specific Spam folder name differs: mark as deleted/junk
            logger.warning("Could not copy to %s (folder may have different name). Flagging as Deleted in Inbox.", spam_folder)
            mail.uid("STORE", email_uid, "+FLAGS", "(\\Deleted)")
            mail.expunge()
            return True
    except Exception as e:
        logger.error("Error moving email UID %s to quarantine: %s", email_uid.decode(), e)
        return False


def run_scanner_cycle(
    mail: imaplib.IMAP4_SSL,
    api_url: str,
    folder: str = "INBOX",
    spam_folder: str = "[Gmail]/Spam",
    dry_run: bool = False
) -> int:
    """
    Runs a single scan pass over all UNSEEN emails in the target mailbox.
    Returns the count of processed messages.
    """
    mail.select(folder)
    status, data = mail.uid("SEARCH", None, "UNSEEN")
    if status != "OK" or not data or not data[0]:
        return 0

    uids = data[0].split()
    logger.info("Found %d unread message(s) in %s. Analyzing...", len(uids), folder)

    for uid in uids:
        status, fetch_data = mail.uid("FETCH", uid, "(RFC822)")
        if status != "OK" or not fetch_data or not fetch_data[0]:
            continue

        raw_email = fetch_data[0][1]
        parsed = parse_email_message(raw_email)

        logger.info("------------------------------------------------------------")
        logger.info("Inspecting: '%s' from <%s>", parsed["subject"], parsed["sender"])
        logger.info("Detected %d URL(s) in email payload.", len(parsed["urls"]))

        # Query PhishTrap
        triage = query_phishtrap(
            api_url=api_url,
            subject=parsed["subject"],
            sender=parsed["sender"],
            body=parsed["body"],
            urls=parsed["urls"]
        )

        if not triage:
            logger.warning("Skipping email UID %s due to API failure. Left as UNSEEN.", uid.decode())
            continue

        decision = triage.get("automated_decision", "HUMAN_REVIEW")
        max_score = triage.get("max_score", 0.0)
        msg_id = triage.get("id", "unknown")

        if decision in ("QUARANTINE", "AUTO_QUARANTINE"):
            logger.warning("🔴 [AUTO_QUARANTINE] Threat Confirmed! Risk Score: %.1f%%", max_score * 100)
            for u in triage.get("urls", []):
                logger.warning("   └─ URL: %s | Score: %.3f", u.get("defanged_url"), u.get("score", 0.0))
            quarantine_email(mail, uid, spam_folder=spam_folder, dry_run=dry_run)

        elif decision in ("HUMAN_REVIEW", "REVIEW"):
            logger.info("🟡 [HUMAN_REVIEW] Ambiguous Edge-Case. Risk Score: %.1f%%", max_score * 100)
            logger.info("   └─ Queued in SecOps Review Console (ID: %s)", msg_id)
            mail.uid("STORE", uid, "+FLAGS", "(\\Flagged)")

        else:
            logger.info("🟢 [AUTO_ALLOW] Email Cleared Safe. Risk Score: %.1f%%", max_score * 100)
            mail.uid("STORE", uid, "+FLAGS", "(\\Seen)")

    return len(uids)


def run_simulation(api_url: str):
    """
    Runs an instant end-to-end verification of the email gateway logic
    using synthetic benign, phishing, and edge-case samples.
    """
    print("\n============================================================")
    print("      PhishTrap Inbound Email Gateway - Simulation Mode     ")
    print("============================================================\n")
    print(f"Target API Endpoint: {api_url}")

    test_emails = [
        {
            "name": "Legitimate Notification",
            "subject": "Python Software Foundation: Weekly Newsletter",
            "sender": "newsletter@python.org",
            "body": "The latest Python releases and documentation updates are now available at https://www.python.org/downloads/. Happy coding!",
            "urls": ["https://www.python.org/downloads/"]
        },
        {
            "name": "High-Risk Credential Harvesting Phish",
            "subject": "URGENT: Your PayPal Account Has Been Suspended",
            "sender": "security-alert@paypa1-support-portal.xyz",
            "body": "Dear customer, your account requires immediate re-verification. Click here: http://secure-login-paypa1.pages.dev/update-account-token",
            "urls": ["http://secure-login-paypa1.pages.dev/update-account-token"]
        },
        {
            "name": "Ambiguous Edge-Case (SecOps Human Review)",
            "subject": "Shared invoice documents for quarterly review",
            "sender": "billing-notice@partner-sharepoint-docs.co",
            "body": "Please review the attached invoice summary at https://billing-review-team.io/portal/document?id=99281.",
            "urls": ["https://billing-review-team.io/portal/document?id=99281"]
        }
    ]

    for item in test_emails:
        print(f"\n[+] Testing: {item['name']}")
        print(f"    Subject: {item['subject']}")
        print(f"    Sender:  {item['sender']}")
        print(f"    Link:    {item['urls'][0]}")

        res = query_phishtrap(api_url, item["subject"], item["sender"], item["body"], item["urls"])
        if res:
            decision = res.get("automated_decision")
            score = res.get("max_score", 0.0)
            msg_id = res.get("id")
            
            if decision in ("QUARANTINE", "AUTO_QUARANTINE"):
                badge = "🔴 AUTO_QUARANTINE"
                action_text = "Action: Threat intercepted! Automatically moved to Quarantine/Spam folder."
            elif decision in ("HUMAN_REVIEW", "REVIEW"):
                badge = "🟡 HUMAN_REVIEW"
                action_text = f"Action: Suspicious edge-case held in Review Queue (ID: {msg_id}) for SecOps analyst verification."
            else:
                badge = "🟢 AUTO_ALLOW"
                action_text = "Action: Verified safe. Delivered to Primary Inbox."

            print(f"    Result:  {badge} (Risk: {score * 100:.2f}%)")
            print(f"    {action_text}")
            if res.get("urls"):
                u = res["urls"][0]
                print(f"    Defanged: {u.get('defanged_url')}")
                if u.get("top_features"):
                    print(f"    Signals:  {', '.join(u.get('top_features'))}")
        else:
            print("    [!] API call failed. Is the PhishTrap server running?")

    print("\n============================================================")
    print("Simulation complete! Check your SecOps Dashboard at http://localhost:8000")
    print("============================================================\n")


def main():
    parser = argparse.ArgumentParser(
        description="PhishTrap Inbound Email Gateway & Real-time Mailbox Scanner."
    )
    parser.add_argument("--server", default=os.getenv("PHISHTRAP_IMAP_SERVER", "imap.gmail.com"),
                        help="IMAP server hostname (default: imap.gmail.com)")
    parser.add_argument("--port", type=int, default=int(os.getenv("PHISHTRAP_IMAP_PORT", "993")),
                        help="IMAP SSL port (default: 993)")
    parser.add_argument("--user", default=os.getenv("PHISHTRAP_EMAIL_USER"),
                        help="Email address / username (or PHISHTRAP_EMAIL_USER env)")
    parser.add_argument("--password", default=os.getenv("PHISHTRAP_EMAIL_PASS"),
                        help="Email app password (or PHISHTRAP_EMAIL_PASS env)")
    parser.add_argument("--api-url", default=os.getenv("PHISHTRAP_API_URL", "http://localhost:8000/api/v1/ingest"),
                        help="PhishTrap Ingest API endpoint (default: http://localhost:8000/api/v1/ingest)")
    parser.add_argument("--folder", default="INBOX",
                        help="Mailbox folder to monitor (default: INBOX)")
    parser.add_argument("--spam-folder", default="[Gmail]/Spam",
                        help="Quarantine folder destination (default: [Gmail]/Spam, use 'Junk' for Outlook)")
    parser.add_argument("--interval", type=int, default=30,
                        help="Seconds between inbox polling cycles (default: 30)")
    parser.add_argument("--once", action="store_true",
                        help="Run a single scan cycle and exit")
    parser.add_argument("--dry-run", action="store_true",
                        help="Audit mode: analyze emails without moving or altering them")
    parser.add_argument("--simulate", action="store_true",
                        help="Run test simulation with synthetic emails without requiring IMAP credentials")

    args = parser.parse_args()

    # If --simulate is requested, run simulation and exit
    if args.simulate:
        run_simulation(args.api_url)
        return

    # Validate required credentials for live mode
    if not args.user or not args.password:
        logger.error("Missing credentials! Pass --user and --password or set PHISHTRAP_EMAIL_USER and PHISHTRAP_EMAIL_PASS.")
        logger.error("Tip: Test the watcher immediately without credentials using: python scripts/email_watcher.py --simulate")
        sys.exit(1)

    logger.info("Initializing PhishTrap Email Gateway...")
    logger.info("Connecting to %s:%d as %s", args.server, args.port, args.user)
    logger.info("Triage API: %s | Poll Interval: %ds | Dry Run: %s", args.api_url, args.interval, args.dry_run)

    while True:
        try:
            mail = imaplib.IMAP4_SSL(args.server, args.port)
            mail.login(args.user, args.password)
            
            run_scanner_cycle(
                mail=mail,
                api_url=args.api_url,
                folder=args.folder,
                spam_folder=args.spam_folder,
                dry_run=args.dry_run
            )
            
            mail.logout()
        except KeyboardInterrupt:
            logger.info("PhishTrap Email Gateway stopped by user.")
            break
        except Exception as e:
            logger.error("Connection or processing error: %s. Retrying in %ds...", e, args.interval)

        if args.once:
            break

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
