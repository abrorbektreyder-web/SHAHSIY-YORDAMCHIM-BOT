import base64
import json
from datetime import date, datetime

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
    parse_ranking,
)
from bot.booking import BookingRequest
from bot.scheduler import TASHKENT
from bot.search import SearchResult

NOW = datetime(2026, 9, 28, 19, 0, tzinfo=TASHKENT)
DUE = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)


def client_with(handler):
    return AIClient(openrouter_key="sk-test", http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def groq_client_with(handler, **kwargs):
    return AIClient(
        groq_key="gsk-test",
        llm_provider="groq",
        stt_provider="groq",
        http=httpx.AsyncClient(transport=httpx.MockTransport(handler)),
        **kwargs,
    )


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


def test_parse_search_intent():
    raw = '{"intent":"search","category":"hotel","query":"arzon mehmonxona","title":"Arzon mehmonxona","place":"Andijon"}'
    assert parse_intent(raw) == Intent(
        "search", title="Arzon mehmonxona", category="hotel", query="arzon mehmonxona", place="Andijon"
    )


def test_parse_search_defaults():
    intent = parse_intent('{"intent":"search","category":"space","query":"Yosin surasi","place":""}')
    assert intent == Intent("search", title="Yosin surasi", category="general", query="Yosin surasi", place=None)
    assert parse_intent('{"intent":"search","query":""}').kind == "unknown"


def test_parse_ranking_filters_bad_items():
    raw = '{"items":[{"n":3,"note":" Eng arzon "},{"n":3,"note":"takror"},{"n":9},{"n":true},{"n":1}]}'
    assert parse_ranking(raw, 3) == [(2, "Eng arzon"), (0, "")]
    assert parse_ranking("buzuq", 3) == []


async def test_rank_results_sends_numbered_results():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return chat_response('{"items":[{"n":2,"note":"To\'g\'ridan-to\'g\'ri reys"}]}')

    results = [SearchResult("A", "https://a.com", "aaa"), SearchResult("B", "https://b.com", "bbb")]
    assert await groq_client_with(handler).rank_results("Istanbul bilet", results) == [(1, "To'g'ridan-to'g'ri reys")]
    user = seen["body"]["messages"][1]["content"]
    assert "Istanbul bilet" in user and "[1] A" in user and "[2] B" in user and "https://b.com" in user
    assert seen["body"]["response_format"] == {"type": "json_object"}


def test_parse_list_filter():
    assert parse_intent('{"intent":"list_tasks","filter":"done"}') == Intent("list_tasks", filter="done")
    assert parse_intent('{"intent":"list_tasks","filter":"weird"}') == Intent("list_tasks")


def test_parse_strips_think_block():
    raw = '<think>foydalanuvchi ro\'yxat so\'rayapti</think>\n{"intent":"list_tasks"}'
    assert parse_intent(raw) == Intent("list_tasks")


def test_parse_non_string_fields_are_unknown():
    assert parse_intent('{"intent":"add_task","title":123}').kind == "unknown"
    assert parse_intent('{"intent":"chat","reply":{"a":1}}').kind == "unknown"


async def test_transcribe_non_json_or_wrong_shape_raises_aierror():
    not_json = client_with(lambda r: httpx.Response(200, text="<html>oops</html>"))
    with pytest.raises(AIError):
        await not_json.transcribe(b"x")
    a_list = client_with(lambda r: httpx.Response(200, json=["text"]))
    with pytest.raises(AIError):
        await a_list.transcribe(b"x")


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


# --- Groq ---

async def test_groq_transcribe_uploads_ogg_to_whisper():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["type"] = request.headers["Content-Type"]
        seen["body"] = request.read()
        return httpx.Response(200, json={"text": " Indinga bankka borish "})

    assert await groq_client_with(handler).transcribe(b"OGGDATA") == "Indinga bankka borish"
    assert seen["url"] == "https://api.groq.com/openai/v1/audio/transcriptions"
    assert seen["auth"] == "Bearer gsk-test"
    assert seen["type"].startswith("multipart/form-data")
    body = seen["body"]
    assert b'name="model"\r\n\r\nwhisper-large-v3\r\n' in body
    assert b'name="language"\r\n\r\nuz\r\n' in body
    # Whisper'ga o'zbekcha namuna: imlo va so'z tanlashni yaxshilaydi.
    assert b'name="prompt"\r\n\r\n' in body
    assert "shifokorga".encode() in body
    assert b'filename="voice.ogg"' in body
    assert b"OGGDATA" in body


async def test_groq_understand_uses_groq_and_default_qwen():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return chat_response('{"intent":"list_tasks"}')

    assert await groq_client_with(handler).understand("ro'yxat", NOW) == Intent("list_tasks")
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer gsk-test"
    assert seen["body"]["model"] == "qwen/qwen3.8-27b"
    assert seen["body"]["response_format"] == {"type": "json_object"}
    # Ovozdan kelgan matndagi eshitish xatolarini tuzatish ko'rsatmasi.
    assert "speech recognition" in seen["body"]["messages"][0]["content"]
    # Internet kerak bo'lgan so'rovlarda ma'lumot o'ylab topmaslik ko'rsatmasi.
    assert "Never invent" in seen["body"]["messages"][0]["content"]


async def test_llm_model_override_is_sent():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return chat_response('{"intent":"list_tasks"}')

    await groq_client_with(handler, llm_model="openai/gpt-oss-20b").understand("x", NOW)
    assert seen["body"]["model"] == "openai/gpt-oss-20b"


async def test_speak_disabled_without_openrouter_key_makes_no_request():
    def handler(request):
        raise AssertionError("tarmoqqa so'rov ketmasligi kerak")

    ai = groq_client_with(handler)
    assert ai.can_speak is False
    with pytest.raises(AIError):
        await ai.speak("salom")
    assert client_with(handler).can_speak is True


async def test_rate_limit_is_retried_once_when_wait_is_short():
    calls = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, headers={"retry-after": "0"}, text="rate limit")
        return chat_response('{"intent":"list_tasks"}')

    assert await groq_client_with(handler).understand("x", NOW) == Intent("list_tasks")
    assert len(calls) == 2


