# 2-bosqich: Internetdan qidirish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bot egasining so'roviga ko'ra Tavily orqali internetdan qidiradi (aviabilet, mehmonxona, restoran, YouTube, umumiy ma'lumot) va 3 ta eng mos natijani havola bilan ko'rsatadi; shahar kerak bo'lsa so'raydi yoki joylashuvdan aniqlaydi.

**Architecture:** `TavilyClient` (search.py) va `Geocoder` (geo.py) — tashqi xizmatlar uchun yupqa httpx mijozlari. AI `search` niyatini aniqlaydi va natijalarni saralaydi (`rank_results`); `logic.run_search` ularni birlashtirib, `views.format_search_pages` bilan sahifalarga bo'ladi. Handlerlar kutilayotgan qidiruvni va "Yana ko'rsat" sahifasini xotirada ushlaydi (bitta egasi, bitta jarayon).

**Tech Stack:** Python 3.10+/3.12, aiogram 3, httpx, Tavily Search API, OpenStreetMap Nominatim, Groq (Qwen 3.8).

**Spec:** `docs/superpowers/specs/2026-09-28-bosqich2-qidiruv-design.md`

## Global Constraints

- Yangi kutubxona yo'q; faqat mavjud `httpx`, `aiogram`.
- Havola va sarlavhalar faqat Tavily natijasidan; AI faqat tartib (`n`) va izoh qaytaradi.
- Tavily: `POST https://api.tavily.com/search`, `Authorization: Bearer <key>`, `search_depth: "basic"`, `max_results: 6`; YouTube uchun `include_domains: ["youtube.com"]`.
- Nominatim: `GET https://nominatim.openstreetmap.org/reverse`, `format=jsonv2`, `zoom=8` (zoom=10 da Toshkentda OSM xatosi — mahalla "shahar" deb qaytadi), `accept-language=uz`, `User-Agent` majburiy.
- Sahifada 3 ta natija; 2-sahifa "Yana ko'rsat" bilan.
- Shahar kerak toifalar: `hotel`, `restaurant`. Kutilayotgan qidiruvga ≤3 so'zli matn — shahar nomi; uzunroq matn — kutish bekor.
- Barcha foydalanuvchi matnlari `content/uz.py`da; HTML matnda `escape(..., quote=False)`, atributda `escape(url)`.
- `TAVILY_API_KEY` ixtiyoriy: bo'lsa qidiruv yoqiladi.
- Commit — egasi ruxsat bergan (lokal), push — alohida ruxsat bilan.

## File Structure

- Create: `bot/search.py`, `bot/geo.py`, `tests/test_search.py`, `tests/test_geo.py`
- Modify: `bot/config.py`, `bot/models.py`, `bot/ai_client.py`, `bot/views.py`, `bot/logic.py`, `bot/keyboards.py`, `bot/handlers.py`, `bot/main.py`, `content/uz.py`, `render.yaml`, `.env.example`
- Tests modify: `tests/test_config.py`, `tests/test_ai_client.py`, `tests/test_views.py`, `tests/test_logic.py`, `tests/test_keyboards.py`

---

### Task 2.1: Tavily qidiruv moduli va sozlama

**Files:** Create `bot/search.py`, `tests/test_search.py`; Modify `bot/config.py`, `tests/test_config.py`

**Interfaces — Produces:** `SearchResult(title: str, url: str, content: str = "")` (frozen), `SearchError(Exception)`, `TavilyClient(api_key: str, http: httpx.AsyncClient | None = None)` → `async search(query: str, category: str, max_results: int = 6) -> list[SearchResult]`, `async close()`; `Config.tavily_api_key: str = ""`.

- [ ] **Step 1: Failing testlar**

