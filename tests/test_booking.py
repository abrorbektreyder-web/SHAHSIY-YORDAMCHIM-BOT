from datetime import date
from urllib.parse import parse_qs, urlparse

from bot.booking import (
    BookingRequest,
    call_script,
    city_search_url,
    extract_contacts,
    find_booking_page,
    format_booking,
    hotel_page_url,
)
from bot.search import SearchResult

HOTEL = BookingRequest(
    name="CHINOR HOTEL", city="Andijon", category="hotel",
    checkin=date(2026, 10, 30), checkout=date(2026, 10, 31), guests=2, rooms=1, room_type="delux",
    name_en="Chinor Hotel", destination_en="Andijan",
)
DUBAI = BookingRequest(
    name="Dubaydagi 5 yulduzli mehmonxona", city="Dubay", category="hotel",
    checkin=date(2026, 10, 30), guests=2, destination_en="Dubai", stars=5,
)
CAFE = BookingRequest(
    name="Rayhon", city="Toshkent", category="restaurant", checkin=date(2026, 10, 1), guests=4, time="19:00",
)


def query(url):
    return parse_qs(urlparse(url).query)


def test_city_search_url_uses_english_destination_dates_and_stars():
    # Brauzerda tekshirilgan: o'zbekcha tavsif yoki mehmonxona nomi "0 variant" va sana
    # tiklanishiga olib keladi; "Dubai" + nflt=class=5 esa 30–31-okt, 5 yulduz, 350 variant.
    url = city_search_url(DUBAI)
    assert url.startswith("https://www.booking.com/searchresults.html?")
    q = query(url)
    assert q["ss"] == ["Dubai"]
    assert q["checkin"] == ["2026-10-30"] and q["checkout"] == ["2026-10-31"]
    assert q["group_adults"] == ["2"] and q["no_rooms"] == ["1"]
    assert q["nflt"] == ["class=5"]


def test_city_search_url_needs_destination():
    assert city_search_url(BookingRequest(name="Mehmonxona", category="hotel")) is None
    no_stars = query(city_search_url(HOTEL))
    assert no_stars["ss"] == ["Andijan"] and "nflt" not in no_stars


def test_find_booking_page_picks_hotel_page():
    results = [
        SearchResult("Reviews", "https://www.booking.com/reviews/uz/hotel/chinor.html?page=1"),
        SearchResult("City", "https://www.booking.com/city/uz/andijan.en-gb.html"),
        SearchResult("CHINOR HOTEL", "https://www.booking.com/hotel/uz/chinor.en-gb.html?aid=1"),
    ]
    assert find_booking_page(results) == "https://www.booking.com/hotel/uz/chinor.en-gb.html"
    assert find_booking_page(results[:2]) is None


def test_hotel_page_url_adds_dates_and_guests():
    # Brauzerda tekshirilgan: /hotel/uz/chinor.html?checkin=2026-10-30... sahifani 30–31-okt bilan ochadi.
    url = hotel_page_url("https://www.booking.com/hotel/uz/chinor.html", HOTEL)
    assert url.startswith("https://www.booking.com/hotel/uz/chinor.html?")
    q = query(url)
    assert q["checkin"] == ["2026-10-30"] and q["checkout"] == ["2026-10-31"]
    assert q["group_adults"] == ["2"] and q["no_rooms"] == ["1"]


def test_extract_contacts_normalizes_phones_and_telegram():
    results = [
        SearchResult("Chinor Hotel", "https://chinor.uz", "Tel: +998 (74) 223-45-67, bron uchun"),
        SearchResult("Chinor", "https://t.me/chinor_hotel", "Telegram kanal. 998742234567"),
        SearchResult("Boshqa", "https://x.uz", "Aloqa: +998 90 123 45 67 va t.me/chinor_booking"),
    ]
    # Raqam boshqa joyniki bo'lib chiqmasligi uchun manba sayti ham qaytariladi.
    assert extract_contacts(results) == [
        ("+998 74 223 45 67", "chinor.uz"),
        ("@chinor_hotel", "t.me"),
        ("+998 90 123 45 67", "x.uz"),
        ("@chinor_booking", "x.uz"),
    ]


def test_extract_contacts_limit():
    many = [SearchResult("x", "https://x.uz", f"+998 90 123 45 6{i}") for i in range(9)]
    assert len(extract_contacts(many)) == 4


def test_call_scripts():
    assert call_script(HOTEL) == (
        "Assalomu alaykum! 30.10.2026 dan 31.10.2026 gacha 2 kishi uchun 1 ta delux xona "
        "band qilmoqchiman. Bo'sh joy bormi va narxi qancha? To'lovni joyida qilsam bo'ladimi?"
    )
    assert call_script(CAFE) == (
        "Assalomu alaykum! 01.10.2026 kuni soat 19:00 ga 4 kishilik joy band qilmoqchiman. Bo'sh joy bormi?"
    )


def test_format_booking_exact_page_with_contacts():
    text = format_booking(HOTEL, [("+998 74 223 45 67", "chinor.uz")], link="page")
    assert text.startswith("🏨 <b>CHINOR HOTEL, Andijon</b> — bron uchun tayyor")
    assert "📅 30.10.2026 → 31.10.2026 · 👥 2 kishi · 🛏 1 xona (delux)" in text
    assert "📞 +998 74 223 45 67 — chinor.uz" in text
    assert "Assalomu alaykum!" in text
    assert "mehmonxona sahifasini" in text
    assert "to'lov" in text.lower()


def test_format_booking_city_list_and_missing_date():
    text = format_booking(DUBAI, [], link="city")
    assert "5⭐" in text and "ro'yxatini" in text
    assert "📞" not in text
    undated = format_booking(BookingRequest(name="Mehmonxona", city="Dubay", category="hotel"), [], link="city")
    assert "sana aytilmadi" in undated


def test_format_booking_escapes_html():
    req = BookingRequest(name="<Hotel>", city="", category="hotel")
    assert "&lt;Hotel&gt;" in format_booking(req, [], link="")
