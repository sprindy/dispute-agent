"""
SQLite database for user management, dispute history, and bookmarks.

Tables:
- users: id, username, email, password_hash, role, created_at
- disputes: id, user_id, dispute_id, category, filed_by, description, result_json, created_at
- bookmarks: id, user_id, dispute_id, created_at
"""
import sqlite3
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "ryde_dispute.db")


def _get_conn() -> sqlite3.Connection:
    """Get a SQLite connection with row factory."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create all tables if they don't exist."""
    conn = _get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            created_at TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS disputes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dispute_id TEXT NOT NULL,
            category TEXT NOT NULL,
            filed_by TEXT NOT NULL,
            description TEXT,
            result_json TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            dispute_id TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(user_id, dispute_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


# --- User operations ---

def create_user(username: str, email: str, password_hash: str, role: str = "user") -> dict:
    """Insert a new user. Raises ValueError on duplicate username/email."""
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)",
            (username, email, password_hash, role, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        user_id = cursor.lastrowid
        return {"id": user_id, "username": username, "email": email, "role": role}
    except sqlite3.IntegrityError as e:
        if "username" in str(e):
            raise ValueError("Username already exists")
        elif "email" in str(e):
            raise ValueError("Email already exists")
        raise
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict]:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[dict]:
    conn = _get_conn()
    try:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def list_all_users() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute("SELECT id, username, email, role, created_at FROM users ORDER BY id").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def update_user_password(user_id: int, password_hash: str):
    conn = _get_conn()
    try:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
        conn.commit()
    finally:
        conn.close()


def delete_user(user_id: int):
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    finally:
        conn.close()


# --- Dispute operations ---

def save_dispute(user_id: int, dispute_id: str, category: str, filed_by: str, description: str, result_json: str) -> int:
    conn = _get_conn()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO disputes (user_id, dispute_id, category, filed_by, description, result_json, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, dispute_id, category, filed_by, description, result_json,
             datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_user_disputes(user_id: int) -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            "SELECT * FROM disputes WHERE user_id = ? ORDER BY created_at DESC", (user_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_all_disputes() -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT d.*, u.username FROM disputes d
               JOIN users u ON d.user_id = u.id
               ORDER BY d.created_at DESC"""
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def delete_dispute(dispute_pk: int, user_id: int):
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM disputes WHERE id = ? AND user_id = ?", (dispute_pk, user_id))
        conn.commit()
    finally:
        conn.close()


# --- Bookmark operations ---

def add_bookmark(user_id: int, dispute_id: str) -> bool:
    conn = _get_conn()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO bookmarks (user_id, dispute_id, created_at) VALUES (?, ?, ?)",
            (user_id, dispute_id, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def remove_bookmark(user_id: int, dispute_id: str) -> bool:
    conn = _get_conn()
    try:
        conn.execute("DELETE FROM bookmarks WHERE user_id = ? AND dispute_id = ?", (user_id, dispute_id))
        conn.commit()
        return True
    finally:
        conn.close()


def get_user_bookmarks(user_id: int) -> list[dict]:
    conn = _get_conn()
    try:
        rows = conn.execute(
            """SELECT b.*, d.category, d.description, d.result_json
               FROM bookmarks b
               LEFT JOIN disputes d ON b.dispute_id = d.dispute_id AND d.user_id = b.user_id
               WHERE b.user_id = ?
               ORDER BY b.created_at DESC""",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def is_bookmarked(user_id: int, dispute_id: str) -> bool:
    conn = _get_conn()
    try:
        row = conn.execute(
            "SELECT 1 FROM bookmarks WHERE user_id = ? AND dispute_id = ?",
            (user_id, dispute_id),
        ).fetchone()
        return row is not None
    finally:
        conn.close()
