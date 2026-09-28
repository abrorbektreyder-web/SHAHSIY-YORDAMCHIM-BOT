from datetime import date
from urllib.parse import parse_qs, urlparse

from bot.booking import BookingRequest, booking_url, call_script, extract_contacts, format_booking
from bot.search import SearchResult

HOTEL = BookingRequest(
    name="CHINOR HOTEL", city="Andijon", category="hotel",
    checkin=date(2026, 10, 30), checkout=date(2026, 10, 31), guests=2, rooms=1, room_type="delux",
)
CAFE = BookingRequest(
    name="Rayhon", city="Toshkent", category="restaurant", checkin=date(2026, 10, 1), guests=4, time="19:00",
)


def test_booking_url_prefills_dates_guests_and_rooms():
    url = booking_url(HOTEL)
    parts = urlparse(url)
    assert parts.scheme == "https" and parts.netloc == "www.booking.com"
    q = parse_qs(parts.query)
    assert q["ss"] == ["CHINOR HOTEL Andijon"]
    assert q["checkin"] == ["2026-10-30"] and q["checkout"] == ["2026-10-31"]
    assert q["group_adults"] == ["2"] and q["no_rooms"] == ["1"]


def test_no_booking_url_for_restaurants():
    assert booking_url(CAFE) is None


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


def test_format_booking_with_and_without_contacts():
    text = format_booking(HOTEL, [("+998 74 223 45 67", "chinor.uz")])
    assert text.startswith("🏨 <b>CHINOR HOTEL, Andijon</b> — bron uchun tayyor")
    assert "📅 30.10.2026 → 31.10.2026 · 👥 2 kishi · 🛏 1 xona (delux)" in text
    assert "📞 +998 74 223 45 67 — chinor.uz" in text
    assert "Assalomu alaykum!" in text
    assert "to'lov" in text.lower()
    assert "topilmadi" in format_booking(HOTEL, [])


def test_format_booking_escapes_html():
    req = BookingRequest(name="<Hotel>", city="", category="hotel")
    assert "&lt;Hotel&gt;" in format_booking(req, [])
