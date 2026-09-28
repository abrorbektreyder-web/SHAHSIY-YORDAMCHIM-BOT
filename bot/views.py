"""Vazifalarni foydalanuvchiga ko'rsatiladigan matnga aylantirish."""
from __future__ import annotations

from datetime import datetime, timedelta
from html import escape
from urllib.parse import urlparse

from bot.models import Task
from bot.scheduler import TASHKENT
from bot.search import SearchResult
from content import uz

DONE_WINDOW = timedelta(days=7)
SEARCH_ICONS = {"flight": "✈️", "hotel": "🏨", "restaurant": "🍽", "youtube": "▶️", "general": "🔎"}
PER_PAGE = 3


def format_due(due_at: datetime | None) -> str:
    if due_at is None:
        return uz.NO_DUE
    return due_at.astimezone(TASHKENT).strftime("%d.%m.%Y %H:%M")


def _format_done(done_at: datetime | None) -> str:
    if done_at is None:
        return uz.DONE_AT.format(date="—")
    return uz.DONE_AT.format(date=done_at.astimezone(TASHKENT).strftime("%d.%m"))


def split_open(tasks: list[Task], now: datetime) -> tuple[list[Task], list[Task], list[Task]]:
    """Bajarilmaganlarni muddati o'tgan / bugun / rejadagi guruhlarga ajratadi."""
    local_now = now.astimezone(TASHKENT)
    overdue, today, upcoming = [], [], []
    for task in tasks:
        if task.due_at is None:
            upcoming.append(task)
            continue
        due = task.due_at.astimezone(TASHKENT)
        if due < local_now:
            overdue.append(task)
        elif due.date() == local_now.date():
            today.append(task)
        else:
            upcoming.append(task)
    return overdue, today, upcoming


def order_open(tasks: list[Task], now: datetime) -> list[Task]:
    overdue, today, upcoming = split_open(tasks, now)
    return overdue + today + upcoming


def build_report(
    open_tasks: list[Task],
    done_tasks: list[Task],
    now: datetime,
    filter: str = "all",
    header: str | None = None,
) -> tuple[str, list[Task]]:
    """Matn va unda raqamlangan bajarilmagan vazifalar (tugmalar shu tartibda chiqadi)."""
    overdue, today, upcoming = split_open(open_tasks, now)
    groups = {
        "all": [(uz.SECTION_OVERDUE, overdue), (uz.SECTION_TODAY, today), (uz.SECTION_UPCOMING, upcoming)],
        "open": [(uz.SECTION_OVERDUE, overdue), (uz.SECTION_TODAY, today), (uz.SECTION_UPCOMING, upcoming)],
        "today": [(uz.SECTION_OVERDUE, overdue), (uz.SECTION_TODAY, today)],
        "overdue": [(uz.SECTION_OVERDUE, overdue)],
        "done": [],
    }[filter]
    done_shown = done_tasks if filter in ("all", "done") else []
    shown = [task for _, group in groups for task in group]
    if not shown and not done_shown:
        return (uz.NO_TASKS if filter == "all" else uz.NO_TASKS_IN_FILTER), []

    lines = [
        header
        or uz.REPORT_HEADER.format(
            total=len(open_tasks) + len(done_tasks), done=len(done_tasks), left=len(open_tasks)
        )
    ]
    n = 0
    for title, group in groups:
        if not group:
            continue
        lines += ["", title.format(count=len(group))]
        for task in group:
            n += 1
            # Bugungi bo'limda sana takrorlanmaydi — faqat soat.
            when = task.due_at.astimezone(TASHKENT).strftime("%H:%M") if group is today else format_due(task.due_at)
            lines.append(f"{n}. {escape(task.title, quote=False)} — <i>{when}</i>")
    if done_shown:
        lines += ["", uz.SECTION_DONE.format(count=len(done_shown))]
        for task in done_shown:
            lines.append(f"• {escape(task.title, quote=False)} — <i>{_format_done(task.done_at)}</i>")
    return "\n".join(lines), shown


def format_daily_report(open_tasks: list[Task], now: datetime) -> tuple[str, list[Task]]:
    if not open_tasks:
        return uz.DAILY_EMPTY, []
    return build_report(
        open_tasks, [], now, "open", header=uz.DAILY_HEADER.format(count=len(open_tasks))
    )


def format_task_list_for_speech(tasks: list[Task]) -> str:
    if not tasks:
        return uz.SPEECH_EMPTY
    parts = [uz.SPEECH_LIST_INTRO.format(count=len(tasks))]
    for n, task in enumerate(tasks, start=1):
        due = "" if task.due_at is None else f", muddati {format_due(task.due_at)}"
        parts.append(f"{n}. {task.title}{due}.")
    return " ".join(parts)


def _domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def format_search_pages(
    category: str, title: str, items: list[tuple[SearchResult, str]], per_page: int = PER_PAGE
) -> list[str]:
    header = f"{SEARCH_ICONS.get(category, '🔎')} <b>{escape(title, quote=False)}</b>"
    pages = []
    for start in range(0, len(items), per_page):
        lines = [header]
        for n, (result, note) in enumerate(items[start:start + per_page], start=start + 1):
            lines += ["", f"{n}. <b>{escape(result.title, quote=False)}</b>"]
            if note:
                lines.append(escape(note, quote=False))
            lines.append(f'🔗 <a href="{escape(result.url)}">{escape(_domain(result.url), quote=False)}</a>')
        pages.append("\n".join(lines))
    return pages


def heard_text(text: str) -> str:
    return uz.HEARD.format(text=escape(text, quote=False))


def task_added_text(title: str, due_at: datetime | None) -> str:
    if due_at is None:
        return uz.TASK_ADDED.format(title=title)
    return uz.TASK_ADDED_DUE.format(title=title, due=format_due(due_at))
