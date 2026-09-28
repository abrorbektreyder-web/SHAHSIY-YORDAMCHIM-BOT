"""Bot kirish nuqtasi.

  MODE=polling  — kompyuterda ishlab chiqish uchun (default)
  MODE=webhook  — Render'da; Telegram xabarni o'zi yuboradi

Webhook rejimida `/health` ochiq turadi: UptimeRobot shuni ping qilib,
Render'ning bepul servisi uxlab qolishiga (va 08:00 hisobot o'tib
ketishiga) yo'l qo'ymaydi.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BotCommand, BotCommandScopeChat
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

from bot import db, views
from bot.ai_client import AIClient
from bot.config import Config, load_config
from bot.handlers import build_router, list_markup
from bot.scheduler import daily_report_loop
from content import uz

log = logging.getLogger(__name__)


# Sir manzilga qo'yilmaydi: aiohttp access log har so'rov manzilini logga yozadi.
# Haqiqiy tekshiruv — X-Telegram-Bot-Api-Secret-Token sarlavhasi.
WEBHOOK_PATH = "/tg/webhook"


def webhook_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}{WEBHOOK_PATH}"


async def health(_request) -> web.Response:
    return web.Response(text="ok")


def make_daily_sender(bot, owner_id: int) -> Callable[[], Awaitable[None]]:
    async def send() -> None:
        tasks = await db.list_open_tasks()
        await bot.send_message(owner_id, views.format_daily_report(tasks), reply_markup=list_markup(tasks))

    return send


def build_bot(config: Config, ai: AIClient) -> tuple[Bot, Dispatcher]:
    bot = Bot(config.bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp["ai"] = ai
    dp.include_router(build_router(config.owner_id))
    return bot, dp


async def _setup_commands(bot: Bot, config: Config) -> None:
    try:
        await bot.set_my_commands(
            [BotCommand(command="start", description=uz.COMMAND_START)],
            scope=BotCommandScopeChat(chat_id=config.owner_id),
        )
    except Exception as exc:  # noqa: BLE001 — menyu botni to'xtatmasin
        log.warning("Menyu o'rnatilmadi: %s", exc)


def build_app(bot: Bot, dp: Dispatcher, config: Config) -> web.Application:
    app = web.Application()
    app.router.add_get("/health", health)
    app.router.add_get("/", health)
    SimpleRequestHandler(dispatcher=dp, bot=bot, secret_token=config.webhook_secret).register(
        app, path=WEBHOOK_PATH
    )
    setup_application(app, dp, bot=bot)
    return app


async def _run_polling(bot: Bot, dp: Dispatcher) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Polling rejimi")
    await dp.start_polling(bot)


async def register_webhook(bot, config: Config) -> None:
    # Render qayta ishga tushayotganda kelgan xabarlar tashlab yuborilmasin.
    await bot.set_webhook(
        webhook_url(config.webhook_base_url),
        secret_token=config.webhook_secret,
        drop_pending_updates=False,
    )
    log.info("Webhook o'rnatildi: %s", config.webhook_base_url)


async def _run_webhook(bot: Bot, dp: Dispatcher, config: Config) -> None:
    await register_webhook(bot, config)
    runner = web.AppRunner(build_app(bot, dp, config))
    await runner.setup()
    await web.TCPSite(runner, host="0.0.0.0", port=config.port).start()
    log.info("HTTP server %s portda", config.port)
    await asyncio.Event().wait()


async def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    config = load_config()
    await db.init_db(config.database_url, config.db_schema)
    ai = AIClient(
        openrouter_key=config.openrouter_api_key,
        groq_key=config.groq_api_key,
        llm_provider=config.llm_provider,
        llm_model=config.llm_model,
        stt_provider=config.stt_provider,
    )
    log.info(
        "AI: matn=%s, ovoz→matn=%s, ovozli javob=%s",
        config.llm_provider, config.stt_provider, "yoqilgan" if ai.can_speak else "o'chirilgan",
    )
    bot, dp = build_bot(config, ai)
    await _setup_commands(bot, config)
    reporter = asyncio.create_task(daily_report_loop(make_daily_sender(bot, config.owner_id)))
    log.info("Bot ishga tushdi (%s)", config.mode)
    try:
        if config.mode == "webhook":
            await _run_webhook(bot, dp, config)
        else:
            await _run_polling(bot, dp)
    finally:
        reporter.cancel()
        await ai.close()
        await db.close_pool()
        await bot.session.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
