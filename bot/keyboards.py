"""Inline tugmalar."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

from bot.models import Task
from content import uz

DONE_PREFIX = "done:"
SPEAK_LIST = "speak:list"
SEARCH_MORE = "search:more"
TITLE_LIMIT = 30


def _short(title: str) -> str:
    return title if len(title) <= TITLE_LIMIT else title[: TITLE_LIMIT - 1] + "…"


def task_list_keyboard(tasks: list[Task]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=uz.DONE_BUTTON.format(n=n, title=_short(task.title)),
                callback_data=f"{DONE_PREFIX}{task.id}",
            )
        ]
        for n, task in enumerate(tasks, start=1)
    ]
    rows.append([InlineKeyboardButton(text=uz.SPEAK_BUTTON, callback_data=SPEAK_LIST)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def parse_done(data: str) -> int | None:
    if not data.startswith(DONE_PREFIX):
        return None
    raw = data[len(DONE_PREFIX):]
    return int(raw) if raw.isdigit() else None


def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=uz.SEND_LOCATION_BUTTON, request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def more_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=uz.SEARCH_MORE_BUTTON, callback_data=SEARCH_MORE)]]
    )


def booking_keyboard(url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=uz.BOOKING_BUTTON, url=url)]])
