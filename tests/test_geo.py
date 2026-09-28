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
    # zoom=10 da Toshkentdagi bir mahalla OSM'da "city" deb belgilangan; zoom=8 "Toshkent" qaytaradi.
    assert params["zoom"] == "8"
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
