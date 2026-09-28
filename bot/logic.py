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
    tasks: list[Task] = field(default_factory=list)


async def handle_text(text: str, ai, store, now: datetime) -> Reply:
    intent = await ai.understand(text, now)
    if intent.kind == "add_task":
        await store.add_task(intent.title, intent.due_at)
        return Reply("voice", views.task_added_text(intent.title, intent.due_at))
    if intent.kind == "list_tasks":
        return Reply("list", tasks=await store.list_open_tasks())
    if intent.kind == "speak_report":
        tasks = await store.list_open_tasks()
        return Reply("list_voice", views.format_task_list_for_speech(tasks), tasks)
    if intent.kind == "chat":
        return Reply("voice", intent.reply)
    return Reply("text", uz.NOT_UNDERSTOOD)
