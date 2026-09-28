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
