"""SQLite index of recordings + transcripts for fast search.

Lightweight: one row per finalized recording. Full-text search over transcripts
via SQLite FTS5 when available, falling back to LIKE.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import List, Optional


class RecordingIndex:
    def __init__(self, recordings_dir: str):
        self.db_path = Path(recordings_dir) / "index.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS recordings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    path TEXT UNIQUE NOT NULL,
                    started_at TEXT,
                    duration_s REAL,
                    transcript TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            try:
                conn.execute(
                    "CREATE VIRTUAL TABLE IF NOT EXISTS recordings_fts "
                    "USING fts5(transcript, content='recordings', content_rowid='id')"
                )
                self._has_fts = True
            except sqlite3.OperationalError:
                self._has_fts = False

    def add(
        self,
        audio_path: Path,
        started_at: Optional[datetime],
        duration_s: float,
        transcript: str = "",
    ) -> None:
        ts = started_at.isoformat() if isinstance(started_at, datetime) else (started_at or "")
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT OR REPLACE INTO recordings (path, started_at, duration_s, transcript) "
                "VALUES (?, ?, ?, ?)",
                (str(audio_path), ts, duration_s, transcript),
            )
            if getattr(self, "_has_fts", False):
                conn.execute(
                    "INSERT INTO recordings_fts (rowid, transcript) VALUES (?, ?)",
                    (cur.lastrowid, transcript),
                )

    def search(self, query: str, limit: int = 50) -> List[dict]:
        with self._connect() as conn:
            if getattr(self, "_has_fts", False):
                try:
                    rows = conn.execute(
                        "SELECT r.* FROM recordings_fts f JOIN recordings r ON r.id = f.rowid "
                        "WHERE recordings_fts MATCH ? ORDER BY r.started_at DESC LIMIT ?",
                        (query, limit),
                    ).fetchall()
                    return [dict(r) for r in rows]
                except sqlite3.OperationalError:
                    pass
            rows = conn.execute(
                "SELECT * FROM recordings WHERE transcript LIKE ? "
                "ORDER BY started_at DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            return [dict(r) for r in rows]

    def all(self, limit: int = 100) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM recordings ORDER BY started_at DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(r) for r in rows]
