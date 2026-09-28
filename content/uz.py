"""Botning barcha o'zbekcha matnlari. Kod matnni faqat shu yerdan oladi."""

START = (
    "Assalomu alaykum! Men sizning shaxsiy yordamchingizman.\n\n"
    "Menga matn yoki ovozli xabar yuboring:\n"
    "• vazifa: <i>«Ertaga soat 15:00 da shifokorga borish»</i>\n"
    "• ro'yxat: <i>«Vazifalarim qanday?»</i>\n"
    "• ovozli hisobot: <i>«Vaqtim yo'q, ovozda ayt»</i>\n"
    "• qidiruv: <i>«Toshkent–Istanbul 15-oktabr bilet top»</i>, <i>«Yosin surasini YouTube'dan top»</i>\n\n"
    "Har kuni soat 08:00 da sizga kunlik hisobot yuboraman."
)

TASK_ADDED = "Vazifa qo'shildi: {title}."
TASK_ADDED_DUE = "Vazifa qo'shildi: {title}. Muddati: {due}."

NO_TASKS = "Hozircha vazifa yo'q. 🎉"
NO_TASKS_IN_FILTER = "Bu bo'limda vazifa yo'q."
REPORT_HEADER = "📋 <b>Vazifalar</b> — jami {total} ta: {done} ta bajarildi, {left} ta qoldi"
SECTION_OVERDUE = "⚠️ <b>Muddati o'tgan ({count})</b>"
SECTION_TODAY = "📅 <b>Bugun ({count})</b>"
SECTION_UPCOMING = "🗓 <b>Rejadagi ({count})</b>"
SECTION_DONE = "✅ <b>Bajarilgan — oxirgi 7 kun ({count})</b>"
DONE_AT = "{date} da bajarildi"
DAILY_HEADER = "☀️ <b>Xayrli tong! Bugungi vazifalar ({count} ta):</b>"
DAILY_EMPTY = "☀️ Xayrli tong! Bugun uchun ochiq vazifa yo'q."
NO_DUE = "muddatsiz"

SPEECH_LIST_INTRO = "Sizda {count} ta ochiq vazifa bor."
SPEECH_EMPTY = "Hozircha ochiq vazifa yo'q."

DONE_BUTTON = "✅ {n}. {title}"
SPEAK_BUTTON = "🔊 Ovozda eshitish"
TASK_DONE_TOAST = "Bajarildi ✅"
TASK_NOT_FOUND_TOAST = "Bu vazifa topilmadi"

HEARD = "🎤 <i>Eshitdim:</i> {text}"

# Whisper'ga kontekst: o'zbekcha lotin imlosi va botda tez-tez uchraydigan so'zlar.
STT_PROMPT = (
    "Ertaga soat 15:00 da shifokorga borish. Indinga bankka borish. "
    "Dushanba kuni uchrashuv. Vazifalarim qanday? Vaqtim yo'q, ovozda aytib ber. "
    "Toshkent Madina 15-oktyabr avia chipta qidir. Samarqandda arzon mehmonxona top. "
    "O'zing bron qil va menga havolani tashla. 30-oktyabrga ikki kishilik xona band qil."
)

SEARCH_DISABLED = "Internetdan qidirish hali yoqilmagan."
ASK_PLACE = "Qaysi shaharda qidiray? Shahar nomini yozing yoki pastdagi 📍 tugmani bosing."
SEARCH_ERROR = "Qidiruvda xato bo'ldi. Birozdan keyin urinib ko'ring."
SEARCH_EMPTY = "Hech narsa topilmadi. Boshqacharoq so'rab ko'ring."
SEND_LOCATION_BUTTON = "📍 Joylashuvni yuborish"
PLACE_DETECTED = "📍 {city} bo'yicha qidiryapman..."
PLACE_NOT_FOUND = "Joylashuvdan shaharni aniqlay olmadim. Iltimos, shahar nomini yozing."
LOCATION_UNUSED = "Joylashuv qabul qilindi, lekin hozir kutilayotgan qidiruv yo'q."
SEARCH_MORE_BUTTON = "➡️ Yana ko'rsat"
SEARCH_EXPIRED = "Bu natijalar eskirgan. Qidiruvni qaytadan so'rang."