`tests/test_search.py`:
```python
import json

import httpx
import pytest

from bot.search import SearchError, SearchResult, TavilyClient


def client_with(handler):
    return TavilyClient("tvly-test", http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_search_sends_query_and_parses_results():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"results": [
            {"title": " KAYAK: Tashkent–Istanbul ", "url": "https://www.kayak.com/x", "content": " $184 dan "},
            {"title": "URLsiz", "content": "tashlanadi"},
            {"title": "Yomon havola", "url": "javascript:alert(1)"},
            {"title": "Matnsiz", "url": "https://example.com"},
        ]})

    results = await client_with(handler).search("Tashkent Istanbul flights", "flight")
    assert results == [
        SearchResult("KAYAK: Tashkent–Istanbul", "https://www.kayak.com/x", "$184 dan"),
        SearchResult("Matnsiz", "https://example.com", ""),
    ]
    assert seen["url"] == "https://api.tavily.com/search"
    assert seen["auth"] == "Bearer tvly-test"
    assert seen["body"] == {"query": "Tashkent Istanbul flights", "search_depth": "basic", "max_results": 6}


async def test_youtube_search_is_limited_to_youtube():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"results": []})

    assert await client_with(handler).search("Yosin surasi", "youtube") == []
    assert seen["body"]["include_domains"] == ["youtube.com"]


async def test_http_error_raises():
    with pytest.raises(SearchError, match="429"):
        await client_with(lambda r: httpx.Response(429, text="limit")).search("x", "general")


async def test_network_error_raises():
    def handler(request):
        raise httpx.ConnectError("down")

    with pytest.raises(SearchError, match="tarmoq"):
        await client_with(handler).search("x", "general")


async def test_bad_json_raises():
    with pytest.raises(SearchError):
        await client_with(lambda r: httpx.Response(200, text="<html>")).search("x", "general")
```

`tests/test_config.py` ga qo'shiladi:
```python
def test_tavily_key_is_optional(tmp_path):
    assert load_config(write_env(tmp_path, GROQ)).tavily_api_key == ""
    cfg = load_config(write_env(tmp_path, {**GROQ, "TAVILY_API_KEY": "tvly-x"}))
    assert cfg.tavily_api_key == "tvly-x"
```

- [ ] **Step 2:** `.venv/Scripts/python -m pytest tests/test_search.py tests/test_config.py -q` → FAIL (`No module named 'bot.search'`, `tavily_api_key`)

- [ ] **Step 3: `bot/search.py`**
```python
"""Tavily orqali internetdan qidirish."""
from __future__ import annotations

from dataclasses import dataclass

import httpx

TAVILY_URL = "https://api.tavily.com/search"
YOUTUBE_DOMAINS = ["youtube.com"]


class SearchError(Exception):
    """Qidiruv xizmati javob bermadi yoki kutilmagan javob qaytardi."""


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    content: str = ""


class TavilyClient:
    def __init__(self, api_key: str, http: httpx.AsyncClient | None = None) -> None:
        self._http = http or httpx.AsyncClient(timeout=30)
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def search(self, query: str, category: str, max_results: int = 6) -> list[SearchResult]:
        payload: dict = {"query": query, "search_depth": "basic", "max_results": max_results}
        if category == "youtube":
            payload["include_domains"] = YOUTUBE_DOMAINS
        try:
            resp = await self._http.post(TAVILY_URL, json=payload, headers=self._headers)
        except httpx.HTTPError as exc:
            raise SearchError(f"tarmoq xatosi: {exc}") from exc
        if resp.status_code != 200:
            raise SearchError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            items = resp.json()["results"]
        except (KeyError, TypeError, ValueError) as exc:
            raise SearchError(f"kutilmagan javob: {resp.text[:200]}") from exc

        results = []
        for item in items if isinstance(items, list) else []:
            if not isinstance(item, dict):
                continue
            title, url, content = item.get("title"), item.get("url"), item.get("content")
            # Havola Telegram HTML'ga qo'yiladi — faqat http(s).
            if isinstance(title, str) and isinstance(url, str) and url.startswith(("http://", "https://")):
                results.append(
                    SearchResult(title.strip(), url, content.strip() if isinstance(content, str) else "")
                )
        return results

    async def close(self) -> None:
        await self._http.aclose()
```

