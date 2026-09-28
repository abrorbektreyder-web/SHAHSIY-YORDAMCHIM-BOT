from bot import main
from bot.models import Task


def test_webhook_path_and_url():
    assert main.webhook_path("abc") == "/tg/abc"
    assert main.webhook_url("https://x.onrender.com/", "abc") == "https://x.onrender.com/tg/abc"


async def test_daily_sender_sends_report_with_buttons_to_owner(monkeypatch):
    sent = {}

    class FakeBot:
        async def send_message(self, chat_id, text, reply_markup=None):
            sent.update(chat_id=chat_id, text=text, markup=reply_markup)

    async def fake_list():
        return [Task(3, "Non")]

    monkeypatch.setattr(main.db, "list_open_tasks", fake_list)
    await main.make_daily_sender(FakeBot(), 42)()
    assert sent["chat_id"] == 42
    assert "Xayrli tong" in sent["text"]
    assert sent["markup"].inline_keyboard[0][0].callback_data == "done:3"


async def test_daily_sender_empty_has_no_buttons(monkeypatch):
    sent = {}

    class FakeBot:
        async def send_message(self, chat_id, text, reply_markup=None):
            sent.update(text=text, markup=reply_markup)

    async def fake_list():
        return []

    monkeypatch.setattr(main.db, "list_open_tasks", fake_list)
    await main.make_daily_sender(FakeBot(), 42)()
    assert sent["markup"] is None
