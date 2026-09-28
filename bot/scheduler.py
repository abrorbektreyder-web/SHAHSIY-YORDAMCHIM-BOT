"""Toshkent vaqti va har kuni 08:00 da ishlaydigan hisobot sikli."""
from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, timedelta, timezone
from typing import Awaitable, Callable

# O'zbekistonda yozgi vaqt yo'q, shuning uchun qat'iy UTC+5 yetarli.
TASHKENT = timezone(timedelta(hours=5), "Asia/Tashkent")
REPORT_HOUR = 8

log = logging.getLogger(__name__)


def now_tashkent() -> datetime:
    return datetime.now(TASHKENT)


def seconds_until(now: datetime, hour: int = REPORT_HOUR) -> float:
    local = now.astimezone(TASHKENT)
    target = local.replace(hour=hour, minute=0, second=0, microsecond=0)
    if target <= local:
        target += timedelta(days=1)
    return (target - local).total_seconds()


async def daily_report_loop(
    send: Callable[[], Awaitable[None]],
    hour: int = REPORT_HOUR,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    clock: Callable[[], datetime] = now_tashkent,
) -> None:
    # asyncio.sleep monoton soat bilan ishlaydi; biroz erta uyg'onsa, 08:00 gacha
    # qolgan millisekundlardan keyin yana yubormaslik uchun sana eslab qolinadi.
    last_sent: date | None = None
    while True:
        await sleep(seconds_until(clock(), hour))
        today = clock().date()
        if today == last_sent:
            continue
        try:
            await send()
            last_sent = today
        except Exception:
            log.exception("Kunlik hisobot yuborilmadi")
