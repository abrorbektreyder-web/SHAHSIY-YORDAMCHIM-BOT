"""Uchta AI xizmati: nutq→matn, matnni tushunish (OpenRouter yoki Groq), matn→nutq (OpenRouter)."""
from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import datetime

import httpx

from bot.models import REPORT_FILTERS
from bot.scheduler import TASHKENT
from content import uz

BASE_URLS = {
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
}
STT_MODEL = "google/gemini-3.5-transcribe"
GROQ_STT_MODEL = "whisper-large-v3"
LLM_MODEL = "google/gemini-3.5-flash-lite"
GROQ_LLM_MODEL = "qwen/qwen3.8-27b"
DEFAULT_LLM_MODELS = {"openrouter": LLM_MODEL, "groq": GROQ_LLM_MODEL}
TTS_MODEL = "google/gemini-3.8-flash-tts"
TTS_VOICE = "Kore"

INTENTS = ("add_task", "list_tasks", "speak_report", "chat", "unknown")
_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$")
# Fikrlovchi modellar (masalan Groq'dagi Qwen) javob oldiga <think> blok qo'yishi mumkin.
_THINK = re.compile(r"<think>.*?</think>", re.DOTALL)


class AIError(Exception):
    """OpenRouter javob bermadi yoki kutilmagan javob qaytardi."""


@dataclass(frozen=True)
class Intent:
    kind: str
    title: str | None = None
    due_at: datetime | None = None
    reply: str = ""
    filter: str = "all"


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
        data = json.loads(_FENCE.sub("", _THINK.sub("", raw).strip()))
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
    if kind == "list_tasks":
        filter_ = data.get("filter")
        return Intent("list_tasks", filter=filter_ if filter_ in REPORT_FILTERS else "all")
    return Intent(kind)


def _text(value: object) -> str:
    return value.strip() if isinstance(value, str) else ""


class AIClient:
    def __init__(
        self,
        *,
        openrouter_key: str = "",
        groq_key: str = "",
        llm_provider: str = "openrouter",
        llm_model: str = "",
        stt_provider: str = "openrouter",
        http: httpx.AsyncClient | None = None,
    ) -> None:
        self._http = http or httpx.AsyncClient(timeout=60)
        self._keys = {"openrouter": openrouter_key, "groq": groq_key}
        self._llm_provider = llm_provider
        self._llm_model = llm_model or DEFAULT_LLM_MODELS[llm_provider]
        self._stt_provider = stt_provider

    @property
    def can_speak(self) -> bool:
        # Matn→nutq faqat OpenRouter'da (pullik); kalit bo'lmasa javoblar matnda qoladi.
        return bool(self._keys["openrouter"])

    async def _post(self, provider: str, path: str, **kwargs) -> httpx.Response:
        key = self._keys[provider]
        if not key:
            raise AIError(f"{provider}: API kaliti berilmagan")
        try:
            resp = await self._http.post(
                f"{BASE_URLS[provider]}{path}",
                headers={"Authorization": f"Bearer {key}"},
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise AIError(f"{path}: tarmoq xatosi: {exc}") from exc
        if resp.status_code != 200:
            raise AIError(f"{path}: HTTP {resp.status_code}: {resp.text[:200]}")
        return resp

    async def transcribe(self, audio: bytes, fmt: str = "ogg") -> str:
        if self._stt_provider == "groq":
            resp = await self._post(
                "groq",
                "/audio/transcriptions",
                data={
                    "model": GROQ_STT_MODEL,
                    "language": "uz",
                    "prompt": uz.STT_PROMPT,
                    "response_format": "json",
                },
                files={"file": (f"voice.{fmt}", audio)},
            )
        else:
            resp = await self._post(
                "openrouter",
                "/audio/transcriptions",
                json={
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
            self._llm_provider,
            "/chat/completions",
            json={
                "model": self._llm_model,
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
            "openrouter",
            "/audio/speech",
            json={"model": TTS_MODEL, "input": text, "voice": TTS_VOICE, "response_format": "mp3"},
        )
        if not resp.content:
            raise AIError("ovoz bo'sh qaytdi")
        return resp.content

    async def close(self) -> None:
        await self._http.aclose()