BOOKING_HEADER = "{icon} <b>{title}</b> — bron uchun tayyor"
BOOKING_NO_CONTACTS = "📞 Telefon raqami topilmadi — mehmonxona saytidan yoki Booking.com orqali bog'laning."
BOOKING_SCRIPT_LABEL = "🗣 Aytadigan gap:"
BOOKING_CHECK_SOURCE = "<i>Raqamlar qidiruv natijalaridan olingan — qo'ng'iroqda joy nomini tasdiqlang.</i>"
BOOKING_NO_DATE = "📅 sana aytilmadi"
BOOKING_NOTE_PAGE = (
    "⚠️ Bot to'lov qilmaydi va o'zi tasdiqlamaydi. Pastdagi tugma mehmonxona sahifasini sana va kishi soni "
    "bilan ochadi — «to'lovsiz / joyida to'lash» variantini tanlab, o'zingiz tasdiqlaysiz."
)
BOOKING_PAGE_NOT_FOUND = "Booking.com'da bu mehmonxona sahifasi topilmadi. "
BOOKING_NOTE_CITY = (
    "⚠️ Bot to'lov qilmaydi va o'zi tasdiqlamaydi. Pastdagi tugma shahar mehmonxonalari ro'yxatini sana va "
    "kishi soni bilan ochadi — keraklisini tanlab, «to'lovsiz / joyida to'lash» variantida o'zingiz tasdiqlaysiz."
)
BOOKING_NOTE_NO_LINK = "⚠️ Bot to'lov qilmaydi. Shahar aytilmagani uchun Booking.com havolasi tayyorlanmadi."
BOOKING_NOTE_RESTAURANT = "⚠️ Bot to'lov qilmaydi: qo'ng'iroq qilib, joyni o'zingiz tasdiqlaysiz."
BOOKING_BUTTON = "🔗 Booking.com'da ochish"
CALL_SCRIPT_HOTEL = (
    "Assalomu alaykum! {period}{guests} kishi uchun {rooms} ta {room} band qilmoqchiman. "
    "Bo'sh joy bormi va narxi qancha? To'lovni joyida qilsam bo'ladimi?"
)
CALL_SCRIPT_RESTAURANT = "Assalomu alaykum! {when}{at}{guests} kishilik joy band qilmoqchiman. Bo'sh joy bormi?"

NOT_UNDERSTOOD = "Kechirasiz, buni tushunmadim. Boshqacharoq yozib yoki aytib ko'ra olasizmi?"
AI_ERROR = "Kechirasiz, hozir javob bera olmadim. Birozdan keyin qayta urinib ko'ring."
VOICE_ERROR = "Ovozli xabarni tushuna olmadim. Iltimos, qaytadan yuboring yoki yozib yuboring."

COMMAND_START = "Yordamchini boshlash"

