"""Telegram handlerlari: xabarni qabul qiladi, logic'ga beradi, javobni yuboradi."""
from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, InlineKeyboardMarkup, Message

from bot import db, views
from bot.ai_client import AIClient, AIError
from bot.keyboards import DONE_PREFIX, SPEAK_LIST, parse_done, task_list_keyboard
from bot.logic import Reply, handle_text
from bot.models import Task
from bot.scheduler import now_tashkent
from content import uz

log = logging.getLogger(__name__)


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
    async def on_voice(message: Message, bot: Bot, ai: AIClient) -> None:
        try:
            audio = await bot.download(message.voice)
            text = await ai.transcribe(audio.read(), fmt="ogg")
        except Exception as exc:  # noqa: BLE001 — egasi javobsiz qolmasin
            log.warning("Ovozli xabar qayta ishlanmadi: %s", exc)
            await message.answer(uz.VOICE_ERROR)
            return
        await _process(message, text, ai)

    @router.message(F.text)
    async def on_text(message: Message, ai: AIClient) -> None:
        await _process(message, message.text, ai)

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
            tasks = await db.list_open_tasks()
            await callback.message.edit_text(views.format_task_list(tasks), reply_markup=list_markup(tasks))
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
            tasks = await db.list_open_tasks()
        except Exception:
            log.exception("Ro'yxatni o'qishda xato")
            await callback.message.answer(uz.AI_ERROR)
            return
        await _send_voice(callback.message, views.format_task_list_for_speech(tasks), ai)

    return router


async def _process(message: Message, text: str, ai: AIClient) -> None:
    try:
        reply = await handle_text(text, ai, db, now_tashkent())
    except AIError as exc:
        log.warning("AI xatosi: %s", exc)
        await message.answer(uz.AI_ERROR)
        return
    except Exception:
        log.exception("Xabarni qayta ishlashda kutilmagan xato")
        await message.answer(uz.AI_ERROR)
        return
    await send_reply(message, reply, ai)


async def send_reply(message: Message, reply: Reply, ai: AIClient) -> None:
    if reply.kind == "list":
        await message.answer(views.format_task_list(reply.tasks), reply_markup=list_markup(reply.tasks))
    elif reply.kind in ("voice", "list_voice"):
        await _send_voice(message, reply.text, ai)
    else:
        await message.answer(reply.text)


async def _send_voice(message: Message, text: str, ai: AIClient) -> None:
    if not ai.can_speak:
        await message.answer(escape(text))
        return
    try:
        audio = await ai.speak(text)
        await message.answer_voice(BufferedInputFile(audio, filename="javob.mp3"))
    except Exception as exc:  # noqa: BLE001 — ovoz chiqmasa ham javob yetib borsin
        log.warning("Ovozli javob yuborilmadi, matnga o'tildi: %s", exc)
        await message.answer(escape(text))
