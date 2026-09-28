import os
from datetime import datetime, timedelta

import asyncpg
import pytest

from bot import db
from bot.scheduler import TASHKENT

URL = os.getenv("TEST_DATABASE_URL")
SCHEMA = "vazifa_test"

pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL berilmagan")


async def _drop_schema():
    conn = await asyncpg.connect(URL, statement_cache_size=0)
    try:
        await conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    finally:
        await conn.close()


@pytest.fixture
async def fresh_db():
    await _drop_schema()
    await db.init_db(URL, SCHEMA)
    yield
    await db.close_pool()
    await _drop_schema()


async def test_add_and_list(fresh_db):
    due = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)
    task_id = await db.add_task("Shifokor", due)
    tasks = await db.list_open_tasks()
    assert [(t.id, t.title) for t in tasks] == [(task_id, "Shifokor")]
    assert tasks[0].due_at == due


async def test_mark_done_hides_task(fresh_db):
    task_id = await db.add_task("Non olish", None)
    assert await db.mark_done(task_id) is True
    assert await db.list_open_tasks() == []
    assert await db.mark_done(task_id) is False


async def test_order_dated_first_then_undated(fresh_db):
    undated = await db.add_task("Muddatsiz", None)
    late = await db.add_task("Kech", datetime(2026, 10, 1, 9, 0, tzinfo=TASHKENT))
    early = await db.add_task("Erta", datetime(2026, 9, 30, 9, 0, tzinfo=TASHKENT))
    assert [t.id for t in await db.list_open_tasks()] == [early, late, undated]


async def test_list_done_tasks_since_newest_first(fresh_db):
    older = await db.add_task("Birinchi bajarilgan", None)
    newer = await db.add_task("Ikkinchi bajarilgan", None)
    await db.add_task("Hali ochiq", None)
    await db.mark_done(older)
    await db.mark_done(newer)

    done = await db.list_done_tasks(datetime.now(TASHKENT) - timedelta(days=7))
    assert [t.id for t in done] == [newer, older]
    assert all(t.done_at is not None for t in done)
    assert await db.list_done_tasks(datetime.now(TASHKENT) + timedelta(days=1)) == []


async def test_init_db_is_idempotent(fresh_db):
    await db.add_task("Saqlanib qolsin", None)
    await db.close_pool()
    await db.init_db(URL, SCHEMA)
    assert [t.title for t in await db.list_open_tasks()] == ["Saqlanib qolsin"]


async def test_use_before_init_raises():
    await db.close_pool()
    with pytest.raises(RuntimeError):
        await db.list_open_tasks()
