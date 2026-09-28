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


async def test_search_can_be_limited_to_domains():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"results": []})

    await client_with(handler).search("Chinor Hotel Andijan", "general", max_results=5, domains=["booking.com"])
    assert seen["body"]["include_domains"] == ["booking.com"]
    assert seen["body"]["max_results"] == 5


async def test_youtube_keeps_only_video_links():
    seen = {}

    def handler(request):
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"results": [
            {"title": "Kanal", "url": "https://www.youtube.com/@QuranUz"},
            {"title": "Pleylist", "url": "https://www.youtube.com/playlist?list=PL123"},
            {"title": "Yosin surasi", "url": "https://www.youtube.com/watch?v=BuCLqqfBcbw"},
            {"title": "Short", "url": "https://www.youtube.com/shorts/abcDEF12345"},
            {"title": "Qisqa havola", "url": "https://youtu.be/n82sRRx730I"},
        ]})

    results = await client_with(handler).search("Yosin surasi", "youtube", max_results=2)
    assert [r.title for r in results] == ["Yosin surasi", "Short"]
    # Kanal/pleylistlar tashlangach ham yetarli video qolishi uchun ko'proq so'raladi.
    assert seen["body"]["max_results"] == 10


async def test_extract_returns_page_texts_by_url():
    seen = {}

    def handler(request):
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={
            "results": [{"url": "https://cbu.uz/kurs", "raw_content": "1 USD = 12 650 so'm"}],
            "failed_results": [{"url": "https://bad.uz", "error": "timeout"}],
        })

    pages = await client_with(handler).extract(["https://cbu.uz/kurs", "https://bad.uz"], "dollar kursi")
    assert pages == {"https://cbu.uz/kurs": "1 USD = 12 650 so'm"}
    assert seen["url"] == "https://api.tavily.com/extract"
    assert seen["body"]["urls"] == ["https://cbu.uz/kurs", "https://bad.uz"]
    assert seen["body"]["query"] == "dollar kursi" and seen["body"]["format"] == "text"


async def test_extract_http_error_raises():
    with pytest.raises(SearchError, match="500"):
        await client_with(lambda r: httpx.Response(500, text="x")).extract(["https://a.uz"], "q")
