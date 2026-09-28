from datetime import datetime, timedelta

from bot.ai_client import AIError, Answer, Intent
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
    def __init__(self, intent, ranking=None, rank_error=False, answer=None):
        self.intent = intent
        self.ranking = ranking or []
        self.rank_error = rank_error
        self.answer_result = answer
        self.seen = []

    async def understand(self, text, now, history=()):
        self.seen.append((text, now))
        self.history = list(history)
        return self.intent

    async def rank_results(self, request, results):
        if self.rank_error:
            raise AIError("down")
        return self.ranking

    async def answer(self, question, sources, now):
        self.answer_sources = sources
        if self.answer_result is None:
            raise AIError("down")
        return self.answer_result


class FakeSearcher:
    def __init__(self, results=None, error=False, extract_error=False):
        self.results = RESULTS if results is None else results
        self.error = error
        self.extract_error = extract_error
        self.calls = []

    async def search(self, query, category, max_results=6, domains=None):
        self.calls.append((query, category))
        if self.error:
            raise SearchError("down")
        return self.results

    async def extract(self, urls, query):
        self.extracted = urls
        if self.extract_error:
            raise SearchError("down")
        return {urls[0]: "TO'LIQ SAHIFA: 1 USD = 12 650 so'm"}


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
    name_en="Chinor Hotel", destination_en="Andijan",
))
DUBAI = Intent("book", booking=BookingRequest(
    name="Dubaydagi 5 yulduzli mehmonxona", city="Dubay", category="hotel",
    checkin=datetime(2026, 10, 30).date(), guests=2, destination_en="Dubai", stars=5,
))


class RoutingSearcher(FakeSearcher):
    """booking.com'ga cheklangan qidiruv — mehmonxona sahifasi, qolgani — aloqa raqamlari."""

    def __init__(self, page=True):
        super().__init__()
        self.page = page

    async def search(self, query, category, max_results=6, domains=None):
        self.calls.append((query, category, domains))
        if domains == ["booking.com"]:
            url = "https://www.booking.com/hotel/uz/chinor.html" if self.page else "https://www.booking.com/city/uz/andijan.html"
            return [SearchResult("CHINOR HOTEL", url, "")]
        return [SearchResult("Chinor", "https://chinor.uz", "Tel: +998 74 223 45 67")]


async def test_book_specific_hotel_opens_its_page_and_finds_contacts():
    searcher = RoutingSearcher()
    reply = await handle_text("Chinor hotel bron qil", FakeAI(BOOK), FakeStore(), NOW, searcher)
    assert reply.kind == "booking"
    assert reply.url.startswith("https://www.booking.com/hotel/uz/chinor.html?checkin=2026-10-30")
    assert "📞 +998 74 223 45 67 — chinor.uz" in reply.text
    assert ("Chinor Hotel Andijan", "general", ["booking.com"]) in searcher.calls
    assert ("CHINOR HOTEL Andijon telefon raqami", "general", None) in searcher.calls


async def test_book_hotel_page_not_found_falls_back_to_city_list():
    reply = await handle_text("bron qil", FakeAI(BOOK), FakeStore(), NOW, RoutingSearcher(page=False))
    assert reply.url.startswith("https://www.booking.com/searchresults.html?ss=Andijan")
    assert "sahifasi topilmadi" in reply.text


async def test_book_generic_hotel_uses_city_list_without_contact_search():
    searcher = RoutingSearcher()
    reply = await handle_text("Dubayda 5 yulduzli mehmonxona bron qil", FakeAI(DUBAI), FakeStore(), NOW, searcher)
    assert "ss=Dubai" in reply.url and "nflt=class%3D5" in reply.url
    assert searcher.calls == []  # aniq nom yo'q — tasodifiy raqam qidirilmaydi
    assert "📞" not in reply.text


async def test_book_without_searcher_or_on_error_still_prepares_link():
    reply = await handle_text("bron qil", FakeAI(BOOK), FakeStore(), NOW)
    assert reply.kind == "booking" and "ss=Andijan" in reply.url
    reply = await handle_text("bron qil", FakeAI(BOOK), FakeStore(), NOW, FakeSearcher(error=True))
    assert reply.kind == "booking" and "ss=Andijan" in reply.url


RATE = Intent("search", title="Bugungi dollar kursi", category="general", query="dollar kursi bugun")


async def test_general_question_gets_answer_from_page_texts():
    searcher = FakeSearcher()
    ai = FakeAI(RATE, answer=Answer(True, "1 $ = 12 650 so'm [1].", (0,)))
    reply = await handle_text("dollar kursi", ai, FakeStore(), NOW, searcher)
    assert reply.kind == "search"
    assert reply.text.startswith("🔎 <b>Bugungi dollar kursi</b>\n\n1 $ = 12 650 so'm [1].")
    assert '[1] <a href="https://r1.com">r1.com</a> — Natija 1' in reply.text
    assert searcher.extracted == ["https://r1.com", "https://r2.com"]
    first_source_text = ai.answer_sources[0][1]
    assert first_source_text == "TO'LIQ SAHIFA: 1 USD = 12 650 so'm"
    assert len(ai.answer_sources) == 4


async def test_answer_works_when_page_reading_fails():
    ai = FakeAI(RATE, answer=Answer(True, "Javob [2].", (1,)))
    reply = await handle_text("dollar kursi", ai, FakeStore(), NOW, FakeSearcher(extract_error=True))
    assert "Javob [2]." in reply.text
    assert ai.answer_sources[0][1] == ""  # sahifa o'qilmadi — qisqa parcha ishlatildi


async def test_answer_not_found_shows_sources():
    reply = await handle_text("dollar kursi", FakeAI(RATE, answer=Answer(False)), FakeStore(), NOW, FakeSearcher())
    assert uz.ANSWER_NOT_FOUND in reply.text and "[4] " in reply.text


async def test_answer_ai_error_falls_back_to_result_list():
    reply = await handle_text("dollar kursi", FakeAI(RATE, answer=None), FakeStore(), NOW, FakeSearcher())
    assert "1. <b>Natija 1</b>" in reply.text