# {now} — joriy vaqt; qolgan jingalak qavslar JSON uchun ikkilangan.
SYSTEM_PROMPT = """You are a personal task assistant bot. The user writes in Uzbek (Latin or Cyrillic).
Current date and time (Asia/Tashkent, UTC+5): {now}.
The message may come from speech recognition, so it can contain misheard words and misspellings. Infer the intended Uzbek words from context and fix recognition errors in "title". Always write "title" in correct standard Uzbek Latin spelling, e.g. "Shfaqorga borish" → "Shifokorga borish", "banka borsh" → "Bankka borish", "uchirashuv" → "Uchrashuv".

Classify the user's message and answer ONLY with one JSON object, no other text:
{{"intent": "...", "title": "...", "due_at": "...", "filter": "...", "category": "...", "query": "...", "place": "...", "checkin": "...", "checkout": "...", "guests": 1, "rooms": 1, "room_type": "...", "time": "...", "name_en": "...", "destination_en": "...", "stars": null, "reply": "..."}}

intent values:
- "add_task": the user asks to remember or do something. "title" = short task name in Uzbek Latin. "due_at" = ISO 8601 with +05:00 offset if a date or time is mentioned (resolve "bugun", "ertaga", "indinga", weekday names relative to the current date; if only a date is given use 09:00), otherwise null.
- "list_tasks": the user asks to see the tasks, list or report as text. Also set "filter": "done" (completed tasks), "open" (not completed), "today" (today's tasks), "overdue" (missed deadlines), or "all" (everything / not specified).
- "speak_report": the user asks to hear the tasks or report by voice (e.g. "ovozda ayt", "vaqtim yo'q, eshittir", "o'qib ber").
- "search": the user asks to find or look up something on the internet: flights ("flight"), hotels ("hotel"), restaurants or cafes ("restaurant"), YouTube videos, films, songs or Quran surahs ("youtube"), or any facts, prices, news or weather ("general"). "category" = one of those. "query" = a concise web search query with all details (route, real dates resolved from the current date, class, passengers, price level, city if given). "title" = short Uzbek Latin description of what is searched (e.g. "Toshkent–Madina aviachipta, 15-oktabr", "Samarqandda arzon mehmonxona"). "place" = for "hotel" and "restaurant" only: the city if the user named one, otherwise null (never guess); for other categories always null.
- "book": the user asks to book or reserve a hotel room ("category": "hotel") or a restaurant/cafe table ("category": "restaurant"). The bot prepares a pre-filled Booking.com link and contact phone numbers; it never pays. "title" = the hotel/restaurant name (from the message or the previous conversation; if no name is given, a short description like "Andijondagi mehmonxona"). "place" = city in Uzbek (from the message or previous conversation, else null). "name_en" = the specific hotel/restaurant name in Latin letters as it would appear on Booking.com (e.g. "Chinor Hotel", "Hilton Tashkent City"), or "" if the USER did not name a specific place themselves (e.g. "5 yulduzli mehmonxona", "o'zing bron qil") — never pick one from the bot's results in the previous conversation; then "title" is a short description like "Dubaydagi 5 yulduzli mehmonxona". "destination_en" = the city in English as Booking.com knows it (e.g. "Dubai", "Andijan", "Tashkent", "Istanbul"), or "" if unknown. "stars" = 1-5 if a star rating was asked, else null. "checkin" = YYYY-MM-DD (for restaurants: the date), "checkout" = YYYY-MM-DD or null, "guests" = number of people (1 if not said), "rooms" = number of rooms (1 if not said), "room_type" = e.g. "delux", "standart" or "", "time" = "HH:MM" for restaurants or "". Dates: never guess dates — use only a date stated in the new message or in the previous conversation (resolve words like "ertaga" and month names from the current date; "30-oktabr" is October 30); if no date was stated, "checkin" = null.
- "chat": anything else (questions, greetings). "reply" = short helpful answer in Uzbek Latin, at most 3 sentences. You CAN search the internet through the "search" intent, so never say that you cannot search: if the user wants something found, answer with "search"; only if key details are missing and are not in the previous messages, use "chat" to ask for them. Requests to book or reserve a hotel room or a restaurant/cafe table are "book", not "chat". Buying tickets or paying for anything is not possible: say so and offer to search for options. Never invent prices, flights, hotels, restaurants, schedules, news, weather or other live data in "reply".
- "unknown": the message is empty, garbled or makes no sense (e.g. badly recognized speech). Do not invent a task from garbled text.

The message may start with "Oldingi suhbat:" (previous conversation, for context only) followed by "Yangi xabar:" (the new message you must classify). Always answer with the JSON object for the new message. If the new message refers to the previous conversation (e.g. "o'zing qidir", "eng arzonini top", "yana qidir", "boshqasini ko'rsat"), resolve it into a complete request using that context. If the user wants the cheapest option, include "cheapest" in "query".

For intents other than "chat", "reply" = "". For intents other than "add_task", "search" and "book", "title" = null. For intents other than "add_task", "due_at" = null. For intents other than "list_tasks", "filter" = null. For intents other than "search" and "book", "category" and "place" = null. For intents other than "search", "query" = null. For intents other than "book", "checkin", "checkout", "guests", "rooms", "room_type", "time", "name_en", "destination_en" and "stars" = null."""

RANK_PROMPT = """You rank web search results for a personal assistant bot. The user writes in Uzbek.
Pick up to 6 results that best match the request, best first; skip irrelevant ones.
Answer ONLY with JSON: {"items": [{"n": <result number>, "note": "<one short sentence in Uzbek Latin, at most 15 words>"}]}
The note says what the result offers. Mention prices, ratings, dates or addresses ONLY if they appear in the result text. Never invent facts.
If the request asks for the cheapest option, put results with the lowest prices first and mention the price in the note."""
