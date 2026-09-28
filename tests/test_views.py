from datetime import datetime, timezone

from bot import views
from bot.models import Task
from bot.scheduler import TASHKENT
from bot.search import SearchResult
from content import uz

NOW = datetime(2026, 9, 28, 19, 0, tzinfo=TASHKENT)
DUE = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)

OVERDUE = Task(1, "Onamga telefon", datetime(2026, 9, 27, 9, 0, tzinfo=TASHKENT))
TODAY = Task(2, "Sut va non", datetime(2026, 9, 28, 20, 0, tzinfo=TASHKENT))
UPCOMING = Task(3, "Shifokor", DUE)
UNDATED = Task(4, "Kitob o'qish")
DONE = Task(5, "Uchrashuv", done_at=datetime(2026, 9, 28, 10, 0, tzinfo=TASHKENT))


def test_full_report_has_sections_counts_and_numbering():
    text, shown = views.build_report([UPCOMING, UNDATED, TODAY, OVERDUE], [DONE], NOW)
    assert text == (
        "📋 <b>Vazifalar</b> — jami 5 ta: 1 ta bajarildi, 4 ta qoldi\n"
        "\n"
        "⚠️ <b>Muddati o'tgan (1)</b>\n"
        "1. Onamga telefon — <i>27.09.2026 09:00</i>\n"
        "\n"
        "📅 <b>Bugun (1)</b>\n"
        "2. Sut va non — <i>20:00</i>\n"
        "\n"
        "🗓 <b>Rejadagi (2)</b>\n"
        "3. Shifokor — <i>29.09.2026 15:00</i>\n"
        "4. Kitob o'qish — <i>muddatsiz</i>\n"
        "\n"
        "✅ <b>Bajarilgan — oxirgi 7 kun (1)</b>\n"
        "• Uchrashuv — <i>28.09 da bajarildi</i>"
    )
    # Tugmalar raqami ro'yxatdagi raqam bilan bir xil bo'lishi uchun tartib muhim.
    assert shown == [OVERDUE, TODAY, UPCOMING, UNDATED]


def test_empty_report():
    assert views.build_report([], [], NOW) == (uz.NO_TASKS, [])


def test_only_done_tasks_still_shown():
    text, shown = views.build_report([], [DONE], NOW)
    assert "Bajarilgan" in text and shown == []


def test_filter_done():
    text, shown = views.build_report([OVERDUE, TODAY], [DONE], NOW, "done")
    assert "Uchrashuv" in text
    assert "Muddati o'tgan" not in text and "Bugun" not in text
    assert shown == []


def test_filter_today_includes_overdue():
    text, shown = views.build_report([OVERDUE, TODAY, UPCOMING], [DONE], NOW, "today")
    assert shown == [OVERDUE, TODAY]
    assert "Rejadagi" not in text and "Bajarilgan" not in text


def test_filter_open_hides_done():
    text, shown = views.build_report([TODAY], [DONE], NOW, "open")
    assert shown == [TODAY] and "Bajarilgan" not in text


def test_filter_with_nothing_to_show():
    assert views.build_report([TODAY], [], NOW, "overdue") == (uz.NO_TASKS_IN_FILTER, [])


def test_title_is_html_escaped():
    text, _ = views.build_report([Task(1, "<b>x</b>")], [], NOW)
    assert "&lt;b&gt;x&lt;/b&gt;" in text


def test_daily_report():
    text, shown = views.format_daily_report([UPCOMING, OVERDUE], NOW)
    assert text.startswith("☀️ <b>Xayrli tong! Bugungi vazifalar (2 ta):</b>")
    assert "Bajarilgan" not in text
    assert shown == [OVERDUE, UPCOMING]
    assert views.format_daily_report([], NOW) == (uz.DAILY_EMPTY, [])


def test_order_open():
    assert views.order_open([UNDATED, UPCOMING, TODAY, OVERDUE], NOW) == [OVERDUE, TODAY, UNDATED, UPCOMING]


def test_due_converted_to_tashkent():
    utc = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
    assert views.format_due(utc) == "29.09.2026 15:00"


def test_speech_text_has_no_html():
    text = views.format_task_list_for_speech([Task(1, "Shifokor", DUE), Task(2, "Non")])
    assert text == (
        "Sizda 2 ta ochiq vazifa bor. "
        "1. Shifokor, muddati 29.09.2026 15:00. "
        "2. Non."
    )


def test_speech_empty():
    assert views.format_task_list_for_speech([]) == uz.SPEECH_EMPTY


def test_search_pages_numbering_links_and_escaping():
    items = [
        (SearchResult("KAYAK <arzon>", "https://www.kayak.com/a?x=1&y=2"), "184$ dan, to'g'ridan-to'g'ri"),
        (SearchResult("Google Flights", "https://google.com/travel"), ""),
        (SearchResult("Expedia", "https://expedia.com/f"), "Izoh"),
        (SearchResult("Aviasales", "https://aviasales.uz/r"), "To'rtinchi"),
    ]
    pages = views.format_search_pages("flight", "Toshkent → Istanbul", items)
    assert len(pages) == 2
    assert pages[0] == (
        "✈️ <b>Toshkent → Istanbul</b>\n"
        "\n"
        "1. <b>KAYAK &lt;arzon&gt;</b>\n"
        "184$ dan, to'g'ridan-to'g'ri\n"
        '🔗 <a href="https://www.kayak.com/a?x=1&amp;y=2">kayak.com</a>\n'
        "\n"
        "2. <b>Google Flights</b>\n"
        '🔗 <a href="https://google.com/travel">google.com</a>\n'
        "\n"
        "3. <b>Expedia</b>\n"
        "Izoh\n"
        '🔗 <a href="https://expedia.com/f">expedia.com</a>'
    )
    assert pages[1].startswith("✈️ <b>Toshkent → Istanbul</b>\n\n4. <b>Aviasales</b>")


def test_search_pages_unknown_category_uses_default_icon():
    pages = views.format_search_pages("x", "Savol", [(SearchResult("A", "https://a.com"), "")])
    assert pages[0].startswith("🔎 <b>Savol</b>")


def test_heard_text_is_escaped():
    assert views.heard_text("Ertaga <bank>") == "🎤 <i>Eshitdim:</i> Ertaga &lt;bank&gt;"


def test_task_added_text():
    assert views.task_added_text("Non", None) == "Vazifa qo'shildi: Non."
    assert (
        views.task_added_text("Shifokor", DUE)
        == "Vazifa qo'shildi: Shifokor. Muddati: 29.09.2026 15:00."
    )
