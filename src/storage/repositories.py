"""
src/storage/repositories.py
Deterministic SQLite repositories for message records, URLs, overrides, and metrics.
"""

import json
import sqlite3
from typing import Optional, List, Dict, Any


class MessageRepository:
    """Repository handling persistence and queries for emails and their extracted URLs."""

    @staticmethod
    def create_message(
        conn: sqlite3.Connection,
        message: Dict[str, Any],
        urls: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Inserts or replaces a message and its extracted URLs within the current transaction.
        Cleans existing URLs if replacing to prevent constraint violations.
        """
        conn.execute("DELETE FROM extracted_urls WHERE message_id = ?", (message["id"],))
        conn.execute(
            """
            INSERT OR REPLACE INTO messages (
                id, subject, sender, body, received_at, max_score,
                automated_decision, current_status, decided_at, decided_by
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message["id"],
                message["subject"],
                message["sender"],
                message["body"],
                message["received_at"],
                float(message["max_score"]),
                message["automated_decision"],
                message["current_status"],
                message["decided_at"],
                message["decided_by"]
            )
        )

        for u in urls:
            conn.execute(
                """
                INSERT INTO extracted_urls (
                    message_id, raw_url, defanged_url, normalized_url,
                    registered_domain, score, top_features_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message["id"],
                    u["raw_url"],
                    u["defanged_url"],
                    u["normalized_url"],
                    u["registered_domain"],
                    float(u["score"]),
                    json.dumps(u.get("top_features", []))
                )
            )

        return MessageRepository.get_message(conn, message["id"])

    @staticmethod
    def get_message(conn: sqlite3.Connection, message_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieves a single message by ID, including its URLs and override history.
        """
        cursor = conn.execute("SELECT * FROM messages WHERE id = ?", (message_id,))
        row = cursor.fetchone()
        if not row:
            return None

        msg_dict = dict(row)

        # Fetch URLs
        url_cursor = conn.execute(
            "SELECT * FROM extracted_urls WHERE message_id = ? ORDER BY score DESC",
            (message_id,)
        )
        urls = []
        for u in url_cursor.fetchall():
            u_dict = dict(u)
            try:
                u_dict["top_features"] = json.loads(u_dict["top_features_json"])
            except Exception:
                u_dict["top_features"] = []
            urls.append(u_dict)
        msg_dict["urls"] = urls

        # Fetch Overrides
        overrides_cursor = conn.execute(
            "SELECT * FROM overrides WHERE message_id = ? ORDER BY timestamp ASC",
            (message_id,)
        )
        msg_dict["overrides"] = [dict(o) for o in overrides_cursor.fetchall()]

        return msg_dict

    @staticmethod
    def list_queue(
        conn: sqlite3.Connection,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Retrieves messages currently queued for human review.
        """
        cursor = conn.execute(
            """
            SELECT * FROM messages
            WHERE current_status = 'HUMAN_REVIEW'
            ORDER BY max_score DESC, received_at DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        results = []
        for row in cursor.fetchall():
            msg_id = row["id"]
            msg = MessageRepository.get_message(conn, msg_id)
            if msg:
                results.append(msg)
        return results

    @staticmethod
    def update_status(
        conn: sqlite3.Connection,
        message_id: str,
        new_status: str
    ) -> bool:
        """
        Updates the current status of a message.
        """
        cursor = conn.execute(
            "UPDATE messages SET current_status = ? WHERE id = ?",
            (new_status, message_id)
        )
        return cursor.rowcount > 0

    @staticmethod
    def get_metrics_summary(conn: sqlite3.Connection) -> Dict[str, Any]:
        """
        Computes aggregate metrics across all messages and human overrides.
        """
        c = conn.cursor()
        
        # Message counts by current status
        c.execute("""
            SELECT current_status, COUNT(*) as cnt
            FROM messages
            GROUP BY current_status
        """)
        status_counts = {row["current_status"]: row["cnt"] for row in c.fetchall()}

        # Automated decisions
        c.execute("""
            SELECT automated_decision, COUNT(*) as cnt
            FROM messages
            GROUP BY automated_decision
        """)
        automated_counts = {row["automated_decision"]: row["cnt"] for row in c.fetchall()}

        # Total messages
        c.execute("SELECT COUNT(*) as total FROM messages")
        total_messages = c.fetchone()["total"]

        # Override breakdown
        c.execute("""
            SELECT new_status, COUNT(*) as cnt
            FROM overrides
            GROUP BY new_status
        """)
        override_breakdown = {row["new_status"]: row["cnt"] for row in c.fetchall()}

        # Total overrides
        c.execute("SELECT COUNT(*) as total_overrides FROM overrides")
        total_overrides = c.fetchone()["total_overrides"]

        return {
            "total_messages": total_messages,
            "automated_decisions": {
                "ALLOW": automated_counts.get("ALLOW", 0),
                "HUMAN_REVIEW": automated_counts.get("HUMAN_REVIEW", 0),
                "QUARANTINE": automated_counts.get("QUARANTINE", 0)
            },
            "current_status_distribution": status_counts,
            "human_review_queue_depth": status_counts.get("HUMAN_REVIEW", 0),
            "total_overrides": total_overrides,
            "override_breakdown": override_breakdown
        }


class AuditRepository:
    """Repository managing audit trail logs and reviewer overrides."""

    @staticmethod
    def record_override(
        conn: sqlite3.Connection,
        message_id: str,
        reviewer_id: str,
        previous_status: str,
        new_status: str,
        reason: str,
        timestamp: str
    ) -> Dict[str, Any]:
        """
        Records a human override event in the audit trail.
        """
        cursor = conn.execute(
            """
            INSERT INTO overrides (
                message_id, reviewer_id, previous_status, new_status, reason, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (message_id, reviewer_id, previous_status, new_status, reason, timestamp)
        )
        override_id = cursor.lastrowid
        return {
            "id": override_id,
            "message_id": message_id,
            "reviewer_id": reviewer_id,
            "previous_status": previous_status,
            "new_status": new_status,
            "reason": reason,
            "timestamp": timestamp
        }

    @staticmethod
    def list_audit_log(
        conn: sqlite3.Connection,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Returns recent audit entries ordered by timestamp descending.
        """
        cursor = conn.execute(
            """
            SELECT o.*, m.subject, m.sender, m.max_score
            FROM overrides o
            JOIN messages m ON o.message_id = m.id
            ORDER BY o.timestamp DESC, o.id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset)
        )
        return [dict(row) for row in cursor.fetchall()]