`bot/config.py`: `Config`ga `tavily_api_key: str = ""` (openrouter_api_key'dan keyin), `load_config` → `tavily_api_key=get("TAVILY_API_KEY")`.

- [ ] **Step 4:** testlar → PASS. **Step 5:** commit `feat: Tavily qidiruv moduli`.

---

### Task 2.2: Joylashuvdan shahar aniqlash

**Files:** Create `bot/geo.py`, `tests/test_geo.py`

**Interfaces — Produces:** `Geocoder(http: httpx.AsyncClient | None = None)` → `async city(lat: float, lon: float) -> str | None`, `async close()`.

- [ ] **Step 1: Failing test** `tests/test_geo.py`:
```python
import httpx

from bot.geo import Geocoder


def geo_with(handler):
    return Geocoder(http=httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_city_from_coordinates_with_user_agent():
    seen = {}

    def handler(request):
        seen["url"] = request.url
        seen["ua"] = request.headers["User-Agent"]
        return httpx.Response(200, json={"address": {"city": "Andijon", "state": "Andijon viloyati"}})

    assert await geo_with(handler).city(40.78, 72.34) == "Andijon"
    assert seen["url"].host == "nominatim.openstreetmap.org"
    params = dict(seen["url"].params)
    assert params["lat"] == "40.78" and params["lon"] == "72.34"
    assert params["accept-language"] == "uz" and params["format"] == "jsonv2"
    assert "shahsiy-yordamchim-bot" in seen["ua"]


async def test_falls_back_to_town_then_state():
    town = geo_with(lambda r: httpx.Response(200, json={"address": {"town": "Asaka"}}))
    assert await town.city(1, 2) == "Asaka"
    state = geo_with(lambda r: httpx.Response(200, json={"address": {"state": "Andijon viloyati"}}))
    assert await state.city(1, 2) == "Andijon viloyati"


async def test_errors_return_none():
    assert await geo_with(lambda r: httpx.Response(500)).city(1, 2) is None
    assert await geo_with(lambda r: httpx.Response(200, json={"error": "x"})).city(1, 2) is None
    assert await geo_with(lambda r: httpx.Response(200, text="<html>")).city(1, 2) is None

    def down(request):
        raise httpx.ConnectError("down")

    assert await geo_with(down).city(1, 2) is None
```

- [ ] **Step 2:** FAIL (`No module named 'bot.geo'`)

- [ ] **Step 3: `bot/geo.py`**
```python
"""Koordinatalardan shahar nomini aniqlash (OpenStreetMap Nominatim)."""
from __future__ import annotations

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/reverse"
# Nominatim foydalanish qoidasi ilovani tanituvchi User-Agent talab qiladi.
USER_AGENT = "shahsiy-yordamchim-bot/1.0 (personal Telegram assistant)"
PLACE_KEYS = ("city", "town", "village", "county", "state")


class Geocoder:
    def __init__(self, http: httpx.AsyncClient | None = None) -> None:
        self._http = http or httpx.AsyncClient(timeout=15)

    async def city(self, lat: float, lon: float) -> str | None:
        try:
            resp = await self._http.get(
                NOMINATIM_URL,
                params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 10, "accept-language": "uz"},
                headers={"User-Agent": USER_AGENT},
            )
            address = resp.json().get("address") if resp.status_code == 200 else None
        except (httpx.HTTPError, ValueError, AttributeError):
            return None
        if not isinstance(address, dict):
            return None
        for key in PLACE_KEYS:
            value = address.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    async def close(self) -> None:
        await self._http.aclose()
```

- [ ] **Step 4:** PASS. **Step 5:** commit `feat: joylashuvdan shahar aniqlash`.

---

### Task 2.3: AI — qidiruv niyati va natijalarni saralash

**Files:** Modify `bot/models.py`, `bot/ai_client.py`, `content/uz.py`, `tests/test_ai_client.py`

**Interfaces — Consumes:** `SearchResult`. **Produces:** `models.SEARCH_CATEGORIES = ("flight", "hotel", "restaurant", "youtube", "general")`, `models.PLACE_CATEGORIES = ("hotel", "restaurant")`; `Intent` yangi maydonlari `category: str = "general"`, `query: str = ""`, `place: str | None = None` (`title` qidiruvda — o'zbekcha qisqa sarlavha); `parse_ranking(raw: str, count: int) -> list[tuple[int, str]]` (0 dan boshlanadigan indekslar); `AIClient.rank_results(request: str, results: list[SearchResult]) -> list[tuple[int, str]]`; `uz.RANK_PROMPT`.

- [ ] **Step 1: Failing testlar** (`tests/test_ai_client.py` ga):
```python
from bot.ai_client import parse_ranking
from bot.search import SearchResult


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
```

- [ ] **Step 2:** FAIL (`cannot import name 'parse_ranking'`)

- [ ] **Step 3: Kod**

`bot/models.py` ga:
```python
SEARCH_CATEGORIES = ("flight", "hotel", "restaurant", "youtube", "general")
# Bu toifalarda shahar aytilmasa, bot so'raydi.
PLACE_CATEGORIES = ("hotel", "restaurant")
```

`bot/ai_client.py`:
- `INTENTS` ga `"search"`; `Intent` ga `category: str = "general"`, `query: str = ""`, `place: str | None = None`.
- JSON tozalashni yordamchiga chiqarish va `parse_intent`da ishlatish:
```python
def _load_json(raw: str) -> object:
    try:
        return json.loads(_FENCE.sub("", _THINK.sub("", raw).strip()))
    except json.JSONDecodeError:
        return None
```
- `parse_intent` ichida `search` bo'limi:
```python
    if kind == "search":
        query = _text(data.get("query"))
        if not query:
            return Intent("unknown")
        category = data.get("category")
        return Intent(
            "search",
            title=_text(data.get("title")) or query,
            category=category if category in SEARCH_CATEGORIES else "general",
            query=query,
            place=_text(data.get("place")) or None,
        )
```
- saralash:
```python
def parse_ranking(raw: str, count: int) -> list[tuple[int, str]]:
    data = _load_json(raw)
    items = data.get("items") if isinstance(data, dict) else None
    ranking, seen = [], set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        n = item.get("n")
        if isinstance(n, int) and not isinstance(n, bool) and 1 <= n <= count and n not in seen:
            seen.add(n)
            ranking.append((n - 1, _text(item.get("note"))))
    return ranking
```
`AIClient`ga:
```python
    async def rank_results(self, request: str, results: list[SearchResult]) -> list[tuple[int, str]]:
        numbered = "\n\n".join(
            f"[{i}] {r.title}\n{r.url}\n{r.content[:400]}" for i, r in enumerate(results, start=1)
        )
        resp = await self._post(
            self._llm_provider,
            "/chat/completions",
            json={
                "model": self._llm_model,
                "messages": [
                    {"role": "system", "content": uz.RANK_PROMPT},
                    {"role": "user", "content": f"So'rov: {request}\n\nNatijalar:\n{numbered}"},
                ],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
        )
        return parse_ranking(self._content(resp), len(results))
```
`understand` va `rank_results` javob matnini olishni `_content(resp)` yordamchisiga chiqarish (hozirgi `try: raw = resp.json()["choices"][0]["message"]["content"] ...` bloki).

`content/uz.py`:
- `SYSTEM_PROMPT` JSON namunasiga `"category"`, `"query"`, `"place"` qo'shiladi; yangi niyat:
```
- "search": the user asks to find something on the internet: flights ("flight"), hotels ("hotel"), restaurants or cafes ("restaurant"), YouTube videos, films, songs or Quran surahs ("youtube"), or any facts or news ("general"). "category" = one of those. "query" = a concise web search query with all details (route, real dates resolved from the current date, class, passengers, price level, city if given). "title" = short Uzbek Latin description of what is searched. "place" = the city if the user named one, otherwise null (never guess).
```
- `chat` qoidasi: qidirish so'rovlari `search`; band qilish/sotib olish so'ralsa — hali mavjud emasligini aytib, qidirib berishni taklif qiladi ("Never invent ..." jumlasi saqlanadi).
- oxirgi qoida: `For intents other than "search", "category", "query" and "place" = null.`
- `RANK_PROMPT`:
```python
RANK_PROMPT = """You rank web search results for a personal assistant bot. The user writes in Uzbek.
Pick up to 6 results that best match the request, best first; skip irrelevant ones.
Answer ONLY with JSON: {"items": [{"n": <result number>, "note": "<1-2 short sentences in Uzbek Latin>"}]}
The note says what the result offers. Mention prices, ratings, dates or addresses ONLY if they appear in the result text. Never invent facts."""
```

- [ ] **Step 4:** PASS (barcha `test_ai_client.py`). **Step 5:** commit `feat: AI qidiruv niyati va natijalarni saralash`.

---

### Task 2.4: Natijalar ko'rinishi

**Files:** Modify `bot/views.py`, `tests/test_views.py`

**Interfaces — Produces:** `SEARCH_ICONS`, `PER_PAGE = 3`, `format_search_pages(category: str, title: str, items: list[tuple[SearchResult, str]], per_page: int = PER_PAGE) -> list[str]`.

- [ ] **Step 1: Failing test**
```python
from bot.search import SearchResult


def test_search_pages_numbering_links_and_escaping():
    items = [
        (SearchResult("KAYAK <arzon>", "https://www.kayak.com/a?x=1&y=2"), "184$ dan, to'g'ridan-to'g'ri"),
        (SearchResult("Google Flights", "https://google.com/travel"), ""),
        (SearchResult("Expedia", "https://expedia.com/f"), "Izoh"),
        (SearchResult("Aviasales", "https://aviasales.uz/r"), "To'rtinchi"),
    ]
    pages = views.format_search_pages("flight", "Toshkent → Istanbul", items)
    assert len(pages) == 2
    assert pages[0] == (
        "✈️ <b>Toshkent → Istanbul</b>\n"
        "\n"
        "1. <b>KAYAK &lt;arzon&gt;</b>\n"
        "184$ dan, to'g'ridan-to'g'ri\n"
        '🔗 <a href="https://www.kayak.com/a?x=1&amp;y=2">kayak.com</a>\n'
        "\n"
        "2. <b>Google Flights</b>\n"
        '🔗 <a href="https://google.com/travel">google.com</a>\n'
        "\n"
        "3. <b>Expedia</b>\n"
        "Izoh\n"
        '🔗 <a href="https://expedia.com/f">expedia.com</a>'
    )
    assert pages[1].startswith("✈️ <b>Toshkent → Istanbul</b>\n\n4. <b>Aviasales</b>")


def test_search_pages_unknown_category_uses_default_icon():
    pages = views.format_search_pages("x", "Savol", [(SearchResult("A", "https://a.com"), "")])
    assert pages[0].startswith("🔎 <b>Savol</b>")
```

- [ ] **Step 2:** FAIL. **Step 3: Kod** (`bot/views.py`):
```python
from urllib.parse import urlparse

from bot.search import SearchResult

SEARCH_ICONS = {"flight": "✈️", "hotel": "🏨", "restaurant": "🍽", "youtube": "▶️", "general": "🔎"}
PER_PAGE = 3


def _domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def format_search_pages(
    category: str, title: str, items: list[tuple[SearchResult, str]], per_page: int = PER_PAGE
) -> list[str]:
    header = f"{SEARCH_ICONS.get(category, '🔎')} <b>{escape(title, quote=False)}</b>"
    pages = []
    for start in range(0, len(items), per_page):
        lines = [header]
        for n, (result, note) in enumerate(items[start:start + per_page], start=start + 1):
            lines += ["", f"{n}. <b>{escape(result.title, quote=False)}</b>"]
            if note:
                lines.append(escape(note, quote=False))
            lines.append(f'🔗 <a href="{escape(result.url)}">{escape(_domain(result.url), quote=False)}</a>')
        pages.append("\n".join(lines))
    return pages
```

- [ ] **Step 4:** PASS. **Step 5:** commit `feat: qidiruv natijalari ko'rinishi`.

---

### Task 2.5: Bot mantiqi

**Files:** Modify `bot/logic.py`, `content/uz.py`, `tests/test_logic.py`

**Interfaces — Consumes:** `Intent`, `AIError`, `SearchError`, `PLACE_CATEGORIES`, `format_search_pages`. **Produces:** `Reply` yangi maydonlari `more: str = ""`, `pending: Intent | None = None`; `Reply.kind` yangi qiymatlari `"search"`, `"ask_place"`; `looks_like_place(text: str) -> bool`; `async run_search(intent, place: str | None, ai, searcher) -> Reply`; `handle_text(text, ai, store, now, searcher=None)`. `uz`: `SEARCH_DISABLED`, `ASK_PLACE`, `SEARCH_ERROR`, `SEARCH_EMPTY`.

- [ ] **Step 1: Failing testlar** (`tests/test_logic.py` — `FakeAI`ga `ranking`/`rank_error`, yangi `FakeSearcher`):
```python
from bot.ai_client import AIError
from bot.logic import looks_like_place, run_search
from bot.search import SearchError, SearchResult

HOTEL = Intent("search", title="Arzon mehmonxona", category="hotel", query="arzon mehmonxona")
RESULTS = [SearchResult(f"Natija {i}", f"https://r{i}.com", "") for i in range(1, 6)]


class FakeSearcher:
    def __init__(self, results=None, error=False):
        self.results = RESULTS if results is None else results
        self.error = error
        self.calls = []

    async def search(self, query, category, max_results=6):
        self.calls.append((query, category))
        if self.error:
            raise SearchError("down")
        return self.results


async def test_search_disabled_without_searcher():
    reply = await handle_text("mehmonxona top", FakeAI(HOTEL), FakeStore(), NOW)
    assert reply == Reply("text", uz.SEARCH_DISABLED)


async def test_hotel_without_place_asks_for_city():
    searcher = FakeSearcher()
    reply = await handle_text("mehmonxona top", FakeAI(HOTEL), FakeStore(), NOW, searcher)
    assert reply == Reply("ask_place", uz.ASK_PLACE, pending=HOTEL)
    assert searcher.calls == []


async def test_place_from_message_goes_straight_to_search():
    intent = Intent("search", title="Arzon mehmonxona", category="hotel", query="arzon mehmonxona", place="Andijon")
    searcher = FakeSearcher()
    reply = await handle_text("Andijonda mehmonxona", FakeAI(intent), FakeStore(), NOW, searcher)
    assert reply.kind == "search"
    assert searcher.calls == [("arzon mehmonxona Andijon", "hotel")]


async def test_run_search_ranks_and_pages():
    ai = FakeAI(HOTEL, ranking=[(4, "Eng yaxshisi"), (0, ""), (1, ""), (2, "To'rtinchi")])
    reply = await run_search(HOTEL, "Andijon", ai, FakeSearcher())
    assert reply.kind == "search"
    assert reply.text.startswith("🏨 <b>Arzon mehmonxona, Andijon</b>\n\n1. <b>Natija 5</b>\nEng yaxshisi")
    assert "4. <b>Natija 3</b>" in reply.more


async def test_place_not_duplicated_in_query():
    intent = Intent("search", title="T", category="restaurant", query="Andijon kafe")
    searcher = FakeSearcher()
    await run_search(intent, "Andijon", FakeAI(intent, ranking=[]), searcher)
    assert searcher.calls == [("Andijon kafe", "restaurant")]


async def test_ranking_failure_falls_back_to_search_order():
    reply = await run_search(HOTEL, "Andijon", FakeAI(HOTEL, rank_error=True), FakeSearcher())
    assert "1. <b>Natija 1</b>" in reply.text and "2. <b>Natija 2</b>" in reply.text
    assert "4. <b>Natija 4</b>" in reply.more


async def test_search_error_and_empty():
    assert await run_search(HOTEL, "A", FakeAI(HOTEL), FakeSearcher(error=True)) == Reply("text", uz.SEARCH_ERROR)
    assert await run_search(HOTEL, "A", FakeAI(HOTEL), FakeSearcher(results=[])) == Reply("text", uz.SEARCH_EMPTY)


async def test_three_results_have_no_second_page():
    reply = await run_search(HOTEL, None, FakeAI(HOTEL, ranking=[]), FakeSearcher(results=RESULTS[:3]))
    assert reply.more == ""


def test_looks_like_place():
    assert looks_like_place("Andijon")
    assert looks_like_place("  Nyu York shahri ")
    assert not looks_like_place("")
    assert not looks_like_place("ertaga soat 10 da bankka borish")
```
`FakeAI` yangilanadi:
```python
class FakeAI:
    def __init__(self, intent, ranking=None, rank_error=False):
        self.intent = intent
        self.ranking = ranking or []
        self.rank_error = rank_error
        self.seen = []

    async def understand(self, text, now):
        self.seen.append((text, now))
        return self.intent

    async def rank_results(self, request, results):
        if self.rank_error:
            raise AIError("down")
        return self.ranking
```

- [ ] **Step 2:** FAIL. **Step 3: Kod** (`bot/logic.py`):
```python
import logging

from bot.ai_client import AIError, Intent
from bot.models import PLACE_CATEGORIES, Task
from bot.search import SearchError

log = logging.getLogger(__name__)
PLACE_WORD_LIMIT = 3


@dataclass(frozen=True)
class Reply:
    kind: str  # "voice" | "text" | "list" | "list_voice" | "search" | "ask_place"
    text: str = ""
    tasks: list[Task] = field(default_factory=list)  # "list": tugmalar shu tartibda
    more: str = ""  # "search": "Yana ko'rsat" sahifasi
    pending: Intent | None = None  # "ask_place": shahar kutayotgan qidiruv


def looks_like_place(text: str) -> bool:
    """Kutilayotgan qidiruvdan keyingi qisqa matn — shahar nomi deb qabul qilinadi."""
    return 0 < len(text.split()) <= PLACE_WORD_LIMIT


async def run_search(intent: Intent, place: str | None, ai, searcher) -> Reply:
    query, title = intent.query, intent.title or intent.query
    if place:
        if place.lower() not in query.lower():
            query = f"{query} {place}"
        if place.lower() not in title.lower():
            title = f"{title}, {place}"
    try:
        results = await searcher.search(query, intent.category)
    except SearchError as exc:
        log.warning("Qidiruv xatosi: %s", exc)
        return Reply("text", uz.SEARCH_ERROR)
    if not results:
        return Reply("text", uz.SEARCH_EMPTY)
    try:
        ranking = await ai.rank_results(query, results)
    except AIError as exc:
        log.warning("Saralash xatosi, qidiruv tartibi ishlatiladi: %s", exc)
        ranking = []
    if not ranking:
        ranking = [(i, "") for i in range(len(results))]
    pages = views.format_search_pages(intent.category, title, [(results[i], note) for i, note in ranking])
    return Reply("search", pages[0], more=pages[1] if len(pages) > 1 else "")
```
`handle_text(text, ai, store, now, searcher=None)` ga (unknown'dan oldin):
```python
    if intent.kind == "search":
        if searcher is None:
            return Reply("text", uz.SEARCH_DISABLED)
        if intent.category in PLACE_CATEGORIES and not intent.place:
            return Reply("ask_place", uz.ASK_PLACE, pending=intent)
        return await run_search(intent, intent.place, ai, searcher)
```
`content/uz.py` ga:
```python
SEARCH_DISABLED = "Internetdan qidirish hali yoqilmagan."
ASK_PLACE = "Qaysi shaharda qidiray? Shahar nomini yozing yoki pastdagi 📍 tugmani bosing."
SEARCH_ERROR = "Qidiruvda xato bo'ldi. Birozdan keyin urinib ko'ring."
SEARCH_EMPTY = "Hech narsa topilmadi. Boshqacharoq so'rab ko'ring."
```

- [ ] **Step 4:** PASS (barcha testlar). **Step 5:** commit `feat: qidiruv mantiqi va shahar so'rash`.

---

### Task 2.6: Telegram qismi va ishga tushirish

**Files:** Modify `bot/keyboards.py`, `bot/handlers.py`, `bot/main.py`, `content/uz.py`, `render.yaml`, `.env.example`, `tests/test_keyboards.py`

**Interfaces — Produces:** `keyboards.SEARCH_MORE = "search:more"`, `location_keyboard() -> ReplyKeyboardMarkup`, `more_keyboard() -> InlineKeyboardMarkup`; handlerlar `searcher` va `geo`ni `dp["searcher"]`, `dp["geo"]`dan oladi; `main.build_bot(config, ai, searcher, geo)`.

- [ ] **Step 1: Failing test** (`tests/test_keyboards.py`):
```python
from bot.keyboards import location_keyboard, more_keyboard


def test_location_keyboard_requests_location_once():
    kb = location_keyboard()
    assert kb.keyboard[0][0].request_location is True
    assert kb.keyboard[0][0].text == "📍 Joylashuvni yuborish"
    assert kb.one_time_keyboard is True and kb.resize_keyboard is True


def test_more_keyboard():
    button = more_keyboard().inline_keyboard[0][0]
    assert button.callback_data == "search:more" and button.text == "➡️ Yana ko'rsat"
```

- [ ] **Step 2:** FAIL. **Step 3: Kod**

`content/uz.py`:
```python
SEND_LOCATION_BUTTON = "📍 Joylashuvni yuborish"
PLACE_DETECTED = "📍 {city} bo'yicha qidiryapman..."
PLACE_NOT_FOUND = "Joylashuvdan shaharni aniqlay olmadim. Iltimos, shahar nomini yozing."
LOCATION_UNUSED = "Joylashuv qabul qilindi, lekin hozir kutilayotgan qidiruv yo'q."
SEARCH_MORE_BUTTON = "➡️ Yana ko'rsat"
SEARCH_EXPIRED = "Bu natijalar eskirgan. Qidiruvni qaytadan so'rang."
```
`START`ga qidiruv namunalari: `• qidiruv: «Toshkent–Istanbul 15-oktabr bilet top», «Yosin surasini YouTube'dan top»`.

`bot/keyboards.py`:
```python
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

SEARCH_MORE = "search:more"


def location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=uz.SEND_LOCATION_BUTTON, request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def more_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=uz.SEARCH_MORE_BUTTON, callback_data=SEARCH_MORE)]]
    )
```

`bot/handlers.py`:
- modul darajasida holat (bitta egasi, bitta jarayon):
```python
# Bot bitta egaga xizmat qiladi va bitta jarayonda ishlaydi — holat xotirada yetarli.
_pending: dict[str, Intent] = {}  # "search" → shahar kutayotgan qidiruv
_more_pages: dict[int, str] = {}  # xabar id → "Yana ko'rsat" sahifasi
MORE_PAGES_LIMIT = 50
NO_PREVIEW = LinkPreviewOptions(is_disabled=True)
```
- `on_voice(message, bot, ai, searcher)` va `on_text(message, ai, searcher)` → `_process(message, text, ai, searcher)`.
- `_process`:
```python
async def _process(message: Message, text: str, ai: AIClient, searcher) -> None:
    try:
        pending = _pending.pop("search", None)
        if pending is not None and looks_like_place(text):
            place = text.strip()
            await message.answer(uz.PLACE_DETECTED.format(city=escape(place, quote=False)), reply_markup=ReplyKeyboardRemove())
            reply = await run_search(pending, place, ai, searcher)
        else:
            reply = await handle_text(text, ai, db, now_tashkent(), searcher)
    except AIError as exc:
        ...  # mavjud
    except Exception:
        ...  # mavjud
    await send_reply(message, reply, ai)
```
- joylashuv:
```python
    @router.message(F.location)
    async def on_location(message: Message, ai: AIClient, searcher, geo: Geocoder) -> None:
        pending = _pending.pop("search", None)
        if pending is None:
            await message.answer(uz.LOCATION_UNUSED, reply_markup=ReplyKeyboardRemove())
            return
        city = await geo.city(message.location.latitude, message.location.longitude)
        if not city:
            _pending["search"] = pending
            await message.answer(uz.PLACE_NOT_FOUND)
            return
        await message.answer(uz.PLACE_DETECTED.format(city=escape(city, quote=False)), reply_markup=ReplyKeyboardRemove())
        await send_reply(message, await run_search(pending, city, ai, searcher), ai)
```
- "Yana ko'rsat":
```python
    @router.callback_query(F.data == SEARCH_MORE)
    async def on_more(callback: CallbackQuery) -> None:
        await callback.answer()
        if not isinstance(callback.message, Message):
            return
        page = _more_pages.pop(callback.message.message_id, None)
        try:
            await callback.message.edit_reply_markup(reply_markup=None)
        except TelegramBadRequest as exc:
            log.info("Tugma olib tashlanmadi: %s", exc)
        await callback.message.answer(page or uz.SEARCH_EXPIRED, link_preview_options=NO_PREVIEW)
```
- `send_reply` ga:
```python
    elif reply.kind == "ask_place":
        _pending["search"] = reply.pending
        await message.answer(reply.text, reply_markup=location_keyboard())
    elif reply.kind == "search":
        sent = await message.answer(
            reply.text, reply_markup=more_keyboard() if reply.more else None, link_preview_options=NO_PREVIEW
        )
        if reply.more:
            _more_pages[sent.message_id] = reply.more
            while len(_more_pages) > MORE_PAGES_LIMIT:
                _more_pages.pop(next(iter(_more_pages)))
```

`bot/main.py`:
```python
    searcher = TavilyClient(config.tavily_api_key) if config.tavily_api_key else None
    geo = Geocoder()
    bot, dp = build_bot(config, ai, searcher, geo)
    log.info("Qidiruv: %s", "yoqilgan" if searcher else "o'chirilgan")
    ...
    finally:
        ...
        if searcher:
            await searcher.close()
        await geo.close()
```
`build_bot(config, ai, searcher, geo)`: `dp["searcher"] = searcher`, `dp["geo"] = geo`.

`render.yaml` ga `TAVILY_API_KEY` (`sync: false`); `.env.example` ga `TAVILY_API_KEY=` (ixtiyoriy izoh bilan).

- [ ] **Step 4:** `.venv/Scripts/python -c "from bot.main import build_app; from bot.handlers import build_router; build_router(1)"` va barcha testlar → PASS. **Step 5:** commit `feat: Telegram'da qidiruv, joylashuv va "Yana ko'rsat"`.

---

### Task 2.7: Jonli sinov va chiqarish

- [ ] **Step 1:** Haqiqiy Groq + Tavily bilan skript orqali (Telegram'siz) 5 ta so'rov: aviabilet, mehmonxona (shahar bilan), restoran (shaharsiz → `ask_place`), YouTube (sura), umumiy savol — natija sarlavhalari va havolalari chiqariladi.
- [ ] **Step 2:** TZ 13-bo'limidagi bloklar belgilanadi, commit.
- [ ] **Step 3:** Egasining ruxsati bilan push; egasi Render → Environment'ga `TAVILY_API_KEY` qo'shadi; deploy'dan keyin Telegram'da sinov (shu jumladan 📍 tugma va "Yana ko'rsat").
