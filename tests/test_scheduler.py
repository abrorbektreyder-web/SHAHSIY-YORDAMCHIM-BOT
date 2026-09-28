import asyncio
from datetime import datetime, timezone

import pytest

from bot.scheduler import TASHKENT, daily_report_loop, seconds_until


def test_before_eight_same_day():
    assert seconds_until(datetime(2026, 9, 29, 7, 30, tzinfo=TASHKENT)) == 30 * 60


def test_exactly_eight_goes_to_next_day():
    assert seconds_until(datetime(2026, 9, 29, 8, 0, tzinfo=TASHKENT)) == 24 * 3600


def test_after_eight_goes_to_next_day():
    assert seconds_until(datetime(2026, 9, 29, 20, 0, tzinfo=TASHKENT)) == 12 * 3600


def test_utc_input_is_converted_to_tashkent():
    # 02:00 UTC = 07:00 Toshkent
    assert seconds_until(datetime(2026, 9, 29, 2, 0, tzinfo=timezone.utc)) == 3600


async def test_loop_sends_and_survives_errors():
    sleeps = []
    sends = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) > 2:
            raise asyncio.CancelledError

    async def send():
        sends.append(1)
        raise RuntimeError("tarmoq xatosi")

    with pytest.raises(asyncio.CancelledError):
        await daily_report_loop(send, sleep=fake_sleep)
    assert len(sends) == 2
    assert all(0 < s <= 24 * 3600 for s in sleeps)


async def test_loop_sends_only_once_per_day():
    # Taymer biroz erta uyg'onsa, 08:00 gacha qolgan millisekundlardan keyin
    # ikkinchi marta yubormasligi kerak.
    times = iter([
        datetime(2026, 9, 29, 7, 59, 59, 990000, tzinfo=TASHKENT),
        datetime(2026, 9, 29, 7, 59, 59, 995000, tzinfo=TASHKENT),
        datetime(2026, 9, 29, 7, 59, 59, 999000, tzinfo=TASHKENT),
        datetime(2026, 9, 29, 8, 0, 0, 1000, tzinfo=TASHKENT),
        datetime(2026, 9, 29, 8, 0, 0, 2000, tzinfo=TASHKENT),
    ])
    sleeps = []
    sends = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        if len(sleeps) > 2:
            raise asyncio.CancelledError

    async def send():
        sends.append(1)

    with pytest.raises(asyncio.CancelledError):
        await daily_report_loop(send, sleep=fake_sleep, clock=lambda: next(times))
    assert len(sends) == 1
