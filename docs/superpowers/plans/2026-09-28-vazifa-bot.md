# Vazifa-Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Egasining matn/ovozli xabarlarini vazifaga aylantiradigan, Supabase'da saqlaydigan, har kuni 08:00 (Toshkent) hisobot yuboradigan va qisqa javoblarni ovozda aytadigan shaxsiy Telegram bot.

**Architecture:** Bitta `aiogram` jarayoni (lokal: polling, Render: webhook + `/health`). Telegram qatlami (`handlers.py`) yupqa: xabarni `logic.handle_text()`ga beradi, u `AIClient` (OpenRouter) va `db` (Supabase) orqali qaror qiladi va `Reply` qaytaradi. Kunlik hisobot — `asyncio` fon vazifasi.

**Tech Stack:** Python 3.10+ (lokal 3.10.11, Render 3.12.7), aiogram 3.x, asyncpg, httpx, python-dotenv, pytest + pytest-asyncio.

**Spec:** `docs/superpowers/specs/2026-09-28-telegram-vazifa-boti-TZ.md`

## Global Constraints

- Botning barcha foydalanuvchiga ko'rinadigan matni — o'zbek tilida (lotin), faqat `content/uz.py`da.
- Faqat `OWNER_ID`ga javob beriladi; boshqalarga hech qanday javob yo'q.
- Kunlik hisobot: har kuni 08:00, Asia/Tashkent (UTC+5, yozgi vaqt yo'q) — `timezone(timedelta(hours=5))`, `zoneinfo` ishlatilmaydi (Windows'da `tzdata` talab qiladi).
- Modellar (faqat `bot/ai_client.py` boshida): STT `google/gemini-3.5-transcribe`, LLM `google/gemini-3.5-flash-lite`, TTS `google/gemini-3.8-flash-tts` (ovoz `Kore`, format `mp3`).
- OpenRouter manzillari: `POST https://openrouter.ai/api/v1/audio/transcriptions` (JSON: `model`, `input_audio{data,format}`, `language`; javob `{"text": ...}`), `POST /api/v1/chat/completions`, `POST /api/v1/audio/speech` (JSON: `model`, `input`, `voice`, `response_format`; javob — xom audio baytlar).
- Qisqa javoblar (vazifa qo'shildi, suhbat) — faqat ovoz; ro'yxat/hisobot — matn + tugmalar; "🔊 Ovozda eshitish" tugmasi yoki ovozli buyruq ro'yxatni ovozga aylantiradi. Ovoz chiqmasa — matnga qaytiladi.
- Ma'lumotlar: Supabase, sxema `DB_SCHEMA` (default `vazifa`), jadval `tasks`. TARGET-AUDIT'ning `bot` sxemasiga tegilmaydi.
- Maxfiy qiymatlar faqat `.env` (lokal, `.gitignore`da) yoki Render Environment'da. Kodga, logga, commit'ga tushmaydi.
- Yangi kutubxonalar faqat `requirements.txt`dagilar.
- Commit — faqat egasi ruxsat bergan bo'lsa (egasining global qoidasi).

## File Structure

```
AGENT-FULL/
├── bot/
│   ├── __init__.py
│   ├── config.py        # .env → Config (TARGET-AUDIT'dan moslashtirilgan)
│   ├── scheduler.py     # TASHKENT, now_tashkent(), seconds_until(), daily_report_loop()
│   ├── models.py        # Task dataclass
│   ├── views.py         # vazifa ro'yxati / hisobot / nutq matnlari
│   ├── db.py            # Supabase: init_db, add_task, list_open_tasks, mark_done, close_pool
│   ├── ai_client.py     # AIClient: transcribe, understand, speak; parse_intent; Intent; AIError
│   ├── logic.py         # handle_text() → Reply
│   ├── keyboards.py     # task_list_keyboard(), parse_done()
│   ├── handlers.py      # build_router(owner_id), send_reply()
│   └── main.py          # ishga tushirish: polling/webhook, /health, kunlik hisobot
├── content/
│   ├── __init__.py
│   └── uz.py            # barcha matnlar + SYSTEM_PROMPT
├── tests/
│   ├── conftest.py
│   ├── test_config.py
│   ├── test_scheduler.py
│   ├── test_views.py
│   ├── test_db.py       # TEST_DATABASE_URL bo'lmasa o'tkazib yuboriladi
│   ├── test_ai_client.py
│   ├── test_logic.py
│   ├── test_keyboards.py
│   └── test_main.py
├── requirements.txt
├── pytest.ini
├── render.yaml
├── .env.example
└── .gitignore
```

Buyruqlar Git Bash'da, loyiha ildizidan ishga tushiriladi. Python: `.venv/Scripts/python`.

---

### Task 1: Loyiha asosi va konfiguratsiya

**Files:**
- Create: `requirements.txt`, `pytest.ini`, `.gitignore`, `.env.example`, `bot/__init__.py`, `content/__init__.py`, `tests/conftest.py`
- Create: `bot/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `bot.config.Config` (frozen dataclass: `bot_token: str`, `owner_id: int`, `openrouter_api_key: str`, `database_url: str`, `db_schema: str = "vazifa"`, `mode: str = "polling"`, `webhook_base_url: str = ""`, `webhook_secret: str = ""`, `port: int = 8080`), `bot.config.ConfigError`, `bot.config.load_config(env_path: str | None = None) -> Config`

- [ ] **Step 1: Asos fayllarini yaratish**

`requirements.txt`:
```
aiogram>=3.31,<4
asyncpg>=0.30,<1
httpx>=0.27,<1
python-dotenv>=1.2,<2
pytest>=8
pytest-asyncio>=1.4
```

`pytest.ini`:
```ini
[pytest]
testpaths = tests
asyncio_mode = auto
pythonpath = .
```

`.gitignore`:
```
.env
.venv/
__pycache__/
*.pyc
.pytest_cache/
```

`.env.example`:
```
BOT_TOKEN=123456:ABC-DEF
OWNER_ID=123456789
OPENROUTER_API_KEY=sk-or-v1-...
DATABASE_URL=postgresql://postgres.xxx:PAROL@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
DB_SCHEMA=vazifa
MODE=polling
# Render o'zi RENDER_EXTERNAL_URL beradi; lokal webhook sinovi uchungina kerak:
# WEBHOOK_BASE_URL=https://vazifa-bot.onrender.com
# WEBHOOK_SECRET=
# PORT=8080
# Faqat db integratsiya testlari uchun (ixtiyoriy):
# TEST_DATABASE_URL=
```

`bot/__init__.py` va `content/__init__.py` — bo'sh fayllar.

`tests/conftest.py`:
```python
from dotenv import load_dotenv

# TEST_DATABASE_URL .env'dan o'qilishi uchun. Config testlari env_path bilan
# ishlaydi, shuning uchun bu ularga ta'sir qilmaydi.
load_dotenv()
```

- [ ] **Step 2: Virtual muhit va kutubxonalarni o'rnatish** (egasining roziligi bilan)

Run: `python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt`
Expected: `Successfully installed aiogram-... asyncpg-... httpx-...` va xatosiz tugaydi.

- [ ] **Step 3: Failing test yozish**

`tests/test_config.py`:
```python
import pytest

from bot.config import ConfigError, load_config

BASE = {
    "BOT_TOKEN": "123:abc",
    "OWNER_ID": "42",
    "OPENROUTER_API_KEY": "sk-or-test",
    "DATABASE_URL": "postgresql://u:p@h:5432/db",
}


def write_env(tmp_path, values):
    path = tmp_path / ".env"
    path.write_text("\n".join(f"{k}={v}" for k, v in values.items()), encoding="utf-8")
    return str(path)


def test_loads_required_values(tmp_path):
    cfg = load_config(write_env(tmp_path, BASE))
    assert cfg.bot_token == "123:abc"
    assert cfg.owner_id == 42
    assert cfg.openrouter_api_key == "sk-or-test"
    assert cfg.db_schema == "vazifa"
    assert cfg.mode == "polling"


def test_missing_openrouter_key_fails(tmp_path):
    values = {k: v for k, v in BASE.items() if k != "OPENROUTER_API_KEY"}
    with pytest.raises(ConfigError, match="OPENROUTER_API_KEY"):
        load_config(write_env(tmp_path, values))


def test_owner_id_must_be_int(tmp_path):
    with pytest.raises(ConfigError, match="OWNER_ID"):
        load_config(write_env(tmp_path, {**BASE, "OWNER_ID": "abrorbek"}))


def test_webhook_requires_base_url(tmp_path):
    with pytest.raises(ConfigError, match="WEBHOOK_BASE_URL"):
        load_config(write_env(tmp_path, {**BASE, "MODE": "webhook"}))


def test_webhook_uses_render_external_url(tmp_path):
    cfg = load_config(write_env(tmp_path, {
        **BASE,
        "MODE": "webhook",
        "RENDER_EXTERNAL_URL": "https://vazifa-bot.onrender.com/",
        "WEBHOOK_SECRET": "s3cret",
    }))
    assert cfg.webhook_base_url == "https://vazifa-bot.onrender.com"


def test_bad_schema_rejected(tmp_path):
    with pytest.raises(ConfigError, match="DB_SCHEMA"):
        load_config(write_env(tmp_path, {**BASE, "DB_SCHEMA": "x;drop"}))
```

- [ ] **Step 4: Test yiqilishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.config'`

- [ ] **Step 5: `bot/config.py`ni yozish**

```python
"""Bot konfiguratsiyasi — .env dan o'qiladi."""
from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Callable

from dotenv import dotenv_values, load_dotenv


class ConfigError(Exception):
    """Konfiguratsiya to'liq emas yoki noto'g'ri."""


@dataclass(frozen=True)
class Config:
    bot_token: str
    owner_id: int
    openrouter_api_key: str
    database_url: str
    db_schema: str = "vazifa"
    mode: str = "polling"
    webhook_base_url: str = ""
    webhook_secret: str = ""
    port: int = 8080


Getter = Callable[[str], str]

MODES = ("polling", "webhook")
# Sxema nomi SQL'ga to'g'ridan-to'g'ri qo'yiladi (identifikatorni parametr qilib bo'lmaydi).
SCHEMA_RE = re.compile(r"^[a-z_][a-z0-9_]*$")


def _require(get: Getter, key: str) -> str:
    value = get(key)
    if not value:
        raise ConfigError(f"{key} .env faylda topilmadi yoki bo'sh")
    return value


def _require_int(get: Getter, key: str) -> int:
    raw = _require(get, key)
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} butun son bo'lishi kerak, keldi: {raw!r}") from exc


def _getter(env_path: str | None) -> Getter:
    """env_path berilsa — faqat o'sha fayl o'qiladi (os.environ'ga tayanmaslik uchun)."""
    if env_path is not None:
        values = dotenv_values(env_path)
        return lambda key: (values.get(key) or "").strip()
    load_dotenv()
    return lambda key: os.getenv(key, "").strip()


def load_config(env_path: str | None = None) -> Config:
    get = _getter(env_path)

    mode = (get("MODE") or "polling").lower()
    if mode not in MODES:
        raise ConfigError(f"MODE faqat {' yoki '.join(MODES)} bo'lishi mumkin, keldi: {mode!r}")

    # Render RENDER_EXTERNAL_URL ni o'zi beradi. Oxiridagi slash olib
    # tashlanadi — aks holda manzilda // hosil bo'ladi.
    base_url = (get("WEBHOOK_BASE_URL") or get("RENDER_EXTERNAL_URL")).rstrip("/")
    if base_url and not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    secret = get("WEBHOOK_SECRET")
    if mode == "webhook":
        if not base_url:
            raise ConfigError("MODE=webhook uchun WEBHOOK_BASE_URL kerak")
        if not secret:
            raise ConfigError("MODE=webhook uchun WEBHOOK_SECRET kerak")

    port_raw = get("PORT")
    try:
        port = int(port_raw) if port_raw else 8080
    except ValueError as exc:
        raise ConfigError(f"PORT butun son bo'lishi kerak, keldi: {port_raw!r}") from exc

    schema = get("DB_SCHEMA") or "vazifa"
    if not SCHEMA_RE.match(schema):
        raise ConfigError(
            f"DB_SCHEMA faqat kichik lotin harf, raqam va _ bo'lishi mumkin, keldi: {schema!r}"
        )

    return Config(
        bot_token=_require(get, "BOT_TOKEN"),
        owner_id=_require_int(get, "OWNER_ID"),
        openrouter_api_key=_require(get, "OPENROUTER_API_KEY"),
        database_url=_require(get, "DATABASE_URL"),
        db_schema=schema,
        mode=mode,
        webhook_base_url=base_url,
        webhook_secret=secret,
        port=port,
    )
```

- [ ] **Step 6: Test o'tishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_config.py -v`
Expected: 6 passed

- [ ] **Step 7: Commit** (egasi ruxsat bergan bo'lsa)

```bash
git add requirements.txt pytest.ini .gitignore .env.example bot/__init__.py content/__init__.py tests/conftest.py bot/config.py tests/test_config.py
git commit -m "feat: loyiha asosi va .env konfiguratsiyasi"
```

---

### Task 2: Toshkent vaqti va kunlik hisobot sikli

**Files:**
- Create: `bot/scheduler.py`
- Test: `tests/test_scheduler.py`

**Interfaces:**
- Produces: `bot.scheduler.TASHKENT: timezone`, `REPORT_HOUR = 8`, `now_tashkent() -> datetime`, `seconds_until(now: datetime, hour: int = REPORT_HOUR) -> float`, `async daily_report_loop(send: Callable[[], Awaitable[None]], hour: int = REPORT_HOUR, sleep: Callable[[float], Awaitable[None]] = asyncio.sleep) -> None`

- [ ] **Step 1: Failing test yozish**

`tests/test_scheduler.py`:
```python
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
```

- [ ] **Step 2: Test yiqilishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_scheduler.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.scheduler'`

- [ ] **Step 3: `bot/scheduler.py`ni yozish**

```python
"""Toshkent vaqti va har kuni 08:00 da ishlaydigan hisobot sikli."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
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
) -> None:
    while True:
        await sleep(seconds_until(now_tashkent(), hour))
        try:
            await send()
        except Exception:
            log.exception("Kunlik hisobot yuborilmadi")
```

- [ ] **Step 4: Test o'tishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_scheduler.py -v`
Expected: 5 passed

- [ ] **Step 5: Commit** (egasi ruxsat bergan bo'lsa)

```bash
git add bot/scheduler.py tests/test_scheduler.py
git commit -m "feat: Toshkent vaqti va kunlik 08:00 hisobot sikli"
```

---

### Task 3: Matnlar va ko'rinishlar

**Files:**
- Create: `bot/models.py`, `content/uz.py`, `bot/views.py`
- Test: `tests/test_views.py`

**Interfaces:**
- Consumes: `bot.scheduler.TASHKENT`
- Produces: `bot.models.Task(id: int, title: str, due_at: datetime | None = None)` (frozen); `content.uz` konstantalari (quyidagi kodda); `bot.views.format_due(due_at: datetime | None) -> str`, `format_task_list(tasks: list[Task], header: str = uz.LIST_HEADER) -> str`, `format_daily_report(tasks: list[Task]) -> str`, `format_task_list_for_speech(tasks: list[Task]) -> str`, `task_added_text(title: str, due_at: datetime | None) -> str`

- [ ] **Step 1: `bot/models.py` va `content/uz.py`ni yaratish**

`bot/models.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    due_at: datetime | None = None
```

`content/uz.py`:
```python
"""Botning barcha o'zbekcha matnlari. Kod matnni faqat shu yerdan oladi."""

START = (
    "Assalomu alaykum! Men sizning shaxsiy yordamchingizman.\n\n"
    "Menga matn yoki ovozli xabar yuboring:\n"
    "• vazifa: <i>«Ertaga soat 15:00 da shifokorga borish»</i>\n"
    "• ro'yxat: <i>«Vazifalarim qanday?»</i>\n"
    "• ovozli hisobot: <i>«Vaqtim yo'q, ovozda ayt»</i>\n\n"
    "Har kuni soat 08:00 da sizga kunlik hisobot yuboraman."
)

TASK_ADDED = "Vazifa qo'shildi: {title}."
TASK_ADDED_DUE = "Vazifa qo'shildi: {title}. Muddati: {due}."

NO_TASKS = "Hozircha ochiq vazifa yo'q. 🎉"
LIST_HEADER = "📋 <b>Ochiq vazifalar ({count} ta):</b>"
DAILY_HEADER = "☀️ <b>Xayrli tong! Bugungi vazifalar ({count} ta):</b>"
DAILY_EMPTY = "☀️ Xayrli tong! Bugun uchun ochiq vazifa yo'q."
NO_DUE = "muddatsiz"

SPEECH_LIST_INTRO = "Sizda {count} ta ochiq vazifa bor."
SPEECH_EMPTY = "Hozircha ochiq vazifa yo'q."

DONE_BUTTON = "✅ {n}. {title}"
SPEAK_BUTTON = "🔊 Ovozda eshitish"
TASK_DONE_TOAST = "Bajarildi ✅"
TASK_NOT_FOUND_TOAST = "Bu vazifa topilmadi"

NOT_UNDERSTOOD = "Kechirasiz, buni tushunmadim. Boshqacharoq yozib yoki aytib ko'ra olasizmi?"
AI_ERROR = "Kechirasiz, hozir javob bera olmadim. Birozdan keyin qayta urinib ko'ring."
VOICE_ERROR = "Ovozli xabarni tushuna olmadim. Iltimos, qaytadan yuboring yoki yozib yuboring."

COMMAND_START = "Yordamchini boshlash"

# {now} — joriy vaqt; qolgan jingalak qavslar JSON uchun ikkilangan.
SYSTEM_PROMPT = """You are a personal task assistant bot. The user writes in Uzbek (Latin or Cyrillic).
Current date and time (Asia/Tashkent, UTC+5): {now}.

Classify the user's message and answer ONLY with one JSON object, no other text:
{{"intent": "...", "title": "...", "due_at": "...", "reply": "..."}}

intent values:
- "add_task": the user asks to remember or do something. "title" = short task name in Uzbek Latin. "due_at" = ISO 8601 with +05:00 offset if a date or time is mentioned (resolve "bugun", "ertaga", "indinga", weekday names relative to the current date; if only a date is given use 09:00), otherwise null.
- "list_tasks": the user asks to see the tasks, list or report as text.
- "speak_report": the user asks to hear the tasks or report by voice (e.g. "ovozda ayt", "vaqtim yo'q, eshittir", "o'qib ber").
- "chat": anything else (questions, greetings). "reply" = short helpful answer in Uzbek Latin, at most 3 sentences.
- "unknown": the message is empty or meaningless.

For intents other than "chat", "reply" = "". For intents other than "add_task", "title" and "due_at" = null."""
```

- [ ] **Step 2: Failing test yozish**

`tests/test_views.py`:
```python
from datetime import datetime

from bot import views
from bot.models import Task
from bot.scheduler import TASHKENT
from content import uz

DUE = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)


def test_empty_list():
    assert views.format_task_list([]) == uz.NO_TASKS


def test_list_numbers_due_and_count():
    text = views.format_task_list([Task(1, "Shifokor", DUE), Task(7, "Non olish")])
    assert "(2 ta)" in text
    assert "1. Shifokor — <i>29.09.2026 15:00</i>" in text
    assert "2. Non olish — <i>muddatsiz</i>" in text


def test_title_is_html_escaped():
    assert "&lt;b&gt;x&lt;/b&gt;" in views.format_task_list([Task(1, "<b>x</b>")])


def test_due_converted_to_tashkent():
    from datetime import timezone
    utc = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
    assert views.format_due(utc) == "29.09.2026 15:00"


def test_daily_empty_and_full():
    assert views.format_daily_report([]) == uz.DAILY_EMPTY
    assert "Xayrli tong" in views.format_daily_report([Task(1, "Non")])


def test_speech_text_has_no_html():
    text = views.format_task_list_for_speech([Task(1, "Shifokor", DUE), Task(2, "Non")])
    assert text == (
        "Sizda 2 ta ochiq vazifa bor. "
        "1. Shifokor, muddati 29.09.2026 15:00. "
        "2. Non."
    )


def test_speech_empty():
    assert views.format_task_list_for_speech([]) == uz.SPEECH_EMPTY


def test_task_added_text():
    assert views.task_added_text("Non", None) == "Vazifa qo'shildi: Non."
    assert (
        views.task_added_text("Shifokor", DUE)
        == "Vazifa qo'shildi: Shifokor. Muddati: 29.09.2026 15:00."
    )
```

- [ ] **Step 3: Test yiqilishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_views.py -v`
Expected: FAIL — `ImportError: cannot import name 'views' from 'bot'`

- [ ] **Step 4: `bot/views.py`ni yozish**

```python
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
```

- [ ] **Step 5: Test o'tishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_views.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit** (egasi ruxsat bergan bo'lsa)

```bash
git add bot/models.py content/uz.py bot/views.py tests/test_views.py
git commit -m "feat: o'zbekcha matnlar va vazifa ro'yxati ko'rinishi"
```

---

### Task 4: Supabase qatlami

**Files:**
- Create: `bot/db.py`
- Test: `tests/test_db.py`

**Interfaces:**
- Consumes: `bot.models.Task`
- Produces: `async init_db(database_url: str, schema: str = "vazifa") -> None`, `async add_task(title: str, due_at: datetime | None) -> int`, `async list_open_tasks() -> list[Task]` (tartib: `due_at` o'sish bo'yicha, muddatsizlar oxirida, keyin `id`), `async mark_done(task_id: int) -> bool` (faqat ochiq vazifa yopilsa `True`), `async close_pool() -> None`. `init_db` chaqirilmasdan boshqa funksiya chaqirilsa — `RuntimeError`.

Integratsiya testlari haqiqiy Supabase'da `vazifa_test` sxemasida ishlaydi va har testdan oldin/keyin uni o'chiradi. `.env`da `TEST_DATABASE_URL` bo'lmasa — o'tkazib yuboriladi. Egasi `TEST_DATABASE_URL`ni `.env`ga o'zi yozadi (Supabase `DATABASE_URL` bilan bir xil qiymat).

- [ ] **Step 1: Failing test yozish**

`tests/test_db.py`:
```python
import os
from datetime import datetime

import asyncpg
import pytest

from bot import db
from bot.scheduler import TASHKENT

URL = os.getenv("TEST_DATABASE_URL")
SCHEMA = "vazifa_test"

pytestmark = pytest.mark.skipif(not URL, reason="TEST_DATABASE_URL berilmagan")


async def _drop_schema():
    conn = await asyncpg.connect(URL, statement_cache_size=0)
    try:
        await conn.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    finally:
        await conn.close()


@pytest.fixture
async def fresh_db():
    await _drop_schema()
    await db.init_db(URL, SCHEMA)
    yield
    await db.close_pool()
    await _drop_schema()


async def test_add_and_list(fresh_db):
    due = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)
    task_id = await db.add_task("Shifokor", due)
    tasks = await db.list_open_tasks()
    assert [(t.id, t.title) for t in tasks] == [(task_id, "Shifokor")]
    assert tasks[0].due_at == due


async def test_mark_done_hides_task(fresh_db):
    task_id = await db.add_task("Non olish", None)
    assert await db.mark_done(task_id) is True
    assert await db.list_open_tasks() == []
    assert await db.mark_done(task_id) is False


async def test_order_dated_first_then_undated(fresh_db):
    undated = await db.add_task("Muddatsiz", None)
    late = await db.add_task("Kech", datetime(2026, 10, 1, 9, 0, tzinfo=TASHKENT))
    early = await db.add_task("Erta", datetime(2026, 9, 30, 9, 0, tzinfo=TASHKENT))
    assert [t.id for t in await db.list_open_tasks()] == [early, late, undated]


async def test_init_db_is_idempotent(fresh_db):
    await db.add_task("Saqlanib qolsin", None)
    await db.close_pool()
    await db.init_db(URL, SCHEMA)
    assert [t.title for t in await db.list_open_tasks()] == ["Saqlanib qolsin"]


async def test_use_before_init_raises():
    await db.close_pool()
    with pytest.raises(RuntimeError):
        await db.list_open_tasks()
```

- [ ] **Step 2: Test yiqilishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_db.py -v`
Expected: FAIL — `ImportError: cannot import name 'db' from 'bot'` (agar `TEST_DATABASE_URL` bo'lmasa — import xatosi baribir ko'rinadi, chunki import skip'dan oldin bajariladi)

- [ ] **Step 3: `bot/db.py`ni yozish**

```python
"""Supabase (PostgreSQL) bilan ishlash. Boshqa modullar SQL yozmaydi."""
from __future__ import annotations

from datetime import datetime

import asyncpg

from bot.models import Task

_pool: asyncpg.Pool | None = None
_schema = "vazifa"


async def init_db(database_url: str, schema: str = "vazifa") -> None:
    global _pool, _schema
    _schema = schema
    # Supabase pooler (pgbouncer) prepared statement keshini qo'llamaydi.
    _pool = await asyncpg.create_pool(
        database_url, min_size=1, max_size=3, statement_cache_size=0
    )
    async with _pool.acquire() as conn:
        await conn.execute(f"CREATE SCHEMA IF NOT EXISTS {_schema}")
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {_schema}.tasks (
                id          BIGSERIAL PRIMARY KEY,
                title       TEXT        NOT NULL,
                due_at      TIMESTAMPTZ,
                done        BOOLEAN     NOT NULL DEFAULT FALSE,
                done_at     TIMESTAMPTZ,
                created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )


def _pool_or_fail() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("init_db() chaqirilmagan")
    return _pool


async def add_task(title: str, due_at: datetime | None) -> int:
    return await _pool_or_fail().fetchval(
        f"INSERT INTO {_schema}.tasks (title, due_at) VALUES ($1, $2) RETURNING id",
        title,
        due_at,
    )


async def list_open_tasks() -> list[Task]:
    rows = await _pool_or_fail().fetch(
        f"SELECT id, title, due_at FROM {_schema}.tasks "
        f"WHERE NOT done ORDER BY due_at NULLS LAST, id"
    )
    return [Task(row["id"], row["title"], row["due_at"]) for row in rows]


async def mark_done(task_id: int) -> bool:
    result = await _pool_or_fail().execute(
        f"UPDATE {_schema}.tasks SET done = TRUE, done_at = now() WHERE id = $1 AND NOT done",
        task_id,
    )
    return result == "UPDATE 1"


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
```

- [ ] **Step 4: Test o'tishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_db.py -v`
Expected: `TEST_DATABASE_URL` bor bo'lsa — 5 passed. Yo'q bo'lsa — 5 skipped (bu holatda egasiga aytiladi, blok "qisman" deb belgilanadi).

- [ ] **Step 5: Commit** (egasi ruxsat bergan bo'lsa)

```bash
git add bot/db.py tests/test_db.py
git commit -m "feat: Supabase'da vazifalarni saqlash qatlami"
```

---

### Task 5: OpenRouter AI mijozi

**Files:**
- Create: `bot/ai_client.py`
- Test: `tests/test_ai_client.py`

**Interfaces:**
- Consumes: `content.uz.SYSTEM_PROMPT`, `bot.scheduler.TASHKENT`
- Produces: `class AIError(Exception)`; `Intent(kind: str, title: str | None = None, due_at: datetime | None = None, reply: str = "")` (frozen; `kind` ∈ `"add_task" | "list_tasks" | "speak_report" | "chat" | "unknown"`); `parse_intent(raw: str) -> Intent`; `class AIClient(api_key: str, http: httpx.AsyncClient | None = None)` with `async transcribe(audio: bytes, fmt: str = "ogg") -> str`, `async understand(text: str, now: datetime) -> Intent`, `async speak(text: str) -> bytes`, `async close() -> None`. Har qanday tarmoq/HTTP/format xatosi → `AIError`.

- [ ] **Step 1: Failing test yozish**

`tests/test_ai_client.py`:
```python
import base64
import json
from datetime import datetime

import httpx
import pytest

from bot.ai_client import (
    LLM_MODEL,
    STT_MODEL,
    TTS_MODEL,
    AIClient,
    AIError,
    Intent,
    parse_intent,
)
from bot.scheduler import TASHKENT

NOW = datetime(2026, 9, 28, 19, 0, tzinfo=TASHKENT)
DUE = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)


def client_with(handler):
    return AIClient("sk-test", http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def chat_response(content):
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


# --- parse_intent ---

def test_parse_add_task_with_due():
    raw = '{"intent":"add_task","title":"Shifokorga borish","due_at":"2026-09-29T15:00:00+05:00","reply":""}'
    assert parse_intent(raw) == Intent("add_task", "Shifokorga borish", DUE, "")


def test_parse_strips_code_fence():
    raw = '```json\n{"intent":"list_tasks","title":null,"due_at":null,"reply":""}\n```'
    assert parse_intent(raw) == Intent("list_tasks")


def test_parse_garbage_is_unknown():
    assert parse_intent("salom").kind == "unknown"
    assert parse_intent("[1, 2]").kind == "unknown"
    assert parse_intent('{"intent":"fly"}').kind == "unknown"


def test_parse_add_task_without_title_is_unknown():
    assert parse_intent('{"intent":"add_task","title":"","due_at":null}').kind == "unknown"


def test_parse_bad_due_is_dropped():
    intent = parse_intent('{"intent":"add_task","title":"X","due_at":"ertaga"}')
    assert intent == Intent("add_task", "X", None, "")


def test_parse_naive_due_gets_tashkent_and_z_is_utc():
    naive = parse_intent('{"intent":"add_task","title":"X","due_at":"2026-09-29T15:00:00"}')
    assert naive.due_at == DUE
    zulu = parse_intent('{"intent":"add_task","title":"X","due_at":"2026-09-29T10:00:00Z"}')
    assert zulu.due_at == DUE


def test_parse_chat_keeps_only_reply():
    raw = '{"intent":"chat","title":"ignored","due_at":null,"reply":"Salom!"}'
    assert parse_intent(raw) == Intent("chat", None, None, "Salom!")


def test_parse_chat_without_reply_is_unknown():
    assert parse_intent('{"intent":"chat","reply":""}').kind == "unknown"


# --- HTTP ---

async def test_transcribe_sends_base64_and_returns_text():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"text": " Ertaga bankka borish "})

    assert await client_with(handler).transcribe(b"OGGDATA") == "Ertaga bankka borish"
    assert seen["url"] == "https://openrouter.ai/api/v1/audio/transcriptions"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["model"] == STT_MODEL
    assert seen["body"]["input_audio"] == {
        "data": base64.b64encode(b"OGGDATA").decode(),
        "format": "ogg",
    }
    assert seen["body"]["language"] == "uz"


async def test_transcribe_empty_text_raises():
    ai = client_with(lambda r: httpx.Response(200, json={"text": "  "}))
    with pytest.raises(AIError):
        await ai.transcribe(b"x")


async def test_http_error_raises_aierror():
    ai = client_with(lambda r: httpx.Response(402, text="no credits"))
    with pytest.raises(AIError, match="402"):
        await ai.transcribe(b"x")


async def test_network_error_raises_aierror():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(AIError, match="tarmoq"):
        await client_with(handler).speak("salom")


async def test_understand_sends_prompt_with_now_and_parses():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return chat_response('{"intent":"list_tasks","title":null,"due_at":null,"reply":""}')

    intent = await client_with(handler).understand("vazifalarim?", NOW)
    assert intent == Intent("list_tasks")
    assert seen["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert seen["body"]["model"] == LLM_MODEL
    assert "2026-09-28T19:00+05:00" in seen["body"]["messages"][0]["content"]
    assert seen["body"]["messages"][1] == {"role": "user", "content": "vazifalarim?"}
    assert seen["body"]["response_format"] == {"type": "json_object"}


async def test_understand_malformed_response_raises():
    ai = client_with(lambda r: httpx.Response(200, json={"oops": 1}))
    with pytest.raises(AIError):
        await ai.understand("x", NOW)


async def test_speak_returns_audio_bytes():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, content=b"MP3BYTES", headers={"Content-Type": "audio/mpeg"})

    assert await client_with(handler).speak("Vazifa qo'shildi") == b"MP3BYTES"
    assert seen["url"] == "https://openrouter.ai/api/v1/audio/speech"
    assert seen["body"] == {
        "model": TTS_MODEL,
        "input": "Vazifa qo'shildi",
        "voice": "Kore",
        "response_format": "mp3",
    }


async def test_speak_empty_audio_raises():
    ai = client_with(lambda r: httpx.Response(200, content=b""))
    with pytest.raises(AIError):
        await ai.speak("x")
```

- [ ] **Step 2: Test yiqilishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_ai_client.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.ai_client'`

- [ ] **Step 3: `bot/ai_client.py`ni yozish**

```python
"""OpenRouter orqali uchta AI xizmati: nutq→matn, matnni tushunish, matn→nutq."""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime

import httpx

from bot.scheduler import TASHKENT
from content import uz

BASE_URL = "https://openrouter.ai/api/v1"
STT_MODEL = "google/gemini-3.5-transcribe"
LLM_MODEL = "google/gemini-3.5-flash-lite"
TTS_MODEL = "google/gemini-3.8-flash-tts"
TTS_VOICE = "Kore"

INTENTS = ("add_task", "list_tasks", "speak_report", "chat", "unknown")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")


class AIError(Exception):
    """OpenRouter javob bermadi yoki kutilmagan javob qaytardi."""


@dataclass(frozen=True)
class Intent:
    kind: str
    title: str | None = None
    due_at: datetime | None = None
    reply: str = ""


def _parse_due(raw: object) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        # Python 3.10 fromisoformat "Z" qo'shimchasini tushunmaydi.
        due = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    return due if due.tzinfo else due.replace(tzinfo=TASHKENT)


def parse_intent(raw: str) -> Intent:
    try:
        data = json.loads(_FENCE.sub("", raw.strip()))
    except json.JSONDecodeError:
        return Intent("unknown")
    if not isinstance(data, dict) or data.get("intent") not in INTENTS:
        return Intent("unknown")

    kind = data["intent"]
    if kind == "add_task":
        title = (data.get("title") or "").strip()
        if not title:
            return Intent("unknown")
        return Intent("add_task", title, _parse_due(data.get("due_at")), "")
    if kind == "chat":
        reply = (data.get("reply") or "").strip()
        return Intent("chat", reply=reply) if reply else Intent("unknown")
    return Intent(kind)


class AIClient:
    def __init__(self, api_key: str, http: httpx.AsyncClient | None = None) -> None:
        self._http = http or httpx.AsyncClient(timeout=60)
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def _post(self, path: str, payload: dict) -> httpx.Response:
        try:
            resp = await self._http.post(f"{BASE_URL}{path}", json=payload, headers=self._headers)
        except httpx.HTTPError as exc:
            raise AIError(f"{path}: tarmoq xatosi: {exc}") from exc
        if resp.status_code != 200:
            raise AIError(f"{path}: HTTP {resp.status_code}: {resp.text[:200]}")
        return resp

    async def transcribe(self, audio: bytes, fmt: str = "ogg") -> str:
        resp = await self._post(
            "/audio/transcriptions",
            {
                "model": STT_MODEL,
                "input_audio": {"data": base64.b64encode(audio).decode(), "format": fmt},
                "language": "uz",
            },
        )
        text = (resp.json().get("text") or "").strip()
        if not text:
            raise AIError("transkripsiya bo'sh qaytdi")
        return text

    async def understand(self, text: str, now: datetime) -> Intent:
        resp = await self._post(
            "/chat/completions",
            {
                "model": LLM_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": uz.SYSTEM_PROMPT.format(now=now.isoformat(timespec="minutes")),
                    },
                    {"role": "user", "content": text},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
        )
        try:
            raw = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise AIError(f"chat javobi kutilmagan shaklda: {resp.text[:200]}") from exc
        return parse_intent(raw or "")

    async def speak(self, text: str) -> bytes:
        resp = await self._post(
            "/audio/speech",
            {"model": TTS_MODEL, "input": text, "voice": TTS_VOICE, "response_format": "mp3"},
        )
        if not resp.content:
            raise AIError("ovoz bo'sh qaytdi")
        return resp.content

    async def close(self) -> None:
        await self._http.aclose()
```

- [ ] **Step 4: Test o'tishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_ai_client.py -v`
Expected: 16 passed

- [ ] **Step 5: Commit** (egasi ruxsat bergan bo'lsa)

```bash
git add bot/ai_client.py tests/test_ai_client.py
git commit -m "feat: OpenRouter orqali ovoz, tushunish va nutq"
```

---

### Task 6: Bot mantiqi

**Files:**
- Create: `bot/logic.py`
- Test: `tests/test_logic.py`

**Interfaces:**
- Consumes: `AIClient.understand(text, now) -> Intent`; store — `add_task(title, due_at) -> int` va `list_open_tasks() -> list[Task]` funksiyalari bor istalgan obyekt (`bot.db` moduli ham mos keladi); `bot.views.task_added_text`, `format_task_list_for_speech`
- Produces: `Reply(kind: str, text: str = "", tasks: list[Task] = [])` (frozen; `kind` ∈ `"voice" | "text" | "list" | "list_voice"`); `async handle_text(text: str, ai, store, now: datetime) -> Reply`

- [ ] **Step 1: Failing test yozish**

`tests/test_logic.py`:
```python
from datetime import datetime

from bot.ai_client import Intent
from bot.logic import Reply, handle_text
from bot.models import Task
from bot.scheduler import TASHKENT
from content import uz

NOW = datetime(2026, 9, 28, 19, 0, tzinfo=TASHKENT)
DUE = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)


class FakeAI:
    def __init__(self, intent):
        self.intent = intent
        self.seen = []

    async def understand(self, text, now):
        self.seen.append((text, now))
        return self.intent


class FakeStore:
    def __init__(self, tasks=None):
        self.tasks = tasks or []
        self.added = []

    async def add_task(self, title, due_at):
        self.added.append((title, due_at))
        return 1

    async def list_open_tasks(self):
        return self.tasks


async def test_add_task_saves_and_replies_by_voice():
    store = FakeStore()
    reply = await handle_text("ertaga 15:00 shifokor", FakeAI(Intent("add_task", "Shifokor", DUE)), store, NOW)
    assert store.added == [("Shifokor", DUE)]
    assert reply == Reply("voice", "Vazifa qo'shildi: Shifokor. Muddati: 29.09.2026 15:00.")


async def test_list_returns_tasks():
    tasks = [Task(1, "Non")]
    reply = await handle_text("ro'yxat", FakeAI(Intent("list_tasks")), FakeStore(tasks), NOW)
    assert reply == Reply("list", tasks=tasks)


async def test_speak_report_returns_speech_text():
    tasks = [Task(1, "Non")]
    reply = await handle_text("ovozda ayt", FakeAI(Intent("speak_report")), FakeStore(tasks), NOW)
    assert reply == Reply("list_voice", "Sizda 1 ta ochiq vazifa bor. 1. Non.", tasks)


async def test_chat_reply_goes_to_voice():
    reply = await handle_text("salom", FakeAI(Intent("chat", reply="Va alaykum assalom!")), FakeStore(), NOW)
    assert reply == Reply("voice", "Va alaykum assalom!")


async def test_unknown_asks_again_as_text_and_saves_nothing():
    store = FakeStore()
    reply = await handle_text("...", FakeAI(Intent("unknown")), store, NOW)
    assert reply == Reply("text", uz.NOT_UNDERSTOOD)
    assert store.added == []


async def test_passes_text_and_now_to_ai():
    ai = FakeAI(Intent("unknown"))
    await handle_text("x", ai, FakeStore(), NOW)
    assert ai.seen == [("x", NOW)]
```

- [ ] **Step 2: Test yiqilishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_logic.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.logic'`

- [ ] **Step 3: `bot/logic.py`ni yozish**

```python
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
```

- [ ] **Step 4: Test o'tishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_logic.py -v`
Expected: 6 passed

- [ ] **Step 5: Commit** (egasi ruxsat bergan bo'lsa)

```bash
git add bot/logic.py tests/test_logic.py
git commit -m "feat: xabarni vazifa/ro'yxat/suhbatga ajratish mantiqi"
```

---

### Task 7: Tugmalar va Telegram handlerlar

**Files:**
- Create: `bot/keyboards.py`, `bot/handlers.py`
- Test: `tests/test_keyboards.py`

**Interfaces:**
- Consumes: `Task`, `uz.DONE_BUTTON`, `uz.SPEAK_BUTTON`, `handle_text`, `Reply`, `AIClient`, `AIError`, `bot.db`, `bot.views`, `now_tashkent`
- Produces: `bot.keyboards.DONE_PREFIX = "done:"`, `SPEAK_LIST = "speak:list"`, `task_list_keyboard(tasks: list[Task]) -> InlineKeyboardMarkup`, `parse_done(data: str) -> int | None`; `bot.handlers.build_router(owner_id: int) -> Router` (handlerlar `ai: AIClient`ni dispatcher'ning `dp["ai"]` qiymatidan oladi), `bot.handlers.list_markup(tasks) -> InlineKeyboardMarkup | None`

`handlers.py` — Telegram'ga yupqa qatlam; uning mantig'i Task 6'da testlangan, o'zi esa Task 9'da haqiqiy bot bilan sinaladi.

- [ ] **Step 1: Failing test yozish**

`tests/test_keyboards.py`:
```python
from bot.keyboards import parse_done, task_list_keyboard
from bot.models import Task


def test_keyboard_has_done_per_task_and_speak_button():
    rows = task_list_keyboard([Task(5, "Non"), Task(9, "Shifokor")]).inline_keyboard
    assert [row[0].callback_data for row in rows] == ["done:5", "done:9", "speak:list"]
    assert rows[0][0].text == "✅ 1. Non"
    assert rows[2][0].text == "🔊 Ovozda eshitish"


def test_long_title_is_shortened():
    rows = task_list_keyboard([Task(1, "a" * 50)]).inline_keyboard
    assert rows[0][0].text == "✅ 1. " + "a" * 29 + "…"


def test_parse_done():
    assert parse_done("done:12") == 12
    assert parse_done("done:x") is None
    assert parse_done("speak:list") is None
```

- [ ] **Step 2: Test yiqilishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_keyboards.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'bot.keyboards'`

- [ ] **Step 3: `bot/keyboards.py`ni yozish**

```python
"""Inline tugmalar."""
from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models import Task
from content import uz

DONE_PREFIX = "done:"
SPEAK_LIST = "speak:list"
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
```

- [ ] **Step 4: Test o'tishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_keyboards.py -v`
Expected: 3 passed

- [ ] **Step 5: `bot/handlers.py`ni yozish**

```python
"""Telegram handlerlari: xabarni qabul qiladi, logic'ga beradi, javobni yuboradi."""
from __future__ import annotations

import logging
from html import escape

from aiogram import Bot, F, Router
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
        audio = await bot.download(message.voice)
        try:
            text = await ai.transcribe(audio.read(), fmt="ogg")
        except AIError as exc:
            log.warning("Transkripsiya xatosi: %s", exc)
            await message.answer(uz.VOICE_ERROR)
            return
        await _process(message, text, ai)

    @router.message(F.text)
    async def on_text(message: Message, ai: AIClient) -> None:
        await _process(message, message.text, ai)

    @router.callback_query(F.data.startswith(DONE_PREFIX))
    async def on_done(callback: CallbackQuery) -> None:
        task_id = parse_done(callback.data)
        ok = task_id is not None and await db.mark_done(task_id)
        await callback.answer(uz.TASK_DONE_TOAST if ok else uz.TASK_NOT_FOUND_TOAST)
        tasks = await db.list_open_tasks()
        await callback.message.edit_text(views.format_task_list(tasks), reply_markup=list_markup(tasks))

    @router.callback_query(F.data == SPEAK_LIST)
    async def on_speak_list(callback: CallbackQuery, ai: AIClient) -> None:
        await callback.answer()
        tasks = await db.list_open_tasks()
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
    try:
        audio = await ai.speak(text)
        await message.answer_voice(BufferedInputFile(audio, filename="javob.mp3"))
    except Exception as exc:  # noqa: BLE001 — ovoz chiqmasa ham javob yetib borsin
        log.warning("Ovozli javob yuborilmadi, matnga o'tildi: %s", exc)
        await message.answer(escape(text))
```

- [ ] **Step 6: Import tekshiruvi va barcha testlar**

Run: `.venv/Scripts/python -c "from bot.handlers import build_router; build_router(1)" && .venv/Scripts/python -m pytest -v`
Expected: xatosiz import; barcha testlar passed (db testlari `TEST_DATABASE_URL` bo'lmasa skipped)

- [ ] **Step 7: Commit** (egasi ruxsat bergan bo'lsa)

```bash
git add bot/keyboards.py bot/handlers.py tests/test_keyboards.py
git commit -m "feat: Telegram handlerlar va vazifa tugmalari"
```

---

### Task 8: Ishga tushirish va Render sozlamasi

**Files:**
- Create: `bot/main.py`, `render.yaml`
- Test: `tests/test_main.py`

**Interfaces:**
- Consumes: `load_config`, `db.init_db/close_pool/list_open_tasks`, `AIClient`, `build_router`, `list_markup`, `daily_report_loop`, `views.format_daily_report`, `uz.COMMAND_START`
- Produces: `webhook_path(secret: str) -> str`, `webhook_url(base_url: str, secret: str) -> str`, `make_daily_sender(bot, owner_id: int) -> Callable[[], Awaitable[None]]`, `build_bot(config: Config, ai: AIClient) -> tuple[Bot, Dispatcher]`, `main()`; ishga tushirish buyrug'i `python -m bot.main`

- [ ] **Step 1: Failing test yozish**

`tests/test_main.py`:
```python
from bot import main
from bot.models import Task


def test_webhook_path_and_url():
    assert main.webhook_path("abc") == "/tg/abc"
    assert main.webhook_url("https://x.onrender.com/", "abc") == "https://x.onrender.com/tg/abc"


async def test_daily_sender_sends_report_with_buttons_to_owner(monkeypatch):
    sent = {}

    class FakeBot:
        async def send_message(self, chat_id, text, reply_markup=None):
            sent.update(chat_id=chat_id, text=text, markup=reply_markup)

    async def fake_list():
        return [Task(3, "Non")]

    monkeypatch.setattr(main.db, "list_open_tasks", fake_list)
    await main.make_daily_sender(FakeBot(), 42)()
    assert sent["chat_id"] == 42
    assert "Xayrli tong" in sent["text"]
    assert sent["markup"].inline_keyboard[0][0].callback_data == "done:3"


async def test_daily_sender_empty_has_no_buttons(monkeypatch):
    sent = {}

    class FakeBot:
        async def send_message(self, chat_id, text, reply_markup=None):
            sent.update(text=text, markup=reply_markup)

    async def fake_list():
        return []

    monkeypatch.setattr(main.db, "list_open_tasks", fake_list)
    await main.make_daily_sender(FakeBot(), 42)()
    assert sent["markup"] is None
```

- [ ] **Step 2: Test yiqilishini tekshirish**

Run: `.venv/Scripts/python -m pytest tests/test_main.py -v`
Expected: FAIL — `ImportError: cannot import name 'main' from 'bot'`

- [ ] **Step 3: `bot/main.py`ni yozish**

```python
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


def webhook_path(secret: str) -> str:
    return f"/tg/{secret}"


def webhook_url(base_url: str, secret: str) -> str:
    return f"{base_url.rstrip('/')}{webhook_path(secret)}"


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
        app, path=webhook_path(config.webhook_secret)
    )
    setup_application(app, dp, bot=bot)
    return app


async def _run_polling(bot: Bot, dp: Dispatcher) -> None:
    await bot.delete_webhook(drop_pending_updates=True)
    log.info("Polling rejimi")
    await dp.start_polling(bot)


async def _run_webhook(bot: Bot, dp: Dispatcher, config: Config) -> None:
    await bot.set_webhook(
        webhook_url(config.webhook_base_url, config.webhook_secret),
        secret_token=config.webhook_secret,
        drop_pending_updates=True,
    )
    log.info("Webhook o'rnatildi: %s", config.webhook_base_url)
    runner = web.AppRunner(build_app(bot, dp, config))
    await runner.setup()
    await web.TCPSite(runner, host="0.0.0.0", port=config.port).start()
    log.info("HTTP server %s portda", config.port)
    await asyncio.Event().wait()


async def run() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
    config = load_config()
    await db.init_db(config.database_url, config.db_schema)
    ai = AIClient(config.openrouter_api_key)
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
```

- [ ] **Step 4: `render.yaml`ni yozish**

```yaml
services:
  - type: web
    name: vazifa-bot
    runtime: python
    plan: free
    region: frankfurt
    buildCommand: pip install -r requirements.txt
    startCommand: python -m bot.main
    healthCheckPath: /health
    envVars:
      - key: PYTHON_VERSION
        value: 3.12.7
      - key: MODE
        value: webhook
      - key: DB_SCHEMA
        value: vazifa
      - key: WEBHOOK_SECRET
        generateValue: true
      - key: BOT_TOKEN
        sync: false
      - key: OWNER_ID
        sync: false
      - key: OPENROUTER_API_KEY
        sync: false
      - key: DATABASE_URL
        sync: false
```

- [ ] **Step 5: Testlar o'tishini tekshirish**

Run: `.venv/Scripts/python -m pytest -v`
Expected: barcha testlar passed (db testlari `TEST_DATABASE_URL` bo'lmasa skipped)

- [ ] **Step 6: Commit** (egasi ruxsat bergan bo'lsa)

```bash
git add bot/main.py render.yaml tests/test_main.py
git commit -m "feat: ishga tushirish, webhook/polling va Render Blueprint"
```

---

### Task 9: Lokal sinov (haqiqiy bot bilan)

**Files:** yo'q (faqat sinov). Egasi `.env` faylini `.env.example`dan nusxalab, o'z qiymatlarini o'zi yozadi — qiymatlar chatga yozilmaydi.

- [ ] **Step 1: Egasi `.env`ni to'ldiradi** — `BOT_TOKEN` (yangi bot), `OWNER_ID`, `OPENROUTER_API_KEY`, `DATABASE_URL`, `DB_SCHEMA=vazifa`, `MODE=polling`, ixtiyoriy `TEST_DATABASE_URL`.

- [ ] **Step 2: db integratsiya testlari** (agar `TEST_DATABASE_URL` yozilgan bo'lsa)

Run: `.venv/Scripts/python -m pytest tests/test_db.py -v`
Expected: 5 passed

- [ ] **Step 3: Botni ishga tushirish** (fon rejimida)

Run: `.venv/Scripts/python -m bot.main`
Expected: logda `Bot ishga tushdi (polling)` va `Polling rejimi`, xato yo'q.

- [ ] **Step 4: Sinov ssenariysi** (egasi Telegram'da bajaradi, natijani log bilan birga tekshiramiz)
1. `/start` → salomlashish matni.
2. Matn: "Ertaga soat 15:00 da shifokorga borish" → ovozli javob "Vazifa qo'shildi: … Muddati: …".
3. Ovozli xabar: "Indinga bankka borish" → ovozli tasdiq. **Agar transkripsiya xatosi bo'lsa** (`ogg` formati qabul qilinmasa yoki o'zbekcha tanilmasa) — logdagi xatoni o'qib, sabab bo'yicha qaror: `STT_MODEL`ni `openai/whisper-large-v3`ga almashtirish yoki ovozni `mp3`ga o'girish (bu yangi kutubxona/ffmpeg talab qiladi — egasidan so'raladi).
4. "Vazifalarim qanday?" → matnli ro'yxat, "✅" va "🔊" tugmalari bilan.
5. "🔊 Ovozda eshitish" → ro'yxat ovozda keladi.
6. "✅ 1. …" → vazifa ro'yxatdan chiqadi.
7. Boshqa Telegram hisobidan botga yozish → javob yo'q.

- [ ] **Step 5: Botni to'xtatish** va natijani egasiga hisobot qilish.

---

### Task 10: GitHub va Render'ga joylash

Egasi bajaradi, ishlab chiquvchi har qadamni oddiy tilda tushuntiradi. Push faqat egasining aniq ruxsati bilan.

- [ ] **Step 1:** GitHub'da yangi bo'sh repo `vazifa-bot` (egasi yaratadi). `.env` push qilinmasligini `git status` bilan tekshirish, keyin `git remote add origin … && git push -u origin main`.
- [ ] **Step 2:** Render → New → Blueprint → `vazifa-bot` repo → `render.yaml` o'qiladi.
- [ ] **Step 3:** Environment: `BOT_TOKEN`, `OWNER_ID`, `OPENROUTER_API_KEY`, `DATABASE_URL` (egasi kiritadi). `WEBHOOK_BASE_URL` shart emas — `RENDER_EXTERNAL_URL` avtomatik.
- [ ] **Step 4:** Deploy logida `Webhook o'rnatildi` va `HTTP server … portda` borligini tekshirish; brauzerda `https://<servis>.onrender.com/health` → `ok`.
- [ ] **Step 5:** UptimeRobot: HTTP(s) monitor, URL `https://<servis>.onrender.com/health`, interval 5 daqiqa.
- [ ] **Step 6:** Lokal bot to'xtatilganini tasdiqlash (bir token bilan polling va webhook bir vaqtda ishlamaydi).

---

### Task 11: Yakuniy sinov

- [ ] **Step 1:** Render'dagi botga Task 9 Step 4 ssenariysining 2, 4, 6-bandlari takrorlanadi.
- [ ] **Step 2:** Ertasi kuni 08:00 (Toshkent) — kunlik hisobot kelganini egasi tasdiqlaydi.
- [ ] **Step 3:** TZ'dagi "Bajarilish holati" bo'limida barcha bloklar ☑ deb belgilanadi.
