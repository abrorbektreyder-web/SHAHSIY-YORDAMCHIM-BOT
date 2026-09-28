# Telegram Shaxsiy Vazifa-Boti — Texnik Reja (1-bosqich)

**Sana:** 2026-09-28
**Holat:** ESKIRGAN — hosting (Render), saqlash (Supabase) va kutubxona (aiogram) bo'yicha yakuniy qarorlar `2026-09-28-telegram-vazifa-boti-TZ.md` faylida. Shu hujjat asosiy hisoblanadi.
**Bosqich:** 1/4 — Vazifa, eslatma va ovozli yordamchi

---

## 1. Maqsad

Foydalanuvchi uchun shaxsiy Telegram bot: matn yoki ovozli xabar orqali vazifa qabul qiladi, saqlaydi, so'ralganda ro'yxatini ko'rsatadi, har kuni belgilangan vaqtda eslatma yuboradi. Faqat bitta foydalanuvchi (bot egasi) uchun ishlaydi.

**Keyingi bosqichlar (bu hujjat qamrovidan tashqari, faqat eslatma sifatida):**
- 2-bosqich: internetdan qidiruv (aviabilet, mehmonxona narxlari va h.k.) — faqat variant/link ko'rsatadi, sotib olmaydi.
- 3-bosqich: istalgan vaqtga eslatma qo'yish (nafaqat kunlik 08:00).
- 4-bosqich: pulsiz va bekor qilinadigan bandlovlar (restoran/kafe stoli) — pul to'lovisiz, faqat bron.

## 2. Foydalanuvchi bilan kelishilgan qarorlar

