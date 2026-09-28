"""Telegram handlerlari: xabarni qabul qiladi, logic'ga beradi, javobni yuboradi."""
from __future__ import annotations

import logging
from collections import deque
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardMarkup,
    LinkPreviewOptions,
    Message,
    ReplyKeyboardRemove,
)

from bot import db, views
from bot.ai_client import AIClient, AIError, Intent
from bot.geo import Geocoder
from bot.keyboards import (
    DONE_PREFIX,
    SEARCH_MORE,
    SPEAK_LIST,
    booking_keyboard,
    location_keyboard,
    more_keyboard,
    parse_done,
    task_list_keyboard,
)
from bot.logic import Reply, handle_text, looks_like_place, run_search, task_report
from bot.models import Task
from bot.scheduler import now_tashkent
from content import uz

log = logging.getLogger(__name__)

# Bot bitta egaga xizmat qiladi va bitta jarayonda ishlaydi — holat xotirada yetarli.
_pending: dict[str, Intent] = {}  # "search" → shahar kutayotgan qidiruv
_more_pages: dict[int, str] = {}  # xabar id → "Yana ko'rsat" sahifasi
MORE_PAGES_LIMIT = 50
# "Eng arzonini top", "yana qidir" kabi gaplar oldingi so'rovga bog'lanishi uchun.
_history: deque[dict] = deque(maxlen=8)
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)


def list_markup(tasks: list[Task]) -> InlineKeyboardMarkup | None:
    return task_list_keyboard(tasks) if tasks else None


def build_router(owner_id: int) -> Router:
    router = Router()
    # Egasidan boshqa hech kimga javob berilmaydi.
    router.message.filter(F.from_user.id == owner_id)
    router.callback_query.filter(F.from_user.id == owner_id)

    @router.message(CommandStart())
    async def on_start(message: Message) -> None:
        await message.answer(uz.START)

    @router.message(F.voice)
    async def on_voice(message: Message, bot: Bot, ai: AIClient, searcher) -> None:
        try:
            audio = await bot.download(message.voice)
            text = await ai.transcribe(audio.read(), fmt="ogg")
        except Exception as exc:  # noqa: BLE001 — egasi javobsiz qolmasin
            log.warning("Ovozli xabar qayta ishlanmadi: %s", exc)
            await message.answer(uz.VOICE_ERROR)
            return
        log.info("Ovozdan eshitildi: %s", text)
        await message.answer(views.heard_text(text))
        await _process(message, text, ai, searcher)

    @router.message(F.text)
    async def on_text(message: Message, ai: AIClient, searcher) -> None:
        await _process(message, message.text, ai, searcher)

    @router.message(F.location)
    async def on_location(message: Message, ai: AIClient, searcher, geo: Geocoder) -> None:
        pending = _pending.pop("search", None)
        if pending is None:
            await message.answer(uz.LOCATION_UNUSED, reply_markup=ReplyKeyboardRemove())
            return
        city = await geo.city(message.location.latitude, message.location.longitude)
        if not city:
            _pending["search"] = pending
            await message.answer(uz.PLACE_NOT_FOUND)
            return
        await message.answer(
            uz.PLACE_DETECTED.format(city=escape(city, quote=False)), reply_markup=ReplyKeyboardRemove()
        )
        try:
            reply = await run_search(pending, city, ai, searcher)
        except Exception:
            log.exception("Joylashuv bo'yicha qidiruvda kutilmagan xato")
            await message.answer(uz.SEARCH_ERROR)
            return
        _remember(f"📍 {city}", reply)
        await send_reply(message, reply, ai)

    @router.callback_query(F.data == SEARCH_MORE)
    async def on_more(callback: CallbackQuery) -> None:
        await callback.answer()
        if not isinstance(callback.message, Message):
            return
        page = _more_pages.pop(callback.message.message_id, None)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest as exc:
            log.info("Tugma olib tashlanmadi: %s", exc)
        await callback.message.answer(page or uz.SEARCH_EXPIRED, link_preview_options=NO_PREVIEW)

    @router.callback_query(F.data.startswith(DONE_PREFIX))
    async def on_done(callback: CallbackQuery) -> None:
        task_id = parse_done(callback.data)
        answered = False
        try:
            ok = task_id is not None and await db.mark_done(task_id)
            await callback.answer(uz.TASK_DONE_TOAST if ok else uz.TASK_NOT_FOUND_TOAST)
            answered = True
            if not isinstance(callback.message, Message):
                return
            report = await task_report(db, now_tashkent())
            await callback.message.edit_text(report.text, reply_markup=list_markup(report.tasks))
        except TelegramBadRequest as exc:
            # Ikki marta bosilsa matn o'zgarmaydi — Telegram "message is not modified" qaytaradi.
            log.info("Ro'yxat yangilanmadi: %s", exc)
        except Exception:
            log.exception("Vazifani yopishda xato")
            # Telegram har bir bosishga faqat bir marta javob berishga ruxsat beradi.
            if not answered:
                await callback.answer(uz.AI_ERROR, show_alert=True)

    @router.callback_query(F.data == SPEAK_LIST)
    async def on_speak_list(callback: CallbackQuery, ai: AIClient) -> None:
        await callback.answer()
        if not isinstance(callback.message, Message):
            return
        try:
            tasks = views.order_open(await db.list_open_tasks(), now_tashkent())
        except Exception:
            log.exception("Ro'yxatni o'qishda xato")
            await callback.message.answer(uz.AI_ERROR)
            return
        await _send_voice(callback.message, views.format_task_list_for_speech(tasks), ai)

    return router


