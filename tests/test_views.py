from datetime import datetime, timezone

from bot import views
from bot.models import Task
from bot.scheduler import TASHKENT
from content import uz

DUE = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)


def test_empty_list():
    assert views.format_task_list([]) == uz.NO_TASKS


def test_list_numbers_due_and_count():
    text = views.format_task_list([Task(1, "Shifokor", DUE), Task(7, "Non olish")])
    assert "(2 ta)" in text
    assert "1. Shifokor — <i>29.09.2026 15:00</i>" in text
    assert "2. Non olish — <i>muddatsiz</i>" in text


def test_title_is_html_escaped():
    assert "&lt;b&gt;x&lt;/b&gt;" in views.format_task_list([Task(1, "<b>x</b>")])


def test_due_converted_to_tashkent():
    utc = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
    assert views.format_due(utc) == "29.09.2026 15:00"


def test_daily_empty_and_full():
    assert views.format_daily_report([]) == uz.DAILY_EMPTY
    assert "Xayrli tong" in views.format_daily_report([Task(1, "Non")])


def test_speech_text_has_no_html():
    text = views.format_task_list_for_speech([Task(1, "Shifokor", DUE), Task(2, "Non")])
    assert text == (
        "Sizda 2 ta ochiq vazifa bor. "
        "1. Shifokor, muddati 29.09.2026 15:00. "
        "2. Non."
    )


def test_speech_empty():
    assert views.format_task_list_for_speech([]) == uz.SPEECH_EMPTY


def test_task_added_text():
    assert views.task_added_text("Non", None) == "Vazifa qo'shildi: Non."
    assert (
        views.task_added_text("Shifokor", DUE)
        == "Vazifa qo'shildi: Shifokor. Muddati: 29.09.2026 15:00."
    )
