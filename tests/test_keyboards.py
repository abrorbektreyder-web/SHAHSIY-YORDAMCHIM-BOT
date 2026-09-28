from bot.keyboards import location_keyboard, more_keyboard, parse_done, task_list_keyboard
from bot.models import Task


def test_keyboard_has_done_per_task_and_speak_button():
    rows = task_list_keyboard([Task(5, "Non"), Task(9, "Shifokor")]).inline_keyboard
    assert [row[0].callback_data for row in rows] == ["done:5", "done:9", "speak:list"]
    assert rows[0][0].text == "✅ 1. Non"
    assert rows[2][0].text == "🔊 Ovozda eshitish"


def test_long_title_is_shortened():
    rows = task_list_keyboard([Task(1, "a" * 50)]).inline_keyboard
    assert rows[0][0].text == "✅ 1. " + "a" * 29 + "…"


def test_parse_done():
    assert parse_done("done:12") == 12
    assert parse_done("done:x") is None
    assert parse_done("speak:list") is None


def test_location_keyboard_requests_location_once():
    kb = location_keyboard()
    assert kb.keyboard[0][0].request_location is True
    assert kb.keyboard[0][0].text == "📍 Joylashuvni yuborish"
    assert kb.one_time_keyboard is True and kb.resize_keyboard is True


def test_more_keyboard():
    button = more_keyboard().inline_keyboard[0][0]
    assert button.callback_data == "search:more" and button.text == "➡️ Yana ko'rsat"
