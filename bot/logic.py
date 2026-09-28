"""Xabarga qanday javob berishni hal qiladi. Telegram'ga bog'liq emas."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from bot import views
from bot.ai_client import AIError, Intent
from bot.models import PLACE_CATEGORIES, Task
from bot.search import SearchError
from content import uz

log = logging.getLogger(__name__)
PLACE_WORD_LIMIT = 3


@dataclass(frozen=True)
class Reply:
    kind: str  # "voice" | "text" | "list" | "list_voice" | "search" | "ask_place"
    text: str = ""
    tasks: list[Task] = field(default_factory=list)  # "list": tugmalar shu tartibda
    more: str = ""  # "search": "Yana ko'rsat" sahifasi
    pending: Intent | None = None  # "ask_place": shahar kutayotgan qidiruv


def looks_like_place(text: str) -> bool:
    """Kutilayotgan qidiruvdan keyingi qisqa matn — shahar nomi deb qabul qilinadi."""
    return 0 < len(text.split()) <= PLACE_WORD_LIMIT


async def task_report(store, now: datetime, filter: str = "all") -> Reply:
    open_tasks = await store.list_open_tasks()
    done_tasks = (
        await store.list_done_tasks(now - views.DONE_WINDOW) if filter in ("all", "done") else []
    )
    text, shown = views.build_report(open_tasks, done_tasks, now, filter)
    return Reply("list", text, shown)


async def daily_report(store, now: datetime) -> Reply:
    text, shown = views.format_daily_report(await store.list_open_tasks(), now)
    return Reply("list", text, shown)


async def run_search(intent: Intent, place: str | None, ai, searcher) -> Reply:
    query, title = intent.query, intent.title or intent.query
    if place:
        if place.lower() not in query.lower():
            query = f"{query} {place}"
        if place.lower() not in title.lower():
            title = f"{title}, {place}"
    try:
        results = await searcher.search(query, intent.category)
    except SearchError as exc:
        log.warning("Qidiruv xatosi: %s", exc)
        return Reply("text", uz.SEARCH_ERROR)
    if not results:
        return Reply("text", uz.SEARCH_EMPTY)
    try:
        ranking = await ai.rank_results(query, results)
    except AIError as exc:
        log.warning("Saralash xatosi, qidiruv tartibi ishlatiladi: %s", exc)
        ranking = []
    if not ranking:
        ranking = [(i, "") for i in range(len(results))]
    pages = views.format_search_pages(intent.category, title, [(results[i], note) for i, note in ranking])
    return Reply("search", pages[0], more=pages[1] if len(pages) > 1 else "")


async def handle_text(text: str, ai, store, now: datetime, searcher=None, history=()) -> Reply:
    intent = await ai.understand(text, now, history)
    if intent.kind == "add_task":
        await store.add_task(intent.title, intent.due_at)
        return Reply("voice", views.task_added_text(intent.title, intent.due_at))
    if intent.kind == "list_tasks":
        return await task_report(store, now, intent.filter)
    if intent.kind == "speak_report":
        tasks = views.order_open(await store.list_open_tasks(), now)
        return Reply("list_voice", views.format_task_list_for_speech(tasks), tasks)
    if intent.kind == "search":
        if searcher is None:
            return Reply("text", uz.SEARCH_DISABLED)
        if intent.category in PLACE_CATEGORIES and not intent.place:
            return Reply("ask_place", uz.ASK_PLACE, pending=intent)
        return await run_search(intent, intent.place, ai, searcher)
    if intent.kind == "chat":
        return Reply("voice", intent.reply)
    return Reply("text", uz.NOT_UNDERSTOOD)