async def _process(message: Message, text: str, ai: AIClient, searcher) -> None:
    try:
        pending = _pending.pop("search", None)
        if pending is not None and looks_like_place(text):
            place = text.strip()
            await message.answer(
                uz.PLACE_DETECTED.format(city=escape(place, quote=False)), reply_markup=ReplyKeyboardRemove()
            )
            reply = await run_search(pending, place, ai, searcher)
        else:
            reply = await handle_text(text, ai, db, now_tashkent(), searcher, list(_history))
    except AIError as exc:
        log.warning("AI xatosi: %s", exc)
        await message.answer(uz.AI_ERROR)
        return
    except Exception:
        log.exception("Xabarni qayta ishlashda kutilmagan xato")
        await message.answer(uz.AI_ERROR)
        return
    _remember(text, reply)
    await send_reply(message, reply, ai)


def _remember(user_text: str, reply: Reply) -> None:
    _history.append({"role": "user", "content": user_text})
    if reply.text:
        _history.append({"role": "assistant", "content": views.memo(reply.text)})


async def send_reply(message: Message, reply: Reply, ai: AIClient) -> None:
    if reply.kind == "list":
        await message.answer(reply.text, reply_markup=list_markup(reply.tasks))
    elif reply.kind in ("voice", "list_voice"):
        await _send_voice(message, reply.text, ai)
    elif reply.kind == "booking":
        await message.answer(
            reply.text,
            reply_markup=booking_keyboard(reply.url) if reply.url else None,
            link_preview_options=NO_PREVIEW,
        )
    elif reply.kind == "ask_place":
        _pending["search"] = reply.pending
        await message.answer(reply.text, reply_markup=location_keyboard())
    elif reply.kind == "search":
        sent = await message.answer(
            reply.text, reply_markup=more_keyboard() if reply.more else None, link_preview_options=NO_PREVIEW
        )
        if reply.more:
            _more_pages[sent.message_id] = reply.more
            while len(_more_pages) > MORE_PAGES_LIMIT:
                _more_pages.pop(next(iter(_more_pages)))
    else:
        await message.answer(reply.text)


async def _send_voice(message: Message, text: str, ai: AIClient) -> None:
    if not ai.can_speak:
        await message.answer(escape(text, quote=False))
        return
    try:
        audio = await ai.speak(text)
        await message.answer_voice(BufferedInputFile(audio, filename="javob.mp3"))
    except Exception as exc:  # noqa: BLE001 — ovoz chiqmasa ham javob yetib borsin
        log.warning("Ovozli javob yuborilmadi, matnga o'tildi: %s", exc)
        await message.answer(escape(text, quote=False))
