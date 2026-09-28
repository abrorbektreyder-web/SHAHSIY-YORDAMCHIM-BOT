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


GROQ = {
    "BOT_TOKEN": "123:abc",
    "OWNER_ID": "42",
    "DATABASE_URL": "postgresql://u:p@h:5432/db",
    "GROQ_API_KEY": "gsk-test",
    "LLM_PROVIDER": "groq",
    "STT_PROVIDER": "groq",
}


def test_groq_only_setup_needs_no_openrouter_key(tmp_path):
    cfg = load_config(write_env(tmp_path, GROQ))
    assert cfg.groq_api_key == "gsk-test"
    assert cfg.openrouter_api_key == ""
    assert cfg.llm_provider == "groq"
    assert cfg.stt_provider == "groq"
    assert cfg.llm_model == ""


def test_tavily_key_is_optional(tmp_path):
    assert load_config(write_env(tmp_path, GROQ)).tavily_api_key == ""
    cfg = load_config(write_env(tmp_path, {**GROQ, "TAVILY_API_KEY": "tvly-x"}))
    assert cfg.tavily_api_key == "tvly-x"


def test_llm_model_override(tmp_path):
    cfg = load_config(write_env(tmp_path, {**GROQ, "LLM_MODEL": "openai/gpt-oss-20b"}))
    assert cfg.llm_model == "openai/gpt-oss-20b"


def test_groq_provider_requires_groq_key(tmp_path):
    values = {k: v for k, v in GROQ.items() if k != "GROQ_API_KEY"}
    with pytest.raises(ConfigError, match="GROQ_API_KEY"):
        load_config(write_env(tmp_path, values))


def test_unknown_provider_rejected(tmp_path):
    with pytest.raises(ConfigError, match="LLM_PROVIDER"):
        load_config(write_env(tmp_path, {**GROQ, "LLM_PROVIDER": "openai"}))


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
