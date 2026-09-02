"""Durable job store for review runs, backed by SQLite (stdlib).

A review job's lifecycle is `pending` -> `running` -> `completed` | `failed`.
The store is the durable record the async submit endpoints and the polling GET
read from. SQLite keeps the MVP single-process and dependency-free; each
operation opens its own connection so `asyncio.to_thread` stays safe.

# ponytail: sqlite is single-node. Swap in the docker-compose Postgres when this
# needs multi-worker job sharing or pgvector similarity.
"""

from __future__ import annotations

import asyncio
import sqlite3
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    playbook_id TEXT NOT NULL,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS token_budget (
    day TEXT PRIMARY KEY,
    tokens INTEGER NOT NULL DEFAULT 0
);
"""

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"


class ReviewStore:
    def __init__(self, path: str) -> None:
        self._path = str(path)
        with sqlite3.connect(self._path) as conn:
            conn.executescript(SCHEMA)

    def _execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with sqlite3.connect(self._path) as conn:
            conn.execute(sql, params)

    def _fetch_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        with sqlite3.connect(self._path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(sql, params).fetchone()
        return dict(row) if row else None

    async def create(self, job_id: str, playbook_id: str) -> None:
        await asyncio.to_thread(
            self._execute,
            "INSERT INTO reviews (id, status, playbook_id) VALUES (?, ?, ?)",
            (job_id, STATUS_PENDING, playbook_id),
        )

    async def transition(
        self,
        job_id: str,
        status: str,
        *,
        result: str | None = None,
        error: str | None = None,
    ) -> None:
        sets = ["status = ?", "updated_at = datetime('now')"]
        params: list[Any] = [status]
        for column, value in (("result", result), ("error", error)):
            if value is not None:
                sets.append(f"{column} = ?")
                params.append(value)
        params.append(job_id)
        await asyncio.to_thread(
            self._execute,
            f"UPDATE reviews SET {', '.join(sets)} WHERE id = ?",
            tuple(params),
        )

    async def get(self, job_id: str) -> dict[str, Any] | None:
        return await asyncio.to_thread(
            self._fetch_one, "SELECT * FROM reviews WHERE id = ?", (job_id,)
        )

    async def add_token_spend(self, day: str, tokens: int) -> None:
        """Accrue tokens spent on a UTC calendar day (idempotent source of truth)."""
        await asyncio.to_thread(
            self._execute,
            "INSERT INTO token_budget (day, tokens) VALUES (?, ?) "
            "ON CONFLICT(day) DO UPDATE SET tokens = tokens + excluded.tokens",
            (day, tokens),
        )

    async def tokens_spent(self, day: str) -> int:
        row = await asyncio.to_thread(
            self._fetch_one,
            "SELECT tokens FROM token_budget WHERE day = ?",
            (day,),
        )
        return int(row["tokens"]) if row else 0
