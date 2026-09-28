"""Bronga tayyorlash: Booking.com havolasi, aloqa raqamlari va aytiladigan gap. To'lov qilinmaydi."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, timedelta
from html import escape
from urllib.parse import urlencode, urlparse

from bot.search import SearchResult
from content import uz

BOOKING_SEARCH_URL = "https://www.booking.com/searchresults.html"
BOOKING_DOMAINS = ["booking.com"]
CONTACT_LIMIT = 4
_PHONE = re.compile(r"\+?998[\s\-().]*(\d{2})[\s\-().]*(\d{3})[\s\-.]*(\d{2})[\s\-.]*(\d{2})(?!\d)")
_TELEGRAM = re.compile(r"(?:https?://)?t\.me/([A-Za-z0-9_]{5,32})")
_HOTEL_PAGE = re.compile(r"^https://www\.booking\.com/hotel/[a-z]{2}/[a-z0-9\-]+(?:\.[a-z\-]+)?\.html")


@dataclass(frozen=True)
class BookingRequest:
    name: str  # foydalanuvchiga ko'rsatiladigan nom (o'zbekcha bo'lishi mumkin)
    city: str = ""
    category: str = "hotel"  # "hotel" | "restaurant"
    checkin: date | None = None  # restoran uchun — sana
    checkout: date | None = None
    guests: int = 1
    rooms: int = 1
    room_type: str = ""
    time: str = ""  # restoran uchun, "19:00"
    name_en: str = ""  # aniq joy nomi lotincha/inglizcha; bo'sh — aniq nom aytilmagan
    destination_en: str = ""  # shahar inglizcha ("Dubai", "Andijan") — Booking faqat shuni taniydi
    stars: int | None = None

    @property
    def nights_end(self) -> date | None:
        if self.checkin is None:
            return None
        if self.checkout and self.checkout > self.checkin:
            return self.checkout
        return self.checkin + timedelta(days=1)


def _d(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def _stay_params(req: BookingRequest) -> dict:
    params: dict = {}
    if req.checkin:
        params.update(checkin=req.checkin.isoformat(), checkout=req.nights_end.isoformat())
    params.update(group_adults=req.guests, no_rooms=req.rooms, group_children=0)
    return params


def city_search_url(req: BookingRequest) -> str | None:
    """Shahar bo'yicha ro'yxat. Booking `ss`da faqat joy nomini taniydi — tavsif yoki
    mehmonxona nomi "0 variant" beradi va sanalarni tashlab yuboradi."""
    destination = req.destination_en or req.city
    if not destination:
        return None
    params = {"ss": destination, **_stay_params(req)}
    if req.stars in (1, 2, 3, 4, 5):
        params["nflt"] = f"class={req.stars}"
    return f"{BOOKING_SEARCH_URL}?{urlencode(params)}"


def find_booking_page(results: list[SearchResult]) -> str | None:
    """Qidiruv natijalaridan mehmonxonaning Booking sahifasi (`/hotel/<davlat>/<nom>.html`)."""
    for result in results:
        match = _HOTEL_PAGE.match(result.url)
        if match:
            return match.group(0)
    return None


def hotel_page_url(page: str, req: BookingRequest) -> str:
    return f"{page}?{urlencode(_stay_params(req))}"


def _domain(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def extract_contacts(results: list[SearchResult]) -> list[tuple[str, str]]:
    """Qidiruv natijalaridan (raqam yoki @telegram, manba sayti) juftliklari.

    Natijalarda boshqa joylarning raqamlari ham uchrashi mumkin — manba egasiga tekshirish uchun ko'rsatiladi.
    """
    contacts: list[tuple[str, str]] = []
    seen: set[str] = set()
    for result in results:
        text = f"{result.url} {result.title} {result.content}"
        found = [(m.start(), "+998 " + " ".join(m.groups())) for m in _PHONE.finditer(text)]
        found += [(m.start(), "@" + m.group(1)) for m in _TELEGRAM.finditer(text)]
        for _, contact in sorted(found):
            if contact not in seen:
                seen.add(contact)
                contacts.append((contact, _domain(result.url)))
    return contacts[:CONTACT_LIMIT]


def call_script(req: BookingRequest) -> str:
    if req.category == "restaurant":
        when = f"{_d(req.checkin)} kuni " if req.checkin else ""
        at = f"soat {req.time} ga " if req.time else ""
        return uz.CALL_SCRIPT_RESTAURANT.format(when=when, at=at, guests=req.guests)
    period = f"{_d(req.checkin)} dan {_d(req.nights_end)} gacha " if req.checkin else ""
    room = f"{req.room_type} xona" if req.room_type else "xona"
    return uz.CALL_SCRIPT_HOTEL.format(period=period, guests=req.guests, rooms=req.rooms, room=room)


def format_booking(req: BookingRequest, contacts: list[tuple[str, str]], link: str) -> str:
    """link: "page" — mehmonxona sahifasi, "city" — shahar ro'yxati, "" — tugma yo'q."""
    icon = "🍽" if req.category == "restaurant" else "🏨"
    title = escape(", ".join(p for p in (req.name, req.city) if p), quote=False)
    details = []
    if req.category == "restaurant":
        when = " ".join(p for p in (_d(req.checkin) if req.checkin else "", req.time) if p)
        details.append(f"📅 {when}" if when else uz.BOOKING_NO_DATE)
        details.append(f"👥 {req.guests} kishi")
    else:
        details.append(f"📅 {_d(req.checkin)} → {_d(req.nights_end)}" if req.checkin else uz.BOOKING_NO_DATE)
        details.append(f"👥 {req.guests} kishi")
        room = f"🛏 {req.rooms} xona"
        details.append(f"{room} ({escape(req.room_type, quote=False)})" if req.room_type else room)
        if req.stars in (1, 2, 3, 4, 5):
            details.append(f"{req.stars}⭐")

    lines = [uz.BOOKING_HEADER.format(icon=icon, title=title), " · ".join(details), ""]
    if contacts:
        lines += [
            f"{'💬' if contact.startswith('@') else '📞'} {contact} — {escape(source, quote=False)}"
            for contact, source in contacts
        ]
        lines += [uz.BOOKING_CHECK_SOURCE, ""]
    elif req.name_en:
        lines += [uz.BOOKING_NO_CONTACTS, ""]
    lines += [uz.BOOKING_SCRIPT_LABEL, f"<i>{escape(call_script(req), quote=False)}</i>", ""]
    if req.category == "restaurant":
        lines.append(uz.BOOKING_NOTE_RESTAURANT)
    elif link == "page":
        lines.append(uz.BOOKING_NOTE_PAGE)
    elif link == "city":
        not_found = uz.BOOKING_PAGE_NOT_FOUND if req.name_en else ""
        lines.append(not_found + uz.BOOKING_NOTE_CITY)
    else:
        lines.append(uz.BOOKING_NOTE_NO_LINK)
    return "\n".join(lines)
