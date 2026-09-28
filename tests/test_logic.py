from datetime import datetime, timedelta

from bot.ai_client import AIError, Intent
from bot.logic import Reply, daily_report, handle_text, looks_like_place, run_search, task_report
from bot.models import Task
from bot.scheduler import TASHKENT
from bot.booking import BookingRequest
from bot.search import SearchError, SearchResult
from content import uz

NOW = datetime(2026, 9, 28, 19, 0, tzinfo=TASHKENT)
DUE = datetime(2026, 9, 29, 15, 0, tzinfo=TASHKENT)
OVERDUE = Task(1, "Onamga telefon", datetime(2026, 9, 27, 9, 0, tzinfo=TASHKENT))
UPCOMING = Task(2, "Shifokor", DUE)
DONE = Task(3, "Uchrashuv", done_at=datetime(2026, 9, 28, 10, 0, tzinfo=TASHKENT))


HOTEL = Intent("search", title="Arzon mehmonxona", category="hotel", query="arzon mehmonxona")
RESULTS = [SearchResult(f"Natija {i}", f"https://r{i}.com", "") for i in range(1, 6)]


class FakeAI:
    def __init__(self, intent, ranking=None, rank_error=False):
        self.intent = intent
        self.ranking = ranking or []
        self.rank_error = rank_error
        self.seen = []

    async def understand(self, text, now, history=()):
        self.seen.append((text, now))
        self.history = list(history)
        return self.intent

    async def rank_results(self, request, results):
        if self.rank_error:
            raise AIError("down")
        return self.ranking


class FakeSearcher:
    def __init__(self, results=None, error=False):
        self.results = RESULTS if results is None else results
        self.error = error
        self.calls = []

    async def search(self, query, category, max_results=6):
        self.calls.append((query, category))
        if self.error:
            raise SearchError("down")
        return self.results


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


async def test_search_disabled_without_searcher():
    reply = await handle_text("mehmonxona top", FakeAI(HOTEL), FakeStore(), NOW)
    assert reply == Reply("text", uz.SEARCH_DISABLED)


async def test_hotel_without_place_asks_for_city():
    searcher = FakeSearcher()
    reply = await handle_text("mehmonxona top", FakeAI(HOTEL), FakeStore(), NOW, searcher)
    assert reply == Reply("ask_place", uz.ASK_PLACE, pending=HOTEL)
    assert searcher.calls == []


async def test_place_from_message_goes_straight_to_search():
    intent = Intent("search", title="Arzon mehmonxona", category="hotel", query="arzon mehmonxona", place="Andijon")
    searcher = FakeSearcher()
    reply = await handle_text("Andijonda mehmonxona", FakeAI(intent), FakeStore(), NOW, searcher)
    assert reply.kind == "search"
    assert searcher.calls == [("arzon mehmonxona Andijon", "hotel")]


async def test_run_search_ranks_and_pages():
    ai = FakeAI(HOTEL, ranking=[(4, "Eng yaxshisi"), (0, ""), (1, ""), (2, "To'rtinchi")])
    reply = await run_search(HOTEL, "Andijon", ai, FakeSearcher())
    assert reply.kind == "search"
    assert reply.text.startswith("🏨 <b>Arzon mehmonxona, Andijon</b>\n\n1. <b>Natija 5</b>\nEng yaxshisi")
    assert "4. <b>Natija 3</b>" in reply.more


async def test_place_not_duplicated_in_query():
    intent = Intent("search", title="T", category="restaurant", query="Andijon kafe")
    searcher = FakeSearcher()
    await run_search(intent, "Andijon", FakeAI(intent, ranking=[]), searcher)
    assert searcher.calls == [("Andijon kafe", "restaurant")]


async def test_ranking_failure_falls_back_to_search_order():
    reply = await run_search(HOTEL, "Andijon", FakeAI(HOTEL, rank_error=True), FakeSearcher())
    assert "1. <b>Natija 1</b>" in reply.text and "2. <b>Natija 2</b>" in reply.text
    assert "4. <b>Natija 4</b>" in reply.more


async def test_search_error_and_empty():
    assert await run_search(HOTEL, "A", FakeAI(HOTEL), FakeSearcher(error=True)) == Reply("text", uz.SEARCH_ERROR)
    assert await run_search(HOTEL, "A", FakeAI(HOTEL), FakeSearcher(results=[])) == Reply("text", uz.SEARCH_EMPTY)


async def test_three_results_have_no_second_page():
    reply = await run_search(HOTEL, None, FakeAI(HOTEL, ranking=[]), FakeSearcher(results=RESULTS[:3]))
    assert reply.more == ""


def test_looks_like_place():
    assert looks_like_place("Andijon")
    assert looks_like_place("  Nyu York shahri ")
    assert not looks_like_place("")
    assert not looks_like_place("ertaga soat 10 da bankka borish")


async def test_history_is_passed_to_ai():
    ai = FakeAI(Intent("unknown"))
    history = [{"role": "user", "content": "Toshkent Madina chipta"}]
    await handle_text("eng arzonini top", ai, FakeStore(), NOW, history=history)
    assert ai.history == history


BOOK = Intent("book", booking=BookingRequest(
    name="CHINOR HOTEL", city="Andijon", category="hotel",
    checkin=datetime(2026, 10, 30).date(), guests=2, rooms=1, room_type="delux",
))


async def test_book_hotel_finds_contacts_and_link():
    searcher = FakeSearcher(results=[SearchResult("Chinor", "https://chinor.uz", "Tel: +998 74 223 45 67")])
    reply = await handle_text("Chinor hotel bron qil", FakeAI(BOOK), FakeStore(), NOW, searcher)
    assert reply.kind == "booking"
    assert reply.url.startswith("https://www.booking.com/searchresults.html?")
    assert "📞 +998 74 223 45 67 — chinor.uz" in reply.text
    assert searcher.calls == [("CHINOR HOTEL Andijon telefon raqami", "general")]


async def test_book_without_searcher_or_on_error_still_prepares_link():
    reply = await handle_text("bron qil", FakeAI(BOOK), FakeStore(), NOW)
    assert reply.kind == "booking" and reply.url and "topilmadi" in reply.text
    reply = await handle_text("bron qil", FakeAI(BOOK), FakeStore(), NOW, FakeSearcher(error=True))
    assert reply.kind == "booking" and "topilmadi" in reply.text
