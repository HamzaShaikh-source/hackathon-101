"""SQLite storage for jobs and candidates, keyed by DB_PATH."""

import json
import os
import sqlite3

DB_PATH = os.environ.get("DB_PATH", "app.db")


def _to_dict(obj):
    return obj.model_dump() if hasattr(obj, "model_dump") else dict(obj)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                description TEXT NOT NULL,
                requirements TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS candidates (
                id TEXT PRIMARY KEY,
                job_id TEXT NOT NULL,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                skills TEXT NOT NULL,
                experience_years REAL NOT NULL,
                raw_text TEXT NOT NULL,
                matches TEXT NOT NULL,
                score REAL NOT NULL
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _job_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "description": row["description"],
        "requirements": json.loads(row["requirements"]),
    }


def save_job(job) -> dict:
    data = _to_dict(job)
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO jobs (id, description, requirements) VALUES (?, ?, ?)",
            (data["id"], data["description"], json.dumps(data["requirements"])),
        )
        conn.commit()
    finally:
        conn.close()
    return data


def get_job(job_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    finally:
        conn.close()
    return _job_row_to_dict(row) if row else None


def list_jobs() -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM jobs").fetchall()
    finally:
        conn.close()
    return [_job_row_to_dict(row) for row in rows]


def _candidate_row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "job_id": row["job_id"],
        "name": row["name"],
        "email": row["email"],
        "skills": json.loads(row["skills"]),
        "experience_years": row["experience_years"],
        "raw_text": row["raw_text"],
        "matches": json.loads(row["matches"]),
        "score": row["score"],
    }


def save_candidate(candidate) -> dict:
    data = _to_dict(candidate)
    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT OR REPLACE INTO candidates
                (id, job_id, name, email, skills, experience_years, raw_text, matches, score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                data["id"],
                data["job_id"],
                data["name"],
                data["email"],
                json.dumps(data["skills"]),
                data["experience_years"],
                data["raw_text"],
                json.dumps(data["matches"]),
                data["score"],
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return data


def get_candidate(candidate_id: str) -> dict | None:
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM candidates WHERE id = ?", (candidate_id,)
        ).fetchone()
    finally:
        conn.close()
    return _candidate_row_to_dict(row) if row else None


def list_candidates(job_id: str) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM candidates WHERE job_id = ? ORDER BY score DESC", (job_id,)
        ).fetchall()
    finally:
        conn.close()
    return [_candidate_row_to_dict(row) for row in rows]
