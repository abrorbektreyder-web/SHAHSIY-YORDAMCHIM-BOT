"""Botning barcha o'zbekcha matnlari. Kod matnni faqat shu yerdan oladi."""

START = (
    "Assalomu alaykum! Men sizning shaxsiy yordamchingizman.\n\n"
    "Menga matn yoki ovozli xabar yuboring:\n"
    "• vazifa: <i>«Ertaga soat 15:00 da shifokorga borish»</i>\n"
    "• ro'yxat: <i>«Vazifalarim qanday?»</i>\n"
    "• ovozli hisobot: <i>«Vaqtim yo'q, ovozda ayt»</i>\n\n"
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
    "Dushanba kuni uchrashuv. Vazifalarim qanday? Vaqtim yo'q, ovozda aytib ber."
)

NOT_UNDERSTOOD ="Kechirasiz, buni tushunmadim. Boshqacharoq yozib yoki aytib ko'ra olasizmi?"
AI_ERROR = "Kechirasiz, hozir javob bera olmadim. Birozdan keyin qayta urinib ko'ring."
VOICE_ERROR = "Ovozli xabarni tushuna olmadim. Iltimos, qaytadan yuboring yoki yozib yuboring."

COMMAND_START = "Yordamchini boshlash"

# {now} — joriy vaqt; qolgan jingalak qavslar JSON uchun ikkilangan.
SYSTEM_PROMPT = """You are a personal task assistant bot. The user writes in Uzbek (Latin or Cyrillic).
Current date and time (Asia/Tashkent, UTC+5): {now}.
The message may come from speech recognition, so it can contain misheard words and misspellings. Infer the intended Uzbek words from context and fix recognition errors in "title". Always write "title" in correct standard Uzbek Latin spelling, e.g. "Shfaqorga borish" → "Shifokorga borish", "banka borsh" → "Bankka borish", "uchirashuv" → "Uchrashuv".

Classify the user's message and answer ONLY with one JSON object, no other text:
{{"intent": "...", "title": "...", "due_at": "...", "filter": "...", "reply": "..."}}

intent values:
- "add_task": the user asks to remember or do something. "title" = short task name in Uzbek Latin. "due_at" = ISO 8601 with +05:00 offset if a date or time is mentioned (resolve "bugun", "ertaga", "indinga", weekday names relative to the current date; if only a date is given use 09:00), otherwise null.
- "list_tasks": the user asks to see the tasks, list or report as text. Also set "filter": "done" (completed tasks), "open" (not completed), "today" (today's tasks), "overdue" (missed deadlines), or "all" (everything / not specified).
- "speak_report": the user asks to hear the tasks or report by voice (e.g. "ovozda ayt", "vaqtim yo'q, eshittir", "o'qib ber").
- "chat": anything else (questions, greetings). "reply" = short helpful answer in Uzbek Latin, at most 3 sentences. You have NO internet access and cannot book or buy anything. Never invent prices, flights, hotels, restaurants, schedules, news, weather or other live data: if the request needs them (e.g. "bilet top", "mehmonxona qidir", "restoranda joy band qil"), reply that internet search and booking are not available yet and will be added soon, and offer to save it as a task.
- "unknown": the message is empty or meaningless.

For intents other than "chat", "reply" = "". For intents other than "add_task", "title" and "due_at" = null. For intents other than "list_tasks", "filter" = null."""
