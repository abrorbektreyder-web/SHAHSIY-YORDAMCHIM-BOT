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
