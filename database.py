"""
Database module for Document Intelligence Platform (Demo).

SQLite storage for:
- documents: uploaded document metadata + processing status
- extractions: extracted payloads (fields + platform envelope)

Design goals:
- Simple local persistence (SQLite file)
- Auditability: ability to retrieve past results
- Reliability under Streamlit reruns (WAL + busy_timeout)
"""

import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DB_NAME = "verification.db"


def _get_conn() -> sqlite3.Connection:
    """
    Centralized connection creator with settings that reduce 'database is locked' errors.
    """
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")         # better concurrent reads/writes
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.execute("PRAGMA busy_timeout = 5000;")        # wait up to 5s if locked
    return conn


def init_db() -> None:
    """
    Initialize SQLite database with required tables.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS extractions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER NOT NULL,
                extracted_data TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            )
        """)

        # Helpful indexes for audit queries
        cur.execute("CREATE INDEX IF NOT EXISTS idx_documents_upload_time ON documents(upload_time);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_extractions_document_id ON extractions(document_id);")

        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.exception("Error initializing database: %s", e)
        raise


def insert_document(filename: str, status: str = "UPLOADED") -> int:
    """
    Insert a new document record.
    Returns document_id.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO documents (filename, status) VALUES (?, ?)",
            (filename, status),
        )
        document_id = cur.lastrowid

        conn.commit()
        conn.close()
        logger.info("Document inserted with ID: %s", document_id)
        return int(document_id)
    except Exception as e:
        logger.exception("Error inserting document: %s", e)
        raise


def update_document_status(document_id: int, status: str) -> None:
    """
    Update status for a document.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute(
            "UPDATE documents SET status = ? WHERE id = ?",
            (status, document_id),
        )

        conn.commit()
        conn.close()
        logger.info("Document %s status updated to %s", document_id, status)
    except Exception as e:
        logger.exception("Error updating document status: %s", e)
        raise


def save_extraction(document_id: int, data_dict: Dict[str, Any]) -> None:
    """
    Save extracted payload as JSON string for a document.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        extracted_data = json.dumps(data_dict, ensure_ascii=False)

        cur.execute(
            "INSERT INTO extractions (document_id, extracted_data) VALUES (?, ?)",
            (document_id, extracted_data),
        )

        conn.commit()
        conn.close()
        logger.info("Extraction saved for document %s", document_id)
    except Exception as e:
        logger.exception("Error saving extraction: %s", e)
        raise


# ----------------------------
# Audit / retrieval helpers (platform-ready)
# ----------------------------

def get_document(document_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch a single document record.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute(
            "SELECT id, filename, upload_time, status FROM documents WHERE id = ?",
            (document_id,),
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        return {
            "id": row[0],
            "filename": row[1],
            "upload_time": row[2],
            "status": row[3],
        }
    except Exception as e:
        logger.exception("Error fetching document: %s", e)
        raise


def get_latest_extraction(document_id: int) -> Optional[Dict[str, Any]]:
    """
    Fetch the latest extraction JSON for a document.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT extracted_data, created_at
            FROM extractions
            WHERE document_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (document_id,),
        )
        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        extracted_json = row[0]
        created_at = row[1]
        payload = json.loads(extracted_json)
        return {"created_at": created_at, "payload": payload}
    except Exception as e:
        logger.exception("Error fetching extraction: %s", e)
        raise


def list_recent_documents(limit: int = 20) -> List[Dict[str, Any]]:
    """
    List recent documents for audit/demo views.
    """
    try:
        conn = _get_conn()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT id, filename, upload_time, status
            FROM documents
            ORDER BY upload_time DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = cur.fetchall()
        conn.close()

        out: List[Dict[str, Any]] = []
        for r in rows:
            out.append(
                {"id": r[0], "filename": r[1], "upload_time": r[2], "status": r[3]}
            )
        return out
    except Exception as e:
        logger.exception("Error listing documents: %s", e)
        raise
