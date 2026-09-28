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
                params={"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 8, "accept-language": "uz"},
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
