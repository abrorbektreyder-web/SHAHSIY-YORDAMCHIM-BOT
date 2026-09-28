"""Supabase (PostgreSQL) bilan ishlash. Boshqa modullar SQL yozmaydi."""
from __future__ import annotations

from datetime import datetime

import asyncpg

from bot.models import Task

_pool: asyncpg.Pool | None = None
_schema = "vazifa"


async def init_db(database_url: str, schema: str = "vazifa") -> None:
    global _pool, _schema
    _schema = schema
    # Supabase pooler (pgbouncer) prepared statement keshini qo'llamaydi.
    _pool = await asyncpg.create_pool(
        database_url, min_size=1, max_size=3, statement_cache_size=0
    )
    async with _pool.acquire() as conn:
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {_schema}")
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_schema}.tasks (
                id          BIGSERIAL PRIMARY KEY,
                title       TEXT        NOT NULL,
                due_at      TIMESTAMPTZ,
                done        BOOLEAN     NOT NULL DEFAULT FALSE,
                done_at     TIMESTAMPTZ,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


def _pool_or_fail() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("init_db() chaqirilmagan")
    return _pool


async def add_task(title: str, due_at: datetime | None) -> int:
    return await _pool_or_fail().fetchval(
        f"INSERT INTO {_schema}.tasks (title, due_at) VALUES ($1, $2) RETURNING id",
        title,
        due_at,
    )


async def list_open_tasks() -> list[Task]:
    rows = await _pool_or_fail().fetch(
        f"SELECT id, title, due_at FROM {_schema}.tasks "
        f"WHERE NOT done ORDER BY due_at NULLS LAST, id"
    )
    return [Task(row["id"], row["title"], row["due_at"]) for row in rows]


async def list_done_tasks(since: datetime) -> list[Task]:
    rows = await _pool_or_fail().fetch(
        f"SELECT id, title, due_at, done_at FROM {_schema}.tasks "
        f"WHERE done AND done_at >= $1 ORDER BY done_at DESC, id DESC",
        since,
    )
    return [Task(row["id"], row["title"], row["due_at"], row["done_at"]) for row in rows]


async def mark_done(task_id: int) -> bool:
    result = await _pool_or_fail().execute(
        f"UPDATE {_schema}.tasks SET done = TRUE, done_at = now() WHERE id = $1 AND NOT done",
        task_id,
    )
    return result == "UPDATE 1"


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
