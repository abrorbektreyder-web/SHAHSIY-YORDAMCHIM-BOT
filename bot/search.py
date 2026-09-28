"""Tavily orqali internetdan qidirish va sahifa matnini o'qish."""
from __future__ import annotations

import re
from dataclasses import dataclass

import httpx

TAVILY_URL = "https://api.tavily.com/search"
TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"
YOUTUBE_DOMAINS = ["youtube.com"]
# Kanal va pleylist havolalari tashlangach ham yetarli video qolishi uchun.
YOUTUBE_FETCH = 10
_VIDEO = re.compile(r"^https?://(?:www\.|m\.)?(?:youtube\.com/(?:watch\?v=|shorts/)|youtu\.be/)[\w-]{6,}")


class SearchError(Exception):
    """Qidiruv xizmati javob bermadi yoki kutilmagan javob qaytardi."""


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    content: str = ""


def is_video_url(url: str) -> bool:
    return bool(_VIDEO.match(url))


class TavilyClient:
    def __init__(self, api_key: str, http: httpx.AsyncClient | None = None) -> None:
        self._http = http or httpx.AsyncClient(timeout=30)
        self._headers = {"Authorization": f"Bearer {api_key}"}

    async def _post(self, url: str, payload: dict) -> dict:
        try:
            resp = await self._http.post(url, json=payload, headers=self._headers)
        except httpx.HTTPError as exc:
            raise SearchError(f"tarmoq xatosi: {exc}") from exc
        if resp.status_code != 200:
            raise SearchError(f"HTTP {resp.status_code}: {resp.text[:200]}")
        try:
            data = resp.json()
        except ValueError as exc:
            raise SearchError(f"kutilmagan javob: {resp.text[:200]}") from exc
        if not isinstance(data, dict):
            raise SearchError(f"kutilmagan javob: {resp.text[:200]}")
        return data

    async def search(
        self, query: str, category: str, max_results: int = 6, domains: list[str] | None = None
    ) -> list[SearchResult]:
        youtube = category == "youtube" and not domains
        payload: dict = {
            "query": query,
            "search_depth": "basic",
            "max_results": max(max_results, YOUTUBE_FETCH) if youtube else max_results,
        }
        if domains:
            payload["include_domains"] = domains
        elif youtube:
            payload["include_domains"] = YOUTUBE_DOMAINS
        items = (await self._post(TAVILY_URL, payload)).get("results")
        if not isinstance(items, list):
            raise SearchError("kutilmagan javob: results yo'q")

        results = []
        for item in items:
            if not isinstance(item, dict):
                continue
            title, url, content = item.get("title"), item.get("url"), item.get("content")
            # Havola Telegram HTML'ga qo'yiladi — faqat http(s).
            if isinstance(title, str) and isinstance(url, str) and url.startswith(("http://", "https://")):
                results.append(
                    SearchResult(title.strip(), url, content.strip() if isinstance(content, str) else "")
                )
        if youtube:
            results = [r for r in results if is_video_url(r.url)][:max_results]
        return results

    async def extract(self, urls: list[str], query: str) -> dict[str, str]:
        """Sahifalarning savolga tegishli qismlari: {url: matn}. O'qib bo'lmaganlari tashlanadi."""
        data = await self._post(
            TAVILY_EXTRACT_URL, {"urls": urls, "query": query, "format": "text", "timeout": 20}
        )
        items = data.get("results")
        pages: dict[str, str] = {}
        for item in items if isinstance(items, list) else []:
            if isinstance(item, dict) and isinstance(item.get("url"), str) and isinstance(item.get("raw_content"), str):
                pages[item["url"]] = item["raw_content"]
        return pages

    async def close(self) -> None:
        await self._http.aclose()
