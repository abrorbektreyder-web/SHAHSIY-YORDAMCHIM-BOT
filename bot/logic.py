"""Xabarga qanday javob berishni hal qiladi. Telegram'ga bog'liq emas."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from bot import views
from bot.models import Task
from content import uz


@dataclass(frozen=True)
class Reply:
    kind: str  # "voice" | "text" | "list" | "list_voice"
    text: str = ""
    tasks: list[Task] = field(default_factory=list)  # "list": tugmalar shu tartibda


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


async def handle_text(text: str, ai, store, now: datetime) -> Reply:
    intent = await ai.understand(text, now)
    if intent.kind == "add_task":
        await store.add_task(intent.title, intent.due_at)
        return Reply("voice", views.task_added_text(intent.title, intent.due_at))
    if intent.kind == "list_tasks":
        return await task_report(store, now, intent.filter)
    if intent.kind == "speak_report":
        tasks = views.order_open(await store.list_open_tasks(), now)
        return Reply("list_voice", views.format_task_list_for_speech(tasks), tasks)
    if intent.kind == "chat":
        return Reply("voice", intent.reply)
    return Reply("text", uz.NOT_UNDERSTOOD)
