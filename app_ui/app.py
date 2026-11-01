"""
app_ui/app.py
PhishTrap SOC Console — Real-Time Phishing Detection & Human-in-the-Loop Override.
Impeccable, human-crafted cybersecurity operations dashboard built with Streamlit.
"""

import sys
import os
import time
import json
import streamlit as st
from datetime import datetime

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.storage.db import get_db_context, init_db
from src.storage.repositories import MessageRepository, AuditRepository
from src.pipeline.orchestrator import PhishingPipelineOrchestrator
from src.pipeline.contracts import EmailPayload
from src.features.defang import defang_url
from app_ui.theme import SOC_CUSTOM_CSS
from app_ui.components import (
    render_status_badge,
    render_score_bar,
    render_metric_card,
    render_defanged_url_item
)

# Set page configuration
st.set_page_config(
    page_title="PhishTrap SecOps Console",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Apply bespoke cyber theme
st.markdown(SOC_CUSTOM_CSS, unsafe_allow_html=True)

# Initialize database schema if needed
init_db()


def main():
    # -------------------------------------------------------------
    # Sidebar: Operational Controls & SecOps Context
    # -------------------------------------------------------------
    with st.sidebar:
        st.markdown(
            """
            <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 15px;">
                <span style="font-size: 1.8rem;">🛡️</span>
                <div>
                    <h2 style="margin: 0; font-size: 1.15rem; font-weight: 800; color: #FFFFFF;">PHISHTRAP</h2>
                    <div style="font-size: 0.72rem; color: #6366F1; font-weight: 700; letter-spacing: 0.08em;">HUMAN-IN-THE-LOOP SOC</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")
        
        # SecOps Reviewer Profile
        st.markdown("<div style='font-size: 0.78rem; font-weight: 700; color: #94A3B8; margin-bottom: 4px;'>ANALYST PROFILE</div>", unsafe_allow_html=True)
        analyst_name = st.text_input("Reviewer Handle", value="analyst_arsh", key="analyst_handle")

        # Triage Thresholds Visualization
        st.markdown("---")
        st.markdown("<div style='font-size: 0.78rem; font-weight: 700; color: #94A3B8; margin-bottom: 6px;'>TRIAGE POLICIES</div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="background: #0B111D; border: 1px solid rgba(255, 255, 255, 0.07); border-radius: 8px; padding: 10px; font-size: 0.76rem;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #10B981; font-weight: 600;">Auto-Allow (T_low)</span>
                    <span style="font-family: 'JetBrains Mono', monospace; color: #E2E8F0;">&lt; 0.0500</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span style="color: #F59E0B; font-weight: 600;">Human Review Band</span>
                    <span style="font-family: 'JetBrains Mono', monospace; color: #E2E8F0;">0.0500 - 0.8500</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                    <span style="color: #EF4444; font-weight: 600;">Auto-Quarantine (T_high)</span>
                    <span style="font-family: 'JetBrains Mono', monospace; color: #E2E8F0;">&ge; 0.8500</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown("---")
        st.markdown("<div style='font-size: 0.78rem; font-weight: 700; color: #94A3B8; margin-bottom: 4px;'>SYSTEM HEALTH</div>", unsafe_allow_html=True)
        st.markdown(
            """
            <div style="font-size: 0.74rem; color: #94A3B8;">
                <div>🟢 Database: <strong>Connected</strong> (SQLite WAL)</div>
                <div style="margin-top: 4px;">⚡ Model: <strong>v1.0.0-lexical-tfidf</strong></div>
                <div style="margin-top: 4px;">🔒 Safety Defanging: <strong>Active</strong></div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("🔄 Refresh Data", use_container_width=True):
            st.rerun()

    # -------------------------------------------------------------
    # Top Hero Header
    # -------------------------------------------------------------
    st.markdown(
        """
        <div class="soc-hero">
            <div class="soc-title-wrap">
                <h1>Security Operations Center (SOC) Console</h1>
                <div class="soc-subtitle">Real-Time Phishing Threat Ingestion, Triage & Human-in-the-Loop Override</div>
            </div>
            <div>
                <div class="soc-live-badge">
                    <div class="pulse-dot"></div>
                    Pipeline Active
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    # -------------------------------------------------------------
    # Primary Navigation Tabs
    # -------------------------------------------------------------
    tab_queue, tab_inspect, tab_audit, tab_metrics, tab_sandbox = st.tabs([
        "📋 Human Review Queue",
        "🔍 Message Investigation & Override",
        "📜 Immutable Audit Trail",
        "📊 Triage Metrics & Telemetry",
        "⚡ Ingestion Sandbox"
    ])

    # -------------------------------------------------------------
    # TAB 1: Human Review Queue
    # -------------------------------------------------------------
    with tab_queue:
        st.markdown("### Pending Human Review Items")
        st.caption("Messages landing in the ambiguous probability band (0.0500 ≤ score < 0.8500) awaiting SecOps analyst verification.")

        with get_db_context() as conn:
            queue_items = MessageRepository.list_queue(conn, limit=100)

        col_q1, col_q2 = st.columns([3, 1])
        with col_q1:
            search_query = st.text_input("Filter Queue by Sender or Subject", placeholder="Type to search...", key="queue_search")
        with col_q2:
            st.metric("Queue Depth", len(queue_items))

        if search_query:
            filtered_queue = [
                q for q in queue_items
                if search_query.lower() in q["sender"].lower() or search_query.lower() in q["subject"].lower()
            ]
        else:
            filtered_queue = queue_items

        if not filtered_queue:
            st.info("🎉 The human review queue is currently clear! No ambiguous messages pending.")
        else:
            for item in filtered_queue:
                msg_id = item["id"]
                score = item.get("max_score", 0.0)
                urls = item.get("urls", [])
                
                with st.container():
                    st.markdown(
                        f"""
                        <div class="soc-card">
                            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 15px;">
                                <div style="flex-grow: 1;">
                                    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 6px;">
                                        {render_status_badge(item.get("current_status", "HUMAN_REVIEW"))}
                                        <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.76rem; color: #64748B;">{msg_id}</span>
                                        <span style="font-size: 0.76rem; color: #94A3B8;">Received: {item.get("received_at", "N/A")}</span>
                                    </div>
                                    <div style="font-weight: 700; font-size: 1.05rem; color: #FFFFFF; margin-bottom: 4px;">
                                        {item.get("subject", "(No Subject)")}
                                    </div>
                                    <div style="font-size: 0.82rem; color: #94A3B8;">
                                        Sender: <span style="color: #E2E8F0; font-weight: 500;">{item.get("sender", "unknown")}</span> | URLs Contained: <strong style="color: #38BDF8;">{len(urls)}</strong>
                                    </div>
                                </div>
                                <div style="min-width: 170px;">
                                    {render_score_bar(score)}
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
                    if st.button(f"🔍 Investigate {msg_id}", key=f"btn_investigate_{msg_id}"):
                        st.session_state["selected_msg_id"] = msg_id
                        st.success(f"Selected {msg_id}! Switch to 'Message Investigation & Override' tab to review.")

    # -------------------------------------------------------------
    # TAB 2: Message Investigation & Human Override
    # -------------------------------------------------------------
    with tab_inspect:
        st.markdown("### Message Deep Inspection Workbench")
        st.caption("Inspect raw headers, analyze defanged URLs, examine ML feature explanations, and execute logged SecOps decisions.")

        # Determine which message to inspect
        target_id = st.session_state.get("selected_msg_id", None)
        
        col_sel1, col_sel2 = st.columns([3, 1])
        with col_sel1:
            manual_id = st.text_input("Enter Message ID to Inspect", value=target_id or "", placeholder="e.g. demo_msg_0003")
        with col_sel2:
            inspect_btn = st.button("Load Message Dossier", use_container_width=True)

        active_id = manual_id.strip() if (manual_id and inspect_btn) or manual_id else target_id

        if not active_id:
            st.info("👈 Select a message from the Human Review Queue or enter a Message ID above to begin investigation.")
        else:
            with get_db_context() as conn:
                msg = MessageRepository.get_message(conn, active_id)

            if not msg:
                st.error(f"Message ID '{active_id}' was not found in the database.")
            else:
                col_dossier, col_action = st.columns([3, 2], gap="large")

                with col_dossier:
                    st.markdown("#### Message Metadata & Content")
                    st.markdown(
                        f"""
                        <div class="soc-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.85rem; color: #6366F1; font-weight: 700;">{msg['id']}</span>
                                {render_status_badge(msg['current_status'])}
                            </div>
                            <div style="font-size: 0.85rem; margin-bottom: 6px;">
                                <strong style="color: #94A3B8;">Subject:</strong> <span style="color: #FFFFFF; font-weight: 600;">{msg['subject']}</span>
                            </div>
                            <div style="font-size: 0.85rem; margin-bottom: 6px;">
                                <strong style="color: #94A3B8;">Sender:</strong> <span style="color: #38BDF8; font-family: 'JetBrains Mono', monospace;">{msg['sender']}</span>
                            </div>
                            <div style="font-size: 0.82rem; margin-bottom: 12px; color: #64748B;">
                                <strong>Received:</strong> {msg['received_at']} | <strong>Automated Decision:</strong> {msg['automated_decision']}
                            </div>
                            <div style="border-top: 1px solid rgba(255, 255, 255, 0.08); padding-top: 10px; margin-top: 10px;">
                                <div style="font-size: 0.76rem; font-weight: 700; color: #94A3B8; text-transform: uppercase; margin-bottom: 6px;">Email Body Content</div>
                                <div style="background: #070B14; padding: 12px; border-radius: 6px; font-size: 0.85rem; line-height: 1.5; color: #CBD5E1; max-height: 200px; overflow-y: auto;">
                                    {html.escape(msg['body'])}
                                </div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    st.markdown("#### Extracted & Defanged URLs")
                    urls = msg.get("urls", [])
                    if not urls:
                        st.markdown("<div style='color: #64748B; font-size: 0.85rem;'>No URLs detected in this email.</div>", unsafe_allow_html=True)
                    else:
                        for u in urls:
                            st.markdown(render_defanged_url_item(u), unsafe_allow_html=True)

                with col_action:
                    st.markdown("#### Analyst Decision Console")
                    st.markdown(
                        """
                        <div style="background: rgba(99, 102, 241, 0.08); border: 1px solid rgba(99, 102, 241, 0.25); border-radius: 8px; padding: 12px; font-size: 0.8rem; color: #C7D2FE; margin-bottom: 15px;">
                            🛡️ <strong>Safety Invariant:</strong> Every action is permanent, atomic, and recorded in the audit trail. A valid justification of at least 5 characters is mandatory.
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                    override_action = st.radio(
                        "Select Override Action",
                        options=["RELEASE", "CONFIRM_PHISH", "RELABEL"],
                        format_func=lambda x: {
                            "RELEASE": "📬 Release to Inbox (False Positive)",
                            "CONFIRM_PHISH": "🚨 Confirm Phish & Block (True Positive)",
                            "RELABEL": "🏷️ Relabel for Model Retraining"
                        }[x]
                    )

                    override_reason = st.text_area(
                        "Analyst Justification (Mandatory)",
                        placeholder="Provide clear rationale (e.g. 'Verified authentic sender via out-of-band phone call; invoice ID corresponds to active PO #4892').",
                        height=110
                    )

                    if st.button("⚡ Execute & Commit Decision", use_container_width=True, type="primary"):
                        if not override_reason or len(override_reason.strip()) < 5:
                            st.error("❌ Justification must contain at least 5 characters.")
                        else:
                            status_map = {
                                "RELEASE": "RELEASED",
                                "CONFIRM_PHISH": "CONFIRMED_PHISH",
                                "RELABEL": "RELABELED"
                            }
                            new_status = status_map[override_action]
                            prev_status = msg["current_status"]
                            
                            if prev_status == new_status:
                                st.warning(f"⚠️ Message is already in status '{new_status}'.")
                            else:
                                with get_db_context() as conn:
                                    # Record override
                                    now_ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                                    AuditRepository.record_override(
                                        conn=conn,
                                        message_id=msg["id"],
                                        reviewer_id=analyst_name,
                                        previous_status=prev_status,
                                        new_status=new_status,
                                        reason=override_reason.strip(),
                                        timestamp=now_ts
                                    )
                                    # Update message status
                                    MessageRepository.update_status(conn, msg["id"], new_status)
                                
                                st.success(f"✅ Successfully updated status from {prev_status} to {new_status}!")
                                time.sleep(0.8)
                                st.rerun()

                    # Show previous overrides for this message
                    overrides = msg.get("overrides", [])
                    if overrides:
                        st.markdown("---")
                        st.markdown("<div style='font-size: 0.8rem; font-weight: 700; color: #94A3B8;'>PREVIOUS OVERRIDES ON THIS MESSAGE</div>", unsafe_allow_html=True)
                        for ov in overrides:
                            st.markdown(
                                f"""
                                <div style="background: #080C14; border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 6px; padding: 8px 10px; margin-top: 6px; font-size: 0.78rem;">
                                    <div style="display: flex; justify-content: space-between;">
                                        <span style="color: #6366F1; font-weight: 600;">{ov['reviewer_id']}</span>
                                        <span style="color: #64748B;">{ov['timestamp']}</span>
                                    </div>
                                    <div style="margin: 4px 0; color: #E2E8F0;">
                                        <strong>{ov['previous_status']}</strong> &rarr; <strong style="color: #38BDF8;">{ov['new_status']}</strong>
                                    </div>
                                    <div style="color: #94A3B8; font-style: italic;">"{ov['reason']}"</div>
                                </div>
                                """,
                                unsafe_allow_html=True
                            )

    # -------------------------------------------------------------
    # TAB 3: Immutable Audit Trail
    # -------------------------------------------------------------
    with tab_audit:
        st.markdown("### Immutable Compliance & Audit Trail")
        st.caption("Chronological record of all SecOps analyst overrides, decisions, timestamps, and justifications.")

        with get_db_context() as conn:
            audit_entries = AuditRepository.list_audit_log(conn, limit=100)

        if not audit_entries:
            st.info("No human overrides have been recorded yet. Decisions made via the workbench will appear here.")
        else:
            st.markdown(f"**Total Historical Overrides:** `{len(audit_entries)}`")
            for entry in audit_entries:
                st.markdown(
                    f"""
                    <div class="soc-card" style="padding: 12px 16px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <div style="display: flex; align-items: center; gap: 8px;">
                                <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.82rem; font-weight: 700; color: #38BDF8;">{entry['message_id']}</span>
                                <span style="color: #64748B;">|</span>
                                <span style="font-size: 0.82rem; color: #E2E8F0;">{entry.get('subject', 'N/A')}</span>
                            </div>
                            <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.74rem; color: #64748B;">{entry['timestamp']}</span>
                        </div>
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
                            <div style="font-size: 0.82rem; color: #94A3B8;">
                                Transition: <strong style="color: #F59E0B;">{entry['previous_status']}</strong> &rarr; <strong style="color: #10B981;">{entry['new_status']}</strong>
                                &nbsp;|&nbsp; Reviewer: <span style="color: #A5B4FC; font-weight: 600;">{entry['reviewer_id']}</span>
                            </div>
                        </div>
                        <div style="margin-top: 8px; background: #070B14; border-radius: 6px; padding: 8px 12px; font-size: 0.8rem; color: #CBD5E1; border-left: 3px solid #6366F1;">
                            <strong>Justification:</strong> "{entry['reason']}"
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

    # -------------------------------------------------------------
    # TAB 4: Triage Metrics & Telemetry
    # -------------------------------------------------------------
    with tab_metrics:
        st.markdown("### Operational Telemetry & Model Performance")
        st.caption("Live aggregate metrics across ingested email traffic, automated triage distribution, and analyst workload.")

        with get_db_context() as conn:
            summary = MessageRepository.get_metrics_summary(conn)

        total_msgs = summary.get("total_messages", 0)
        auto_dec = summary.get("automated_decisions", {})
        status_dist = summary.get("current_status_distribution", {})
        total_overrides = summary.get("total_overrides", 0)

        # High-impact KPI grid
        col_m1, col_m2, col_m3, col_m4 = st.columns(4)
        with col_m1:
            st.markdown(render_metric_card("Total Ingested", total_msgs, "Email payloads evaluated", "#6366F1"), unsafe_allow_html=True)
        with col_m2:
            auto_quar = auto_dec.get("QUARANTINE", 0)
            pct_q = f"{(auto_quar / total_msgs * 100):.1f}%" if total_msgs > 0 else "0%"
            st.markdown(render_metric_card("Auto-Quarantined", auto_quar, f"{pct_q} traffic blocked (T >= 0.85)", "#EF4444"), unsafe_allow_html=True)
        with col_m3:
            auto_allow = auto_dec.get("ALLOW", 0)
            pct_a = f"{(auto_allow / total_msgs * 100):.1f}%" if total_msgs > 0 else "0%"
            st.markdown(render_metric_card("Auto-Allowed", auto_allow, f"{pct_a} traffic cleared (T < 0.05)", "#10B981"), unsafe_allow_html=True)
        with col_m4:
            q_depth = summary.get("human_review_queue_depth", 0)
            st.markdown(render_metric_card("Review Queue Depth", q_depth, f"Total overrides: {total_overrides}", "#F59E0B"), unsafe_allow_html=True)

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.markdown("#### Automated Triage Policy Split")
            triage_data = {
                "Auto-Allow (T < 0.05)": auto_allow,
                "Human Review (0.05 ≤ T < 0.85)": auto_dec.get("HUMAN_REVIEW", 0),
                "Auto-Quarantine (T ≥ 0.85)": auto_quar
            }
            st.bar_chart(triage_data)

        with col_chart2:
            st.markdown("#### Current State Distribution")
            st.bar_chart(status_dist)

    # -------------------------------------------------------------
    # TAB 5: Live Ingestion Sandbox
    # -------------------------------------------------------------
    with tab_sandbox:
        st.markdown("### Live Email Ingestion & Multi-Agent Test Bench")
        st.caption("Submit any ad-hoc synthetic email or select a preset to watch the 6 deterministic agents parse, score, triage, persist, and audit the payload in real-time.")

        preset_options = {
            "Custom (Enter below)": {
                "subject": "",
                "sender": "",
                "body": ""
            },
            "Credential Harvesting Threat (High Risk)": {
                "subject": "CRITICAL: Suspicious account activity detected",
                "sender": "security-alert@paypal-update.pages.dev",
                "body": "Your payment authorization has failed. Please verify your identity immediately: http://paypal-verification-update.secure-login-account.pages.dev/banking/signin.php?token=9281"
            },
            "Ambiguous Cloud Document Sharing (Review Band)": {
                "subject": "Shared Document: Project Q3 Roadmap Review",
                "sender": "share-notifications@docs-cloud.co",
                "body": "Alice has shared a spreadsheet with you. Review the draft at https://portal.billing-docs.co/invoices/client/9821/review"
            },
            "Legitimate Corporate Meeting Memo (Low Risk)": {
                "subject": "Architecture Sync & Weekly Update",
                "sender": "lead-architect@internal-tools.org",
                "body": "Team, please review the system design notes on the company wiki before our call: https://wikipedia.org/wiki/Phishing"
            }
        }

        selected_preset = st.selectbox("Select Test Scenario Preset", list(preset_options.keys()))
        preset_val = preset_options[selected_preset]

        col_sb1, col_sb2 = st.columns(2)
        with col_sb1:
            sb_subject = st.text_input("Subject Line", value=preset_val["subject"], key="sb_subj")
            sb_sender = st.text_input("Sender Address", value=preset_val["sender"], key="sb_sender")
        with col_sb2:
            sb_body = st.text_area("Email Body (Contains URLs)", value=preset_val["body"], height=105, key="sb_body")

        if st.button("🚀 Ingest & Process Email Through Pipeline", use_container_width=True, type="primary"):
            if not sb_subject or not sb_sender or not sb_body:
                st.error("Please fill in Subject, Sender, and Body.")
            else:
                with st.spinner("Processing through 6-agent pipeline..."):
                    orchestrator = PhishingPipelineOrchestrator()
                    email_payload = EmailPayload(
                        subject=sb_subject,
                        sender=sb_sender,
                        body=sb_body
                    )
                    with get_db_context() as conn:
                        result = orchestrator.process_email(email_payload, db_conn=conn)

                st.success(f"Processing complete in {result.execution_time_ms} ms! Assigned Message ID: `{result.message_id}`")
                
                # Show pipeline step-by-step trace
                col_res1, col_res2 = st.columns([2, 1])
                with col_res1:
                    st.markdown("#### Triage Decision Dossier")
                    st.markdown(
                        f"""
                        <div class="soc-card">
                            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                                <span style="font-size: 0.85rem; color: #94A3B8;">Triage Decision:</span>
                                {render_status_badge(result.decision)}
                            </div>
                            <div style="margin: 8px 0;">
                                {render_score_bar(result.max_score)}
                            </div>
                            <div style="font-size: 0.82rem; color: #CBD5E1; margin-top: 8px; border-top: 1px solid rgba(255, 255, 255, 0.06); padding-top: 6px;">
                                <strong>Triage Rationale:</strong> {result.triage_output.rationale}
                            </div>
                            <div style="font-size: 0.8rem; color: #64748B; margin-top: 4px;">
                                Action Taken: {result.action_output.action_taken}
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

                with col_res2:
                    st.markdown("#### Agent Execution Sequence")
                    st.markdown(
                        f"""
                        <div style="background: #0B111D; border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 8px; padding: 12px; font-size: 0.78rem; font-family: 'JetBrains Mono', monospace;">
                            <div>1. <strong>ParserAgent</strong>: {result.parser_output.url_count} URLs found</div>
                            <div style="margin-top: 4px;">2. <strong>FeatureAgent</strong>: Extracted 26 features</div>
                            <div style="margin-top: 4px;">3. <strong>ClassifierAgent</strong>: Max score {result.max_score:.4f}</div>
                            <div style="margin-top: 4px;">4. <strong>TriageAgent</strong>: -> {result.decision}</div>
                            <div style="margin-top: 4px;">5. <strong>ActionAgent</strong>: Persisted = {result.action_output.persisted}</div>
                            <div style="margin-top: 4px;">6. <strong>AuditAgent</strong>: Logged</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )


if __name__ == "__main__":
    main()
