"""
src/storage/db.py
SQLite database connection and schema management for PhishTrap.
"""

import os
import sqlite3
from typing import Generator
from contextlib import contextmanager

DEFAULT_DB_PATH = os.path.join(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")),
    "data",
    "phishing_pipeline.db"
)


def get_db_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Creates and returns a connection to the SQLite database.
    Enables foreign keys and sets Row factory for dict-like access.
    """
    if db_path is None:
        db_path = os.getenv("PHISHTRAP_DB_PATH", DEFAULT_DB_PATH)
    
    # Ensure directory exists if path is not in-memory
    if db_path != ":memory:":
        os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
        
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def get_db_context(db_path: str = None) -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager providing safe transaction handling.
    Commits on success, rolls back on exception, and automatically closes.
    """
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: str = None) -> None:
    """
    Initializes the database schema if tables do not exist.
    """
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                subject TEXT NOT NULL,
                sender TEXT NOT NULL,
                body TEXT NOT NULL,
                received_at TEXT NOT NULL,
                max_score REAL NOT NULL,
                automated_decision TEXT NOT NULL,
                current_status TEXT NOT NULL,
                decided_at TEXT NOT NULL,
                decided_by TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_status ON messages(current_status);
            CREATE INDEX IF NOT EXISTS idx_messages_received ON messages(received_at);

            CREATE TABLE IF NOT EXISTS extracted_urls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                raw_url TEXT NOT NULL,
                defanged_url TEXT NOT NULL,
                normalized_url TEXT NOT NULL,
                registered_domain TEXT NOT NULL,
                score REAL NOT NULL,
                top_features_json TEXT NOT NULL,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_urls_message_id ON extracted_urls(message_id);

            CREATE TABLE IF NOT EXISTS overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message_id TEXT NOT NULL,
                reviewer_id TEXT NOT NULL,
                previous_status TEXT NOT NULL,
                new_status TEXT NOT NULL,
                reason TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_overrides_message_id ON overrides(message_id);
            CREATE INDEX IF NOT EXISTS idx_overrides_timestamp ON overrides(timestamp);
            """)
    finally:
        conn.close()
