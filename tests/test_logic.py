from datetime import datetime

from bot.ai_client import Intent
from bot.logic import Reply, handle_text
from bot.models import Task
from bot.scheduler import TASHKENT
from content import uz

NOW = datetime(2026, 9, 28, 19, 0, tzinfo=TASHKENT)
DUE = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)


class FakeAI:
    def __init__(self, intent):
        self.intent = intent
        self.seen = []

    async def understand(self, text, now):
        self.seen.append((text, now))
        return self.intent


class FakeStore:
    def __init__(self, tasks=None):
        self.tasks = tasks or []
        self.added = []

    async def add_task(self, title, due_at):
        self.added.append((title, due_at))
        return 1

    async def list_open_tasks(self):
        return self.tasks


async def test_add_task_saves_and_replies_by_voice():
    store = FakeStore()
    reply = await handle_text("ertaga 15:00 shifokor", FakeAI(Intent("add_task", "Shifokor", DUE)), store, NOW)
    assert store.added == [("Shifokor", DUE)]
    assert reply == Reply("voice", "Vazifa qo'shildi: Shifokor. Muddati: 29.09.2026 15:00.")


async def test_list_returns_tasks():
    tasks = [Task(1, "Non")]
    reply = await handle_text("ro'yxat", FakeAI(Intent("list_tasks")), FakeStore(tasks), NOW)
    assert reply == Reply("list", tasks=tasks)


async def test_speak_report_returns_speech_text():
    tasks = [Task(1, "Non")]
    reply = await handle_text("ovozda ayt", FakeAI(Intent("speak_report")), FakeStore(tasks), NOW)
    assert reply == Reply("list_voice", "Sizda 1 ta ochiq vazifa bor. 1. Non.", tasks)


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
