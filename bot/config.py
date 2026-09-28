"""Bot konfiguratsiyasi — .env dan o'qiladi."""
from __future__ import annotations

import hashlib
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
    database_url: str
    openrouter_api_key: str = ""
    groq_api_key: str = ""
    llm_provider: str = "openrouter"
    llm_model: str = ""
    stt_provider: str = "openrouter"
    db_schema: str = "vazifa"
    mode: str = "polling"
    webhook_base_url: str = ""
    webhook_secret: str = ""
    port: int = 8080


Getter = Callable[[str], str]

MODES = ("polling", "webhook")
PROVIDER_KEYS = {"openrouter": "OPENROUTER_API_KEY", "groq": "GROQ_API_KEY"}
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
    # Render generateValue base64 beradi ("=", "+", "/" bilan), Telegram esa
    # secret_token'da faqat A-Z a-z 0-9 _ - ni qabul qiladi. Hex xesh har doim mos.
    raw_secret = get("WEBHOOK_SECRET")
    secret = hashlib.sha256(raw_secret.encode()).hexdigest() if raw_secret else ""
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

    providers = {}
    for key in ("LLM_PROVIDER", "STT_PROVIDER"):
        providers[key] = (get(key) or "openrouter").lower()
        if providers[key] not in PROVIDER_KEYS:
            raise ConfigError(
                f"{key} faqat {' yoki '.join(PROVIDER_KEYS)} bo'lishi mumkin, keldi: {providers[key]!r}"
            )
    # Tanlangan provayderlarning kaliti majburiy; OpenRouter kaliti bo'lmasa
    # bot faqat ovozli javobni o'chiradi.
    for provider in set(providers.values()):
        _require(get, PROVIDER_KEYS[provider])

    return Config(
        bot_token=_require(get, "BOT_TOKEN"),
        owner_id=_require_int(get, "OWNER_ID"),
        database_url=_require(get, "DATABASE_URL"),
        openrouter_api_key=get("OPENROUTER_API_KEY"),
        groq_api_key=get("GROQ_API_KEY"),
        llm_provider=providers["LLM_PROVIDER"],
        llm_model=get("LLM_MODEL"),
        stt_provider=providers["STT_PROVIDER"],
        db_schema=schema,
        mode=mode,
        webhook_base_url=base_url,
        webhook_secret=secret,
        port=port,
    )
