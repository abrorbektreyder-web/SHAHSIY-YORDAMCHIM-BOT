from bot import main
from bot.config import Config
from bot.models import Task


def test_webhook_url_has_fixed_path_without_secret():
    assert main.WEBHOOK_PATH == "/tg/webhook"
    assert main.webhook_url("https://x.onrender.com/") == "https://x.onrender.com/tg/webhook"


async def test_register_webhook_keeps_pending_updates():
    calls = {}

    class FakeBot:
        async def set_webhook(self, url, **kwargs):
            calls.update(url=url, **kwargs)

    config = Config(
        bot_token="t", owner_id=1, openrouter_api_key="k", database_url="d",
        mode="webhook", webhook_base_url="https://x.onrender.com", webhook_secret="abc123",
    )
    await main.register_webhook(FakeBot(), config)
    assert calls["url"] == "https://x.onrender.com/tg/webhook"
    assert calls["secret_token"] == "abc123"
    # Render qayta ishga tushayotganda yuborilgan xabarlar yo'qolmasin.
    assert calls["drop_pending_updates"] is False


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
