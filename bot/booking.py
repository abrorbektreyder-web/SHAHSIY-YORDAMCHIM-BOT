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
CONTACT_LIMIT = 4
_PHONE = re.compile(r"\+?998[\s\-().]*(\d{2})[\s\-().]*(\d{3})[\s\-.]*(\d{2})[\s\-.]*(\d{2})(?!\d)")
_TELEGRAM = re.compile(r"(?:https?://)?t\.me/([A-Za-z0-9_]{5,32})")


@dataclass(frozen=True)
class BookingRequest:
    name: str
    city: str = ""
    category: str = "hotel"  # "hotel" | "restaurant"
    checkin: date | None = None  # restoran uchun — sana
    checkout: date | None = None
    guests: int = 1
    rooms: int = 1
    room_type: str = ""
    time: str = ""  # restoran uchun, "19:00"

    @property
    def nights_end(self) -> date | None:
        if self.checkin is None:
            return None
        if self.checkout and self.checkout > self.checkin:
            return self.checkout
        return self.checkin + timedelta(days=1)


def _d(value: date) -> str:
    return value.strftime("%d.%m.%Y")


def booking_url(req: BookingRequest) -> str | None:
    """Mehmonxona uchun sana, kishi va xona oldindan to'ldirilgan Booking.com qidiruv havolasi."""
    if req.category != "hotel":
        return None
    params = {"ss": " ".join(p for p in (req.name, req.city) if p)}
    if req.checkin:
        params.update(checkin=req.checkin.isoformat(), checkout=req.nights_end.isoformat())
    params.update(group_adults=req.guests, no_rooms=req.rooms, group_children=0)
    return f"{BOOKING_SEARCH_URL}?{urlencode(params)}"


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


def format_booking(req: BookingRequest, contacts: list[tuple[str, str]]) -> str:
    icon = "🍽" if req.category == "restaurant" else "🏨"
    title = escape(", ".join(p for p in (req.name, req.city) if p), quote=False)
    details = []
    if req.category == "restaurant":
        if req.checkin or req.time:
            details.append("📅 " + " ".join(p for p in (_d(req.checkin) if req.checkin else "", req.time) if p))
        details.append(f"👥 {req.guests} kishi")
    else:
        if req.checkin:
            details.append(f"📅 {_d(req.checkin)} → {_d(req.nights_end)}")
        details.append(f"👥 {req.guests} kishi")
        room = f"🛏 {req.rooms} xona"
        details.append(f"{room} ({escape(req.room_type, quote=False)})" if req.room_type else room)

    lines = [uz.BOOKING_HEADER.format(icon=icon, title=title), " · ".join(details), ""]
    if contacts:
        lines += [
            f"{'💬' if contact.startswith('@') else '📞'} {contact} — {escape(source, quote=False)}"
            for contact, source in contacts
        ]
        lines.append(uz.BOOKING_CHECK_SOURCE)
    else:
        lines.append(uz.BOOKING_NO_CONTACTS)
    lines += ["", uz.BOOKING_SCRIPT_LABEL, f"<i>{escape(call_script(req), quote=False)}</i>", ""]
    lines.append(uz.BOOKING_NOTE_RESTAURANT if req.category == "restaurant" else uz.BOOKING_NOTE_HOTEL)
    return "\n".join(lines)
