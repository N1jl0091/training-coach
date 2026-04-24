import sqlite3
import json
import os
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "/data/coach.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS messages (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            role        TEXT NOT NULL,
            content     TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS activities (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            strava_id   TEXT UNIQUE NOT NULL,
            sport_type  TEXT NOT NULL,
            name        TEXT,
            data        TEXT NOT NULL,
            created_at  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS tokens (
            id            INTEGER PRIMARY KEY,
            access_token  TEXT,
            refresh_token TEXT,
            expires_at    INTEGER
        );
    """)
    conn.commit()
    conn.close()


# ── Messages ──────────────────────────────────────────────────────────────────

def save_message(role: str, content: str):
    conn = get_conn()
    conn.execute(
        "INSERT INTO messages (role, content) VALUES (?, ?)", (role, content)
    )
    conn.commit()
    conn.close()


def get_recent_messages(limit: int = 30) -> list[dict]:
    """Returns last N messages in chronological order."""
    conn = get_conn()
    rows = conn.execute(
        "SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


# ── Activities ────────────────────────────────────────────────────────────────

def save_activity(strava_id: str, sport_type: str, name: str, data: dict):
    conn = get_conn()
    conn.execute(
        """INSERT OR REPLACE INTO activities (strava_id, sport_type, name, data)
           VALUES (?, ?, ?, ?)""",
        (strava_id, sport_type.lower(), name, json.dumps(data)),
    )
    conn.commit()
    conn.close()


def get_activities(sport_type: Optional[str] = None, limit: int = 10) -> list[dict]:
    conn = get_conn()
    if sport_type:
        rows = conn.execute(
            """SELECT strava_id, sport_type, name, data, created_at
               FROM activities WHERE sport_type = ?
               ORDER BY created_at DESC LIMIT ?""",
            (sport_type.lower(), limit),
        ).fetchall()
    else:
        rows = conn.execute(
            """SELECT strava_id, sport_type, name, data, created_at
               FROM activities ORDER BY created_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    conn.close()
    return [
        {
            "strava_id": r["strava_id"],
            "sport_type": r["sport_type"],
            "name": r["name"],
            "data": json.loads(r["data"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


# ── Strava tokens ─────────────────────────────────────────────────────────────

def save_token(access_token: str, refresh_token: str, expires_at: int):
    conn = get_conn()
    conn.execute("DELETE FROM tokens")
    conn.execute(
        "INSERT INTO tokens (id, access_token, refresh_token, expires_at) VALUES (1, ?, ?, ?)",
        (access_token, refresh_token, expires_at),
    )
    conn.commit()
    conn.close()


def get_token() -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("SELECT * FROM tokens WHERE id = 1").fetchone()
    conn.close()
    if row:
        return {
            "access_token": row["access_token"],
            "refresh_token": row["refresh_token"],
            "expires_at": row["expires_at"],
        }
    return None
