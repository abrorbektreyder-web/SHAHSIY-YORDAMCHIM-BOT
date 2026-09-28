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
