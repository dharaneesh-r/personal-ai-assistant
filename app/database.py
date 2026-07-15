import os
import json
import sqlite3
from typing import Any, Dict, List, Optional

DB_PATH = "data/history.db"

def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 1. Sessions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        mode TEXT NOT NULL,
        model TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    
    # 2. Messages table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        mode TEXT NOT NULL,
        timestamp TEXT NOT NULL,
        sources TEXT,
        chunks_used INTEGER,
        rewritten_query TEXT,
        tool_calls TEXT,
        iterations INTEGER,
        model TEXT,
        FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
    )
    """)
    
    # 3. Evaluations table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS evaluations (
        id TEXT PRIMARY KEY,
        question TEXT NOT NULL,
        answer TEXT NOT NULL,
        context TEXT NOT NULL,
        overall REAL NOT NULL,
        faithfulness_score INTEGER NOT NULL,
        faithfulness_reason TEXT,
        relevance_score INTEGER NOT NULL,
        relevance_reason TEXT,
        groundedness_score INTEGER NOT NULL,
        groundedness_reason TEXT,
        model TEXT NOT NULL,
        timestamp TEXT NOT NULL
    )
    """)
    
    conn.commit()
    conn.close()

# --- Sessions CRUD ---

def save_session(session_id: str, title: str, mode: str, model: str, created_at: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO sessions (id, title, mode, model, created_at) VALUES (?, ?, ?, ?, ?)",
        (session_id, title, mode, model, created_at)
    )
    conn.commit()
    conn.close()

def get_all_sessions() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_session(session_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_session(session_id: str) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    # cascade delete isn't enabled by default in sqlite without PRAGMA foreign_keys = ON;
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
    conn.commit()
    conn.close()

# --- Messages CRUD ---

def save_message(
    msg_id: str,
    session_id: str,
    role: str,
    content: str,
    mode: str,
    timestamp: str,
    sources: List[str] = None,
    chunks_used: int = None,
    rewritten_query: str = None,
    tool_calls: List[dict] = None,
    iterations: int = None,
    model: str = None
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    
    # Serialize complex objects to JSON strings
    sources_str = json.dumps(sources) if sources is not None else None
    tool_calls_str = json.dumps(tool_calls) if tool_calls is not None else None
    
    cursor.execute(
        """
        INSERT OR REPLACE INTO messages 
        (id, session_id, role, content, mode, timestamp, sources, chunks_used, rewritten_query, tool_calls, iterations, model)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            msg_id, session_id, role, content, mode, timestamp,
            sources_str, chunks_used, rewritten_query, tool_calls_str, iterations, model
        )
    )
    conn.commit()
    conn.close()

def get_session_messages(session_id: str) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
    rows = cursor.fetchall()
    conn.close()
    
    results = []
    for row in rows:
        d = dict(row)
        # Deserialize JSON fields
        if d["sources"]:
            try:
                d["sources"] = json.loads(d["sources"])
            except:
                d["sources"] = []
        else:
            d["sources"] = []
            
        if d["tool_calls"]:
            try:
                d["tool_calls"] = json.loads(d["tool_calls"])
            except:
                d["tool_calls"] = []
        else:
            d["tool_calls"] = []
            
        results.append(d)
        
    return results

# --- Evaluations CRUD ---

def save_evaluation(
    eval_id: str,
    question: str,
    answer: str,
    context: str,
    overall: float,
    faithfulness_score: int,
    faithfulness_reason: str,
    relevance_score: int,
    relevance_reason: str,
    groundedness_score: int,
    groundedness_reason: str,
    model: str,
    timestamp: str
) -> None:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO evaluations 
        (id, question, answer, context, overall, faithfulness_score, faithfulness_reason, relevance_score, relevance_reason, groundedness_score, groundedness_reason, model, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            eval_id, question, answer, context, overall,
            faithfulness_score, faithfulness_reason, relevance_score, relevance_reason,
            groundedness_score, groundedness_reason, model, timestamp
        )
    )
    conn.commit()
    conn.close()

def get_all_evaluations() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evaluations ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]
