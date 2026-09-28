from datetime import datetime, timedelta

from bot.ai_client import Intent
from bot.logic import Reply, daily_report, handle_text, task_report
from bot.models import Task
from bot.scheduler import TASHKENT
from content import uz

NOW = datetime(2026, 9, 28, 19, 0, tzinfo=TASHKENT)
DUE = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)
OVERDUE = Task(1, "Onamga telefon", datetime(2026, 9, 27, 9, 0, tzinfo=TASHKENT))
UPCOMING = Task(2, "Shifokor", DUE)
DONE = Task(3, "Uchrashuv", done_at=datetime(2026, 9, 28, 10, 0, tzinfo=TASHKENT))


class FakeAI:
    def __init__(self, intent):
        self.intent = intent
        self.seen = []

    async def understand(self, text, now):
        self.seen.append((text, now))
        return self.intent


class FakeStore:
    def __init__(self, tasks=None, done=None):
        self.tasks = tasks or []
        self.done = done or []
        self.added = []
        self.done_since = None

    async def add_task(self, title, due_at):
        self.added.append((title, due_at))
        return 1

    async def list_open_tasks(self):
        return self.tasks

    async def list_done_tasks(self, since):
        self.done_since = since
        return self.done


async def test_add_task_saves_and_replies_by_voice():
    store = FakeStore()
    reply = await handle_text("ertaga 15:00 shifokor", FakeAI(Intent("add_task", "Shifokor", DUE)), store, NOW)
    assert store.added == [("Shifokor", DUE)]
    assert reply == Reply("voice", "Vazifa qo'shildi: Shifokor. Muddati: 29.09.2026 15:00.")


async def test_list_returns_full_report_with_done_last_7_days():
    store = FakeStore([UPCOMING, OVERDUE], [DONE])
    reply = await handle_text("vazifalarim", FakeAI(Intent("list_tasks")), store, NOW)
    assert reply.kind == "list"
    assert reply.tasks == [OVERDUE, UPCOMING]
    assert "Bajarilgan" in reply.text and "Muddati o'tgan" in reply.text
    assert store.done_since == NOW - timedelta(days=7)


async def test_list_filter_is_applied():
    store = FakeStore([UPCOMING, OVERDUE], [DONE])
    reply = await handle_text("bajarilganlar", FakeAI(Intent("list_tasks", filter="done")), store, NOW)
    assert reply.tasks == []
    assert "Uchrashuv" in reply.text and "Shifokor" not in reply.text


async def test_task_report_skips_done_query_when_not_needed():
    store = FakeStore([UPCOMING])
    await task_report(store, NOW, "today")
    assert store.done_since is None


async def test_daily_report():
    reply = await daily_report(FakeStore([UPCOMING, OVERDUE], [DONE]), NOW)
    assert reply.kind == "list"
    assert reply.text.startswith("☀️")
    assert reply.tasks == [OVERDUE, UPCOMING]


async def test_speak_report_uses_report_order():
    reply = await handle_text("ovozda ayt", FakeAI(Intent("speak_report")), FakeStore([UPCOMING, OVERDUE]), NOW)
    assert reply.kind == "list_voice"
    assert reply.text.startswith("Sizda 2 ta ochiq vazifa bor. 1. Onamga telefon")


async def test_chat_reply_goes_to_voice():
    reply = await handle_text("salom", FakeAI(Intent("chat", reply="Va alaykum assalom!")), FakeStore(), NOW)
    assert reply == Reply("voice", "Va alaykum assalom!")


async def test_unknown_asks_again_as_text_and_saves_nothing():
    store = FakeStore()
    reply = await handle_text("...", FakeAI(Intent("unknown")), store, NOW)
    assert reply == Reply("text", uz.NOT_UNDERSTOOD)
    assert store.added == []


async def test_passes_text_and_now_to_ai():
    ai = FakeAI(Intent("unknown"))
    await handle_text("x", ai, FakeStore(), NOW)
    assert ai.seen == [("x", NOW)]
