import sqlite3
from datetime import datetime
from typing import Optional, List, Dict

from config import DB_PATH


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Job Descriptions
    cur.execute("""
        CREATE TABLE IF NOT EXISTS jds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jd_hash TEXT UNIQUE,
            raw_text TEXT,
            structured_text TEXT,
            created_at TEXT
        )
    """)

    # Resumes
    cur.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            resume_hash TEXT UNIQUE,
            filename TEXT,
            raw_text TEXT,
            structured_text TEXT,
            created_at TEXT
        )
    """)

    # Scores (LLM / TF-IDF / future)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            jd_hash TEXT,
            resume_hash TEXT,
            score_type TEXT,     -- 'llm' | 'tfidf'
            score_value REAL,
            remarks TEXT,
            model_name TEXT,
            created_at TEXT,
            UNIQUE(jd_hash, resume_hash, score_type)
        )
    """)

    conn.commit()
    conn.close()


def save_jd(jd_hash: str, raw_text: str, structured_text: str):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO jds
        (jd_hash, raw_text, structured_text, created_at)
        VALUES (?, ?, ?, ?)
    """, (
        jd_hash,
        raw_text,
        structured_text,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


def get_jd_by_hash(jd_hash: str) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM jds WHERE jd_hash = ?", (jd_hash,))
    row = cur.fetchone()

    conn.close()
    return dict(row) if row else None


def save_resume(
    resume_hash: str,
    filename: str,
    raw_text: str,
    structured_text: str
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR IGNORE INTO resumes
        (resume_hash, filename, raw_text, structured_text, created_at)
        VALUES (?, ?, ?, ?, ?)
    """, (
        resume_hash,
        filename,
        raw_text,
        structured_text,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


def get_resume_by_hash(resume_hash: str) -> Optional[Dict]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM resumes WHERE resume_hash = ?", (resume_hash,))
    row = cur.fetchone()

    conn.close()
    return dict(row) if row else None


def get_all_resumes() -> List[Dict]:
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM resumes")
    rows = cur.fetchall()

    conn.close()
    return [dict(r) for r in rows]


def save_score(
    jd_hash: str,
    resume_hash: str,
    score_type: str,
    score_value: float,
    remarks: str,
    model_name: Optional[str] = None
):
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        INSERT OR REPLACE INTO scores
        (jd_hash, resume_hash, score_type, score_value, remarks, model_name, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        jd_hash,
        resume_hash,
        score_type,
        score_value,
        remarks,
        model_name,
        datetime.utcnow().isoformat()
    ))

    conn.commit()
    conn.close()


def get_score_by_jd_and_resume(jd_hash: str, resume_hash: str, score_type: str) -> Optional[Dict]:
    """
    Retrieves existing score for a jd-resume pair.
    Returns the cached score if it exists, None otherwise.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT * FROM scores 
        WHERE jd_hash = ? AND resume_hash = ? AND score_type = ?
    """, (jd_hash, resume_hash, score_type))
    
    row = cur.fetchone()
    conn.close()
    
    return dict(row) if row else None


def get_combined_scores_for_jd(jd_hash: str) -> List[Dict]:
    """
    Returns one row per resume with LLM score and TF-IDF similarity.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            r.filename,

            MAX(CASE WHEN s.score_type = 'llm'
                     THEN s.score_value END) AS llm_score,

            MAX(CASE WHEN s.score_type = 'tfidf'
                     THEN s.score_value END) AS tfidf_similarity,

            MAX(CASE WHEN s.score_type = 'llm'
                     THEN s.remarks END) AS llm_remarks

        FROM resumes r
        LEFT JOIN scores s
          ON r.resume_hash = s.resume_hash
         AND s.jd_hash = ?

        GROUP BY r.resume_hash
        ORDER BY llm_score DESC
    """, (jd_hash,))

    rows = cur.fetchall()
    conn.close()

    return [dict(r) for r in rows]
