import re

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


def test_render_base64_secret_becomes_telegram_safe(tmp_path):
    # Render generateValue namunasi: base64, "=" bilan tugaydi, "+" va "/" bo'lishi mumkin.
    env = write_env(tmp_path, {
        **BASE,
        "MODE": "webhook",
        "RENDER_EXTERNAL_URL": "https://vazifa-bot.onrender.com",
        "WEBHOOK_SECRET": "B0jr+hAP/Y7pg92AN0c9MN4yecczLMdwnx4OkA1KFUk=",
    })
    first = load_config(env).webhook_secret
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,256}", first)
    assert load_config(env).webhook_secret == first


def test_bad_schema_rejected(tmp_path):
    with pytest.raises(ConfigError, match="DB_SCHEMA"):
        load_config(write_env(tmp_path, {**BASE, "DB_SCHEMA": "x;drop"}))
