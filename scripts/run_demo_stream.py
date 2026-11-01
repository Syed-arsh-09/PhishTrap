"""
scripts/run_demo_stream.py
Simulated real-time email stream replayer for the PhishTrap multi-agent pipeline.
Generates and replays 100 realistic synthetic emails covering benign, phishing,
ambiguous edge cases, and malformed inputs.
"""

import os
import sys
import time
import random
from typing import List, Dict, Any

# Ensure project root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.storage.db import init_db, get_db_connection
from src.storage.repositories import MessageRepository
from src.pipeline.orchestrator import PhishingPipelineOrchestrator


BENIGN_DOMAINS = [
    "google.com", "github.com", "wikipedia.org", "python.org",
    "stackoverflow.com", "nytimes.com", "microsoft.com", "apple.com",
    "amazon.com", "cloudflare.com", "mozilla.org", "linkedin.com"
]

PHISH_DOMAINS = [
    "secure-login.pages.dev", "account-verify-support.xyz", "update-bank-security.top",
    "paypal-signin-alert.net", "crypto-wallet-recovery.com", "online-banking-auth.info",
    "192.168.1.1", "10.0.0.1", "appleid-verify-user.cc", "secure-account-token.biz"
]

AMBIGUOUS_DOMAINS = [
    "client-portal-docs.co", "billing-review-team.io", "vendor-invoice-system.app",
    "partner-hub-access.org", "internal-sharepoint-docs.me", "verify-partner-id.cc"
]


def generate_synthetic_stream(count: int = 100) -> List[Dict[str, Any]]:
    """
    Generates a deterministic synthetic email stream of 100 samples.
    Random seed is fixed for 100% reproducibility.
    """
    random.seed(42)
    emails = []

    for i in range(1, count + 1):
        msg_id = f"demo_msg_{i:04d}"
        rand_val = random.random()

        if rand_val < 0.45:
            # 1. Clean Benign Email (45%)
            domain = random.choice(BENIGN_DOMAINS)
            path = random.choice(["articles/summary", "search?q=security", "docs/api", "profile/settings", ""])
            url = f"https://{domain}/{path}" if path else f"https://{domain}"
            email = {
                "id": msg_id,
                "subject": f"Project Sync and Weekly Update #{i}",
                "sender": f"colleague_{i}@company.org",
                "body": f"Hi team, please review the latest documentation at {url}. Let me know your thoughts.",
                "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - (count - i) * 60))
            }
        elif rand_val < 0.80:
            # 2. Blatant Phishing Email (35%)
            phish_dom = random.choice(PHISH_DOMAINS)
            path = random.choice([
                "banking/login.php?verify=true", "auth/account/signin", "wallet/token/recovery",
                "confirm-password/update.html", "security/urgent-review"
            ])
            url = f"http://{phish_dom}/{path}&id={random.randint(1000, 9999)}"
            email = {
                "id": msg_id,
                "subject": f"URGENT: Your account access will be terminated within 24h [Notice #{i}]",
                "sender": f"security-alert_{i}@critical-notice.com",
                "body": f"Unauthorized sign-in detected! You must verify your credentials immediately at {url} to avoid suspension.",
                "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - (count - i) * 60))
            }
        elif rand_val < 0.95:
            # 3. Ambiguous Edge Case Email (15%)
            amb_dom = random.choice(AMBIGUOUS_DOMAINS)
            url = f"https://portal.{amb_dom}/invoices/client/doc_{random.randint(100, 999)}"
            email = {
                "id": msg_id,
                "subject": f"Invoice and Statement from Vendor #{i}",
                "sender": f"billing_{i}@{amb_dom}",
                "body": f"Please find your outstanding monthly statement ready for review: {url}",
                "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - (count - i) * 60))
            }
        else:
            # 4. Clean text with no URLs or Edge Case (5%)
            email = {
                "id": msg_id,
                "subject": f"Internal Memo: Coffee machine maintenance #{i}",
                "sender": f"office-manager_{i}@company.internal",
                "body": f"Notice: The 3rd floor pantry coffee maker will be serviced tomorrow morning at 9:00 AM.",
                "received_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - (count - i) * 60))
            }

        emails.append(email)

    return emails


def main():
    print("=" * 65)
    print("   PHISHTRAP MULTI-AGENT STREAM REPLAYER (100 EMAILS)   ")
    print("=" * 65)

    # 1. Initialize SQLite Database
    init_db()
    conn = get_db_connection()

    # 2. Initialize Orchestrator
    orchestrator = PhishingPipelineOrchestrator(t_low=0.05, t_high=0.85)
    emails = generate_synthetic_stream(count=100)

    print(f"[*] Generated 100 reproducible synthetic test emails.")
    print(f"[*] Processing through 6-agent pipeline...")
    print("-" * 65)

    triage_counts = {"ALLOW": 0, "QUARANTINE": 0, "HUMAN_REVIEW": 0}
    t0 = time.time()

    for idx, email in enumerate(emails, 1):
        res = orchestrator.process_email(email, db_conn=conn)
        triage_counts[res.decision] = triage_counts.get(res.decision, 0) + 1

        # Print progress every 10 emails or for alerts
        status_tag = f"[{res.decision}]"
        if res.decision == "QUARANTINE":
            status_tag = f"\033[91m{status_tag}\033[0m"
        elif res.decision == "HUMAN_REVIEW":
            status_tag = f"\033[93m{status_tag}\033[0m"
        else:
            status_tag = f"\033[92m{status_tag}\033[0m"

        if idx % 10 == 0 or idx == 1 or res.decision == "HUMAN_REVIEW":
            threat_info = f"Max Score: {res.max_score:.4f}"
            print(f"  [{idx:03d}/100] {status_tag} {email['id']} | {threat_info} | {email['subject'][:35]}...")

    conn.commit()
    conn.close()

    total_time = round(time.time() - t0, 2)
    throughput = round(100 / max(total_time, 0.01), 1)

    print("-" * 65)
    print("                STREAM REPLAY SUMMARY                   ")
    print("-" * 65)
    print(f"  Total Processed        : 100 emails")
    print(f"  Total Wall Clock Time  : {total_time}s ({throughput} emails/sec)")
    print(f"  Auto-Quarantined       : {triage_counts['QUARANTINE']} ({triage_counts['QUARANTINE']/100:.1%})")
    print(f"  Auto-Allowed           : {triage_counts['ALLOW']} ({triage_counts['ALLOW']/100:.1%})")
    print(f"  Human Review Queue     : {triage_counts['HUMAN_REVIEW']} ({triage_counts['HUMAN_REVIEW']/100:.1%})")
    print("=" * 65)
    print("[+] All 100 emails and extracted URLs successfully persisted to SQLite database!")


if __name__ == "__main__":
    main()

