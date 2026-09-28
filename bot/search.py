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