| Mavzu | Qaror |
|---|---|
| Vazifa maydonlari | Nomi + muddati (deadline) |
| Bajarilgan deb belgilash | Inline tugma ("✅ Bajarildi") |
| Kirish huquqi | Faqat bot egasi (Telegram user ID bo'yicha tekshiriladi), boshqalarga javob berilmaydi |
| Kunlik hisobot vaqti | Har kuni 08:00, Asia/Tashkent vaqt zonasi |
| Ovozli xabar (kirish) | Qabul qilinadi, matnga o'giriladi |
| Ovozli javob (chiqish) | Qisqa javoblar — ovoz bilan; uzun ro'yxat/hisobot — matn bilan (+ "🔊 Ovozda eshitish" tugmasi yoki ovozli buyruq bilan ovozga aylantirish) |
| Saqlash joyi | Bitta JSON fayl (`data/tasks.json`), murakkab bazama'lumot shart emas |
| Joylashuv (hosting) | Replit (Reserved VM / Always-On deployment) |
| Modellar | Nutqni matnga: `google/gemini-3.5-transcribe`; matnni tushunish: `google/gemini-3.5-flash-lite`; matnni nutqqa: `google/gemini-3.8-flash-tts` — barchasi OpenRouter orqali |

## 3. Arxitektura

Bitta doimiy ishlaydigan Python jarayoni:

```
Telegram foydalanuvchisi
      |
      v
[Telegram Bot API]  <-- python-telegram-bot kutubxonasi (long polling)
      |
      v
[main.py — xabar routeri]
      |-- ovozli xabar bo'lsa --> [OpenRouter: gemini-3.5-transcribe] --> matn
      |
      v
[OpenRouter: gemini-3.5-flash-lite] --> niyatni aniqlash (yangi vazifa / ro'yxat so'rovi / oddiy gap)
      |
      |-- yangi vazifa --> [tasks_store.py] --> data/tasks.json ga yoziladi
      |-- ro'yxat so'rovi --> [tasks_store.py] --> o'qiladi --> Telegram xabari (matn + tugmalar)
      |-- oddiy gap --> to'g'ridan-to'g'ri javob matni
      |
      v
javob qisqami? --> [OpenRouter: gemini-3.8-flash-tts] --> ovozli xabar
javob uzunmi?  --> matn xabar (+ "🔊 Ovozda eshitish" tugmasi)

[scheduler.py] — python-telegram-bot JobQueue orqali har kuni 08:00 (Asia/Tashkent)
      --> data/tasks.json o'qiydi --> tugallanmagan vazifalar ro'yxatini matn qilib yuboradi
```

## 4. Komponentlar

- **`main.py`** — botni ishga tushiradi, Telegram handlerlarini ro'yxatdan o'tkazadi (matn, ovoz, tugma bosish, `/start`).
- **`auth.py`** — kelgan xabarning `user_id`'sini `OWNER_ID` bilan solishtiradi; mos kelmasa, javob bermay o'tkazib yuboradi.
- **`ai_client.py`** — OpenRouter'ga uchta so'rov turi uchun funksiyalar: `transcribe(audio) -> text`, `understand(text) -> intent+javob`, `speak(text) -> audio`.
- **`tasks_store.py`** — `data/tasks.json` bilan ishlash: `add_task`, `list_open_tasks`, `mark_done`. Fayl bo'lmasa, bo'sh ro'yxat bilan yaratadi.
- **`scheduler.py`** — kunlik 08:00 (Asia/Tashkent) vazifasini ro'yxatdan o'tkazadi.
- **`data/tasks.json`** — vazifalar ro'yxati: `[{id, title, due_at, done, created_at}]`.

## 5. Ma'lumot oqimi (misol)

1. Foydalanuvchi: "Ertaga soat 15:00 da shifokorga borish" (matn yoki ovoz).
2. Ovoz bo'lsa → `transcribe()` → matnga aylanadi.
3. `understand()` matnni tahlil qiladi → `{intent: "add_task", title: "Shifokorga borish", due_at: "2026-09-29T15:00"}`.
4. `tasks_store.add_task(...)` chaqiriladi, `tasks.json`ga yoziladi.
5. Qisqa tasdiq matni tuziladi: "Vazifa qo'shildi: Shifokorga borish — ertaga, 15:00".
6. Bu qisqa javob bo'lgani uchun `speak()` orqali ovozga aylantirilib, ovozli xabar sifatida yuboriladi.

## 6. Xatoliklarni boshqarish

- OpenRouter so'rovi muvaffaqiyatsiz bo'lsa (tarmoq xatosi, limit) — foydalanuvchiga oddiy xabar: "Kechirasiz, hozir javob bera olmadim, birozdan keyin qayta urinib ko'ring." Dastur to'xtamaydi.
- Niyat aniqlanmasa (`understand()` noaniq javob qaytarsa) — bot "Buni tushunmadim, boshqacharoq yozib/ayta olasizmi?" deb so'raydi, vazifa sifatida saqlamaydi.
- `tasks.json` fayli shikastlangan/o'qib bo'lmasa — zaxira sifatida bo'sh ro'yxatdan boshlanadi, xato log'ga yoziladi (foydalanuvchiga ko'rsatilmaydi, lekin yo'qolmaydi — fayl ustiga yozishdan oldin eski nusxa saqlab qo'yiladi).
- Ruxsatsiz foydalanuvchidan xabar kelsa (owner emas) — bot indamaydi (hech qanday javob yubormaydi), log'da qayd etiladi.

## 7. Testlash rejasi

- `tasks_store.py` uchun avtomatik testlar (TDD): vazifa qo'shish, ro'yxatni olish, bajarilgan deb belgilash, bo'sh/mavjud bo'lmagan faylni to'g'ri boshqarish.
- `ai_client.py` uchun: OpenRouter chaqiruvlari mock (soxta) javoblar bilan sinaladi — haqiqiy tarmoqqa har safar chiqmasdan mantiq to'g'riligini tekshirish uchun.
- Yakunida: haqiqiy Telegram bot bilan **1 ta qo'lda sinov** — bitta matnli vazifa va bitta ovozli vazifa yuborib, javoblarni tekshirish (foydalanuvchi ishtirokida yoki ishlab chiquvchi ko'rsatadi).

## 8. Kerakli maxfiy ma'lumotlar (Replit "Secrets"ga kiritiladi, kodga yozilmaydi)

- `TELEGRAM_BOT_TOKEN`
- `OPENROUTER_API_KEY`
- `OWNER_TELEGRAM_ID`

## 9. Qamrovdan tashqari (hozircha qilinmaydi)

- Ko'p foydalanuvchilik.
- Internetdan qidiruv, bron qilish, to'lov (2/4-bosqichlar).
- Istalgan vaqtga eslatma qo'yish (hozircha faqat kunlik 08:00 hisobot) — 3-bosqich.
- Email/pochta integratsiyasi.
