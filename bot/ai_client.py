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
        title = _text(data.get("title"))
        if not title:
            return Intent("unknown")
        return Intent("add_task", title, _parse_due(data.get("due_at")), "")
    if kind == "chat":
        reply = _text(data.get("reply"))
        return Intent("chat", reply=reply) if reply else Intent("unknown")
    return Intent(kind)


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


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
        try:
            text = _text(resp.json().get("text"))
        except (AttributeError, ValueError) as exc:
            raise AIError(f"transkripsiya javobi kutilmagan shaklda: {resp.text[:200]}") from exc
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
