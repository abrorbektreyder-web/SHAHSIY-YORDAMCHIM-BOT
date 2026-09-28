"""Vazifalarni foydalanuvchiga ko'rsatiladigan matnga aylantirish."""
from __future__ import annotations

from datetime import datetime
from html import escape

from bot.models import Task
from bot.scheduler import TASHKENT
from content import uz


def format_due(due_at: datetime | None) -> str:
    if due_at is None:
        return uz.NO_DUE
    return due_at.astimezone(TASHKENT).strftime("%d.%m.%Y %H:%M")


def format_task_list(tasks: list[Task], header: str = uz.LIST_HEADER) -> str:
    if not tasks:
        return uz.NO_TASKS
    lines = [header.format(count=len(tasks)), ""]
    for n, task in enumerate(tasks, start=1):
        lines.append(f"{n}. {escape(task.title)} — <i>{format_due(task.due_at)}</i>")
    return "\n".join(lines)


def format_daily_report(tasks: list[Task]) -> str:
    if not tasks:
        return uz.DAILY_EMPTY
    return format_task_list(tasks, uz.DAILY_HEADER)


def format_task_list_for_speech(tasks: list[Task]) -> str:
    if not tasks:
        return uz.SPEECH_EMPTY
    parts = [uz.SPEECH_LIST_INTRO.format(count=len(tasks))]
    for n, task in enumerate(tasks, start=1):
        due = "" if task.due_at is None else f", muddati {format_due(task.due_at)}"
        parts.append(f"{n}. {task.title}{due}.")
    return " ".join(parts)


def task_added_text(title: str, due_at: datetime | None) -> str:
    if due_at is None:
        return uz.TASK_ADDED.format(title=title)
    return uz.TASK_ADDED_DUE.format(title=title, due=format_due(due_at))