async def test_rate_limit_with_long_wait_is_not_retried():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(429, headers={"retry-after": "30"}, text="rate limit")

    with pytest.raises(AIError, match="429"):
        await groq_client_with(handler).understand("x", NOW)
    assert len(calls) == 1


async def test_llm_requests_cap_output_tokens():
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return chat_response('{"intent":"list_tasks","items":[]}')

    ai = groq_client_with(handler)
    await ai.understand("x", NOW)
    await ai.rank_results("x", [SearchResult("A", "https://a.com")])
    assert all(0 < body["max_tokens"] <= 400 for body in bodies)


async def test_understand_sends_conversation_history_before_new_message():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return chat_response('{"intent":"list_tasks"}')

    history = [
        {"role": "user", "content": "Toshkent Madina 15-oktabr avia chipta qidir"},
        {"role": "assistant", "content": "Toshkent–Madina chiptalari: Aviasales, Google Travel"},
    ]
    await groq_client_with(handler).understand("O'zing qidir va eng arzonini top", NOW, history)
    messages = seen["body"]["messages"]
    # Bot javoblari JSON emas — ularni assistant navbati qilib bersak, model JSON o'rniga matn yozadi
    # (Groq: json_validate_failed). Shuning uchun suhbat faqat kontekst sifatida user xabariga qo'shiladi.
    assert [m["role"] for m in messages] == ["system", "user"]
    user = messages[1]["content"]
    assert "Foydalanuvchi: Toshkent Madina 15-oktabr avia chipta qidir" in user
    assert "Bot: Toshkent–Madina chiptalari: Aviasales, Google Travel" in user
    assert user.endswith("Yangi xabar: O'zing qidir va eng arzonini top")


async def test_understand_without_history_sends_plain_message():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return chat_response('{"intent":"list_tasks"}')

    await groq_client_with(handler).understand("salom", NOW)
    assert seen["body"]["messages"][1] == {"role": "user", "content": "salom"}


async def test_prompts_never_deny_search_and_handle_cheapest():
    seen = []

    def handler(request):
        seen.append(json.loads(request.content)["messages"][0]["content"])
        return chat_response('{"intent":"list_tasks","items":[]}')

    ai = groq_client_with(handler)
    await ai.understand("x", NOW)
    await ai.rank_results("x", [SearchResult("A", "https://a.com")])
    system, rank = seen
    assert "never say that you cannot search" in system
    assert "garbled" in system
    assert "cheapest" in rank


def test_parse_book_intent():
    raw = (
        '{"intent":"book","category":"hotel","title":"CHINOR HOTEL","place":"Andijon",'
        '"checkin":"2026-10-30","checkout":null,"guests":2,"rooms":1,"room_type":"delux",'
        '"name_en":"Chinor Hotel","destination_en":"Andijan","stars":null}'
    )
    assert parse_intent(raw) == Intent("book", booking=BookingRequest(
        name="CHINOR HOTEL", city="Andijon", category="hotel",
        checkin=date(2026, 10, 30), checkout=None, guests=2, rooms=1, room_type="delux",
        name_en="Chinor Hotel", destination_en="Andijan", stars=None,
    ))


def test_parse_book_generic_hotel_with_stars():
    raw = ('{"intent":"book","category":"hotel","title":"Dubaydagi 5 yulduzli mehmonxona","place":"Dubay",'
           '"name_en":"","destination_en":"Dubai","stars":5}')
    booking = parse_intent(raw).booking
    assert booking.name_en == "" and booking.destination_en == "Dubai" and booking.stars == 5
    assert parse_intent(raw.replace('"stars":5', '"stars":9')).booking.stars is None


def test_parse_book_defaults_and_restaurant():
    raw = '{"intent":"book","category":"cafe","title":"Rayhon","guests":"ko\'p","rooms":0,"checkin":"ertaga","time":"19:00"}'
    intent = parse_intent(raw)
    assert intent.booking == BookingRequest(name="Rayhon", category="hotel", guests=1, rooms=1, time="19:00")
    restaurant = parse_intent('{"intent":"book","category":"restaurant","title":"Rayhon","guests":4}')
    assert restaurant.booking.category == "restaurant" and restaurant.booking.guests == 4
    assert parse_intent('{"intent":"book","title":""}').kind == "unknown"


async def test_system_prompt_describes_booking():
    seen = {}

    def handler(request):
        seen["system"] = json.loads(request.content)["messages"][0]["content"]
        return chat_response('{"intent":"list_tasks"}')

    await groq_client_with(handler).understand("x", NOW)
    assert '"book"' in seen["system"] and "never pays" in seen["system"]
    assert "destination_en" in seen["system"] and "never guess dates" in seen["system"]
    assert "never pick one from the bot's results" in seen["system"]
