from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# Ro'yxatning qaysi qismi ko'rsatiladi: hammasi / bajarilmagan / bajarilgan / bugun / muddati o'tgan.
REPORT_FILTERS = ("all", "open", "done", "today", "overdue")
SEARCH_CATEGORIES = ("flight", "hotel", "restaurant", "youtube", "general")
# Bu toifalarda shahar aytilmasa, bot so'raydi.
PLACE_CATEGORIES = ("hotel", "restaurant")


@dataclass(frozen=True)
class Task:
    id: int
    title: str
    due_at: datetime | None = None
    done_at: datetime | None = None
