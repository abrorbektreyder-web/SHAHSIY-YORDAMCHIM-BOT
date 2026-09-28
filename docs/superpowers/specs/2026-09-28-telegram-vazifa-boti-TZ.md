# TEXNIK TOPSHIRIQ (TZ)
## Shaxsiy Telegram Vazifa-Yordamchi Boti — 1-bosqich

| | |
|---|---|
| **Loyiha nomi** | Shaxsiy Telegram Vazifa-Boti (kodli nomi: `vazifa-bot`) |
| **Versiya** | 1.0 (1-bosqich) |
| **Sana** | 2026-09-28 |
| **Mijoz / Egasi** | Yakka foydalanuvchi (bot faqat bitta shaxs uchun ishlaydi) |
| **Holat** | Tasdiqlangan, ishga tushirishga tayyor |

---

## 1. LOYIHA HAQIDA

### 1.1 Maqsad
Telegram orqali ishlaydigan, sun'iy intellekt asosidagi shaxsiy yordamchi bot yaratish. Foydalanuvchi botga matn yoki ovozli xabar orqali vazifa beradi; bot uni tushunadi, saqlaydi, so'ralganda ro'yxatini ko'rsatadi va har kuni belgilangan vaqtda eslatma yuboradi.

### 1.2 Muammo, nimani hal qiladi
Foydalanuvchi kundalik ishlarini (uchrashuv, ishlar, eslatmalar) yozib boradigan, buni og'zaki (ovozli) tarzda ham qila oladigan, va o'zi eslatib turadigan vositaga muhtoj — bu vosita doim qo'l ostida (telefon/Telegram) bo'lishi kerak.

### 1.3 Loyiha chegaralari (Scope)
**Kiradi (1-bosqich):** vazifa qo'shish, ro'yxatni ko'rish, bajarilgan deb belgilash, kunlik avtomatik hisobot, ovozli kirish/chiqish, faqat egasiga xizmat qilish.

**Kirmaydi (keyingi bosqichlar uchun qoldirilgan):** internetdan qidiruv, aviabilet/mehmonxona/restoran narxlarini topish, pulsiz joy bandlash, email integratsiyasi, ko'p foydalanuvchilik, istalgan vaqtga eslatma qo'yish (hozircha faqat kunlik 08:00).

---

## 2. TEXNOLOGIYALAR STEKI (Tech Stack)

| Qatlam | Texnologiya | Nima uchun tanlangan |
|---|---|---|
| Dasturlash tili | **Python 3.12** | Telegram bot va AI integratsiyalari uchun eng keng qo'llab-quvvatlanadigan til, tayyor kutubxonalar ko'p |
| Telegram bilan aloqa | **`aiogram` 3.x** (async) | Egasining TARGET-AUDIT loyihasida Render'da sinalgan; `config.py`, `main.py` (polling/webhook + `/health`) patternlari qayta ishlatiladi |
| AI modellar provayderi | **OpenRouter API** (`https://openrouter.ai/api/v1`) | Bitta API kaliti orqali bir nechta AI modelga (matn, nutq-matn, matn-nutq) kirish imkonini beradi |
| Nutqni matnga o'girish (STT) | **Sinov davri: `whisper-large-v3` (Groq, bepul)**; keyin ixtiyoriy `google/gemini-3.5-transcribe` (OpenRouter) | Whisper o'zbek tilini va Telegram `ogg` formatini qo'llaydi; Groq bepul tarifida kuniga 2000 so'rov. `STT_PROVIDER` bilan tanlanadi |
| Matnni tushunish / suhbat | **Sinov davri: `qwen/qwen3.8-27b` (Groq, bepul)**; keyin ixtiyoriy `google/gemini-3.5-flash-lite` (OpenRouter) | Groq juda tez, bepul tarifida kuniga 1000 so'rov, JSON rejimini qo'llaydi. `LLM_PROVIDER` / `LLM_MODEL` bilan tanlanadi |
| Matnni nutqqa o'girish (TTS) | **`google/gemini-3.8-flash-tts`** (OpenRouter orqali, pullik) | Groq'da o'zbekcha TTS yo'q. `OPENROUTER_API_KEY` bo'sh bo'lsa, bot barcha javoblarni matnda yuboradi |
| Ma'lumot saqlash | **Supabase (PostgreSQL)**, `asyncpg` orqali, alohida `vazifa` sxemasi | Render bepul tarifida disk vaqtinchalik (qayta ishga tushganda fayl o'chadi); egasida Supabase hisobi allaqachon bor, TARGET-AUDIT'ning `bot` sxemasiga tegmaydi |
| Vaqt rejalashtirish | **`asyncio`** fon vazifasi (08:00 gacha kutadi, yuboradi, takrorlaydi) | Qo'shimcha kutubxonasiz, bitta foydalanuvchi uchun yetarli |
| Muhit o'zgaruvchilari | **`.env` (lokal) / Render Environment** | Maxfiy kalitlarni kodga yozmaslik uchun |
| Hosting (joylashtirish) | **Render.com** — Web Service, webhook rejimi, bepul tarif + UptimeRobot | Egasiga tanish platforma; UptimeRobot har 5 daqiqada `/health`ni tekshirib, servisni uxlatmaydi (08:00 hisobot o'z vaqtida ketishi uchun shart) |
| Versiyalarni kuzatish | Git (ixtiyoriy, hozircha ishlatilmayapti) | Kelajakda kod tarixini saqlash uchun tavsiya etiladi |

### 2.1 Asosiy Python kutubxonalari (`requirements.txt`)

```
aiogram>=3.31,<4
asyncpg>=0.30,<1
httpx>=0.27,<1
python-dotenv>=1.2,<2
pytest>=8
pytest-asyncio>=1.4
```

> Eslatma: `aiogram`, `asyncpg`, `python-dotenv`, `pytest` — TARGET-AUDIT bilan bir xil versiyalar. Yangi qo'shilgani faqat `httpx` (OpenRouter'ga so'rov yuborish uchun).

---

## 3. ARXITEKTURA

```
                        ┌──────────────────────┐
                        │   Telegram foydal.    │
                        └──────────┬────────────┘
                                   │ matn / ovoz
                                   v
                     ┌─────────────────────────────┐
                     │   Telegram Bot API           │
                     │   (Render: webhook,           │
                     │    lokal: polling)            │
                     └──────────────┬────────────────┘
                                    v
                     ┌─────────────────────────────┐
                     │   main.py (router)            │◄──── auth.py (faqat OWNER_ID)
                     └──────────────┬────────────────┘
                     ovoz bo'lsa    │    matn bo'lsa
                          v         │         │
              ┌───────────────────┐│          │
              │ ai_client.        ││          │
              │ transcribe()      ││          │
              │ (gemini-3.5-      ││          │
              │  transcribe)      ││          │
              └─────────┬─────────┘│          │
                        └──────────┴──────────┘
                                   v
                     ┌─────────────────────────────┐
                     │ ai_client.understand()        │
                     │ (gemini-3.5-flash-lite)       │
                     │ → intent: add_task /          │
                     │   list_tasks / chit_chat /     │
                     │   speak_report                │
                     └──────────────┬────────────────┘
                                    v
            ┌───────────────────────┴───────────────────────┐
            v                                                v
  ┌───────────────────┐                          ┌───────────────────────┐
  │ db.py               │                          │ to'g'ridan-to'g'ri     │
  │ (Supabase: vazifa.  │                          │ javob matni tuziladi   │
  │  tasks jadvali)     │                          │                        │
  │ add/list/mark_done  │                          └───────────┬───────────┘
  └──────────┬──────────┘                                      │
             v                                                 v
   javob qisqami? ──── ha ───► ai_client.speak() (gemini-3.8-flash-tts) ──► ovozli xabar
             │
             no (uzun ro'yxat/hisobot)
             v
   matn + "✅ Bajarildi" / "🔊 Ovozda eshitish" tugmalari bilan yuboriladi

   ┌─────────────────────────────────────────────┐
   │ scheduler.py — asyncio fon vazifasi, har kuni │
   │ 08:00 (Asia/Tashkent) → db.py'dan o'qiydi →   │
   │ egasiga matn hisobot yuboradi                  │
   └─────────────────────────────────────────────┘
```

### 3.1 Fayl tuzilishi

```
vazifa-bot/
├── bot/
│   ├── main.py          # kirish nuqtasi: polling/webhook + /health (TARGET-AUDIT'dan moslashtirilgan)
│   ├── config.py        # .env validatsiyasi (TARGET-AUDIT'dan moslashtirilgan)
│   ├── scheduler.py     # Toshkent vaqti, kunlik 08:00 hisobot sikli (asyncio)
│   ├── models.py        # Task
│   ├── views.py         # ro'yxat / hisobot / nutq matnlari
│   ├── db.py            # Supabase (asyncpg): add_task / list_open_tasks / mark_done
│   ├── ai_client.py     # OpenRouter: transcribe / understand / speak
│   ├── logic.py         # xabar → javob qarori (Telegram'ga bog'liq emas)
│   ├── keyboards.py     # "✅ Bajarildi", "🔊 Ovozda eshitish" tugmalari
│   └── handlers.py      # Telegram handlerlar, faqat OWNER_ID filtri shu yerda
├── content/
│   └── uz.py            # barcha o'zbekcha matnlar va AI ko'rsatmasi bitta joyda
├── tests/               # har modul uchun pytest testlari
├── requirements.txt
├── pytest.ini
├── render.yaml          # Render Blueprint
├── .env.example
└── .gitignore
```

Batafsil ish rejasi (har fayl kodi va testlari bilan): `docs/superpowers/plans/2026-09-28-vazifa-bot.md`.

---

## 4. FUNKSIONAL TALABLAR

| № | Talab | Qabul mezoni |
|---|---|---|
| F1 | Matnli vazifa qabul qilish | "Ertaga soat 15:00 shifokorga borish" → vazifa nomi va muddati to'g'ri ajratib olinadi |
| F2 | Ovozli vazifa qabul qilish | Ovozli xabar matnga aylantirilib, F1 bilan bir xil natija beradi |
| F3 | Vazifalar hisoboti | Umumiy son (jami / bajarildi / qoldi) va bo'limlar: ⚠️ Muddati o'tgan, 📅 Bugun, 🗓 Rejadagi, ✅ Bajarilgan (oxirgi 7 kun); ✅ tugmasi faqat bajarilmaganlarda. Qisman so'rash mumkin: "bajarilganlar", "bugungi", "muddati o'tganlar", "bajarilmaganlar" |
| F4 | Vazifani bajarilgan deb belgilash | Tugma bosilganda vazifa `done: true` bo'ladi va ro'yxatdan chiqadi |
| F5 | Kunlik avtomatik hisobot | Har kuni 08:00 (Asia/Tashkent) tugallanmagan vazifalar ro'yxati avtomatik yuboriladi |
| F6 | Ovozli javob (qisqa) | Qisqa javoblar (vazifa qo'shildi, suhbat) faqat ovozli xabar sifatida yuboriladi; ovoz yaratilmasa — matn bilan (egasining qarori: "qisqa javoblar ovozli, uzun hisobotlar matn shaklida") |
| F7 | Hisobotni ovozda eshitish | Tugma yoki ovozli buyruq ("vaqtim yo'q, ovozda ayt") orqali oxirgi ro'yxat ovozga aylantiriladi |
| F8 | Faqat egasiga xizmat | `OWNER_ID`dan boshqa `user_id`dan kelgan xabarlarga javob berilmaydi |
| F9 | Oddiy suhbat | Vazifa/ro'yxat bilan bog'liq bo'lmagan xabarlarga ham tabiiy javob qaytariladi |

---

## 5. NOFUNKSIONAL TALABLAR

- **Ishonchlilik:** OpenRouter yoki Telegram tarafidan vaqtinchalik xato bo'lsa, bot ishlashda davom etadi, foydalanuvchiga tushunarli xabar beradi.
- **Xavfsizlik:** Maxfiy kalitlar faqat muhit o'zgaruvchilari (Render Environment) orqali saqlanadi, kodga yoki logga yozilmaydi. Webhook `WEBHOOK_SECRET` bilan himoyalanadi.
- **Tezlik:** Oddiy matnli so'rovga javob — odatda 2-5 soniya ichida (AI model javob tezligiga bog'liq).
- **Til:** Botning barcha javoblari — o'zbek tilida.
- **Doimiy ishlash:** Render bepul tarifi + UptimeRobot (har 5 daqiqada `/health`) orqali 24/7 uyg'oq turadi. Bitta servis oyiga ~720 soat ishlaydi, bepul tarif limiti (750 soat) ichida.

---

## 6. MA'LUMOTLAR TUZILISHI

Supabase, `vazifa` sxemasi (TARGET-AUDIT'ning `bot` sxemasidan alohida, bir xil Supabase loyihasida bo'lishi mumkin):

```sql
CREATE TABLE IF NOT EXISTS vazifa.tasks (
    id          BIGSERIAL PRIMARY KEY,
    title       TEXT        NOT NULL,
    due_at      TIMESTAMPTZ,
    done        BOOLEAN     NOT NULL DEFAULT FALSE,
    done_at     TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Jadval bot birinchi ishga tushganda `init_db()` orqali avtomatik yaratiladi (TARGET-AUDIT'dagi kabi idempotent DDL).

---

## 7. MUHIT O'ZGARUVCHILARI (Secrets)

| Nomi | Tavsif | Qayerdan olinadi |
|---|---|---|
| `BOT_TOKEN` | Yangi botning Telegram tokeni (TARGET-AUDIT botidan **alohida** bot) | @BotFather |
| `GROQ_API_KEY` | Groq API kaliti (bepul) | console.groq.com → API Keys |
| `LLM_PROVIDER` / `STT_PROVIDER` | `groq` yoki `openrouter` | Sinov davrida ikkalasi `groq` |
| `LLM_MODEL` | Matn modeli (bo'sh — provayder standarti) | `qwen/qwen3.8-27b` |
| `OPENROUTER_API_KEY` | OpenRouter API kaliti — **ixtiyoriy**, faqat ovozli javob (TTS) yoki OpenRouter provayderi uchun | openrouter.ai → Keys |
| `OWNER_ID` | Egasining Telegram user ID raqami | @userinfobot (TARGET-AUDIT'dagi qiymat bilan bir xil) |
| `DATABASE_URL` | Supabase ulanish manzili | Supabase → Project Settings → Database (TARGET-AUDIT'dagi bilan bir xil bo'lishi mumkin) |
| `DB_SCHEMA` | Sxema nomi | `vazifa` (o'zgarmas) |
| `MODE` | `polling` (lokal) yoki `webhook` (Render) | `render.yaml` o'rnatadi |
| `WEBHOOK_BASE_URL` | Render servis manzili | Shart emas — Render `RENDER_EXTERNAL_URL`ni o'zi beradi, kod undan foydalanadi |
| `WEBHOOK_SECRET` | Webhook himoya kaliti | Render avtomatik yaratadi (kod uni Telegram qabul qiladigan hex ko'rinishga o'giradi) |

Bular hech qachon kodga yozilmaydi — faqat Render servisining **Environment** bo'limiga kiritiladi (lokal sinov uchun `.env` fayliga, u `.gitignore`da).

---

## 8. LOYIHANI KO'TARISH (DEPLOY QILISH) — QADAMLAR

### 8.1 Tayyorgarlik (egasi bajaradi)
1. @BotFather orqali **yangi** bot yaratish, tokenni olish (TARGET-AUDIT botining tokeni ishlatilmaydi).
2. openrouter.ai'da API kalit olish va hisobga ozgina balans qo'shish (modellar pullik, lekin arzon).
3. `OWNER_ID` va Supabase `DATABASE_URL` — TARGET-AUDIT'dagi qiymatlar qayta ishlatiladi.

### 8.2 Lokal sinov (ishlab chiquvchi bajaradi)
4. Kod yoziladi, `pytest` testlari o'tishi tekshiriladi.
5. `.env` fayli bilan `MODE=polling` rejimida kompyuterda ishga tushirilib, botga 1 ta matnli va 1 ta ovozli sinov vazifasi yuboriladi.

### 8.3 GitHub'ga yuklash
6. Yangi GitHub repo (masalan `vazifa-bot`) yaratiladi va kod push qilinadi (`.env` push qilinmaydi).

### 8.4 Render'ga joylash (egasi bajaradi, ishlab chiquvchi qadam-baqadam yo'l ko'rsatadi)
7. Render → **New → Blueprint** → `vazifa-bot` repo tanlanadi (`render.yaml` avtomatik o'qiladi).
8. Environment bo'limiga maxfiy qiymatlar kiritiladi: `BOT_TOKEN`, `GROQ_API_KEY`, `OWNER_ID`, `DATABASE_URL`. (`OPENROUTER_API_KEY` — ixtiyoriy, ovozli javob kerak bo'lganda keyin qo'lda qo'shiladi.)
9. Deploy logida "Webhook o'rnatildi" chiqqanini va `https://<servis>.onrender.com/health` → `ok` qaytarishini tekshirish.
10. UptimeRobot'da `https://<servis>.onrender.com/health` uchun 5 daqiqalik monitor qo'shiladi.

> ⚠️ Render'ga joylangandan keyin botni **kompyuterda (`MODE=polling`) qayta ishga tushirmang**: polling rejimi Render'dagi webhook'ni o'chirib qo'yadi va bot Render qayta ishga tushmaguncha javob bermay qoladi. Kompyuterda sinash kerak bo'lsa — @BotFather'dan alohida sinov boti oching.

### 8.5 Yakuniy sinov
11. Telegramda botga 1 ta matnli va 1 ta ovozli vazifa yuboriladi, "Ro'yxat" va "✅ Bajarildi" tekshiriladi.
12. Ertasi kuni soat 08:00'da (Toshkent) avtomatik hisobot kelishi tekshiriladi.

---

## 9. TESTLASH REJASI

- **Birlik testlari (unit tests):** `db.py` uchun — vazifa qo'shish, ochiq vazifalarni o'qish, bajarilgan deb belgilash (TARGET-AUDIT'dagi `conftest.py` uslubida); `scheduler.py` uchun — keyingi 08:00 (Asia/Tashkent) vaqtini to'g'ri hisoblash.
- **Mock testlar:** `ai_client.py` funksiyalari haqiqiy OpenRouter'ga chiqmasdan, soxta javoblar bilan tekshiriladi.
- **Qo'lda sinov (manual):** haqiqiy Telegram bot orqali 1 ta matnli + 1 ta ovozli vazifa yuborib, natija ko'rsatiladi.

---

## 10. KELAJAKDAGI BOSQICHLAR (ushbu TZ qamroviga kirmaydi)

| Bosqich | Tavsif |
|---|---|
| 2 | Internetdan qidiruv (aviabilet, mehmonxona narxlari) — faqat ma'lumot/link ko'rsatish |
| 3 | Istalgan vaqtga eslatma qo'yish (nafaqat kunlik 08:00) |
| 4 | Pulsiz, bekor qilinadigan bandlovlar (restoran/kafe) — pul to'lovisiz |

---

## 11. OCHIQ SAVOLLAR / TAVAKKALCHILIKLAR

- OpenRouter'dagi model nomlari (`gemini-3.5-transcribe`, `gemini-3.8-flash-tts` va h.k.) vaqt o'tishi bilan yangilanishi yoki narxi o'zgarishi mumkin — kod ichida bu nomlar bitta joyda (`ai_client.py` boshida) saqlanadi, kerak bo'lsa oson almashtiriladi.
- Render bepul tarifi UptimeRobot bo'lmasa 15 daqiqa harakatsizlikdan keyin "uxlab qoladi" — bu holda 08:00 hisobot ketmaydi va birinchi javob 30-60 soniya kechikadi. UptimeRobot monitori majburiy.
- Bitta Supabase loyihasini TARGET-AUDIT bilan bo'lishish — sxemalar alohida (`bot` va `vazifa`), lekin ulanishlar soni umumiy limitdan foydalanadi. Bitta foydalanuvchi uchun bu muammo emas.
- OpenRouter xarajati — har bir ovozli xabar 3 ta model chaqiruvini (transkripsiya, tushunish, ovoz) talab qiladi. Shaxsiy foydalanishda oyiga bir necha dollardan oshmasligi kutiladi; OpenRouter panelida limit qo'yish tavsiya etiladi.
- Telegram ovozli xabari `ogg/opus` formatida keladi. OpenRouter hujjatida `ogg` qabul qilinadi deb yozilgan, lekin `opus` alohida tilga olinmagan. O'zbek tilini `gemini-3.5-transcribe` tanishi ham hujjatda tasdiqlanmagan. Ikkalasi 9-blokda haqiqiy ovoz bilan tekshiriladi. Ishlamasa, zaxira variant: `openai/whisper-large-v3` (o'zbek tilini qo'llaydi) yoki ovozni `mp3`ga o'girish.

- Groq bepul tarifi limitlari (2026-09 holatiga): `qwen/qwen3.8-27b` — daqiqasiga 30, kuniga 1000 so'rov; `whisper-large-v3` — daqiqasiga 20, kuniga 2000 so'rov, soatiga 7200 soniya audio. Groq'dagi Qwen 3.8 "fikrlovchi" model: JSON rejimida fikrlash matni javobga aralashmaydi, lekin javob vaqtini oshirishi mumkin — 9-blokda o'lchanadi.

---

## 12. BAJARILISH HOLATI

Har bir blok tugaganda va uning testlari o'tganda ☐ → ☑ qilib belgilanadi. Blok raqamlari ish rejasidagi Task raqamlariga mos keladi.

| Blok | Nima qilinadi | Holat | Tekshiruv natijasi |
|---|---|---|---|
| 1 | Loyiha asosi va konfiguratsiya (`config.py`, kutubxonalar) | ☑ | 6/6 test o'tdi |
| 2 | Toshkent vaqti va kunlik 08:00 hisobot sikli (`scheduler.py`) | ☑ | 5/5 test o'tdi |
| 3 | O'zbekcha matnlar va ro'yxat ko'rinishi (`uz.py`, `views.py`) | ☑ | 8/8 test o'tdi |
| 4 | Supabase'da saqlash (`db.py`) | ☑ | 5/5 integratsiya testi haqiqiy Supabase'da o'tdi (`vazifa_test` sxemasi, eu-central-1 pooler) |
| 5 | OpenRouter AI: ovoz→matn, tushunish, matn→ovoz (`ai_client.py`) | ☑ | 16/16 test o'tdi (sun'iy javoblar bilan; haqiqiy OpenRouter — 9-blokda) |
| 6 | Bot mantiqi: vazifa / ro'yxat / suhbat (`logic.py`) | ☑ | 6/6 test o'tdi |
| 7 | Telegram handlerlar va tugmalar (`handlers.py`, `keyboards.py`) | ☑ | 3/3 tugma testi o'tdi; handlerlar xatosiz yuklandi (haqiqiy Telegram — 9-blokda) |
| 8 | Ishga tushirish va Render sozlamasi (`main.py`, `render.yaml`) | ☑ | 3/3 test o'tdi; umumiy: 47 o'tdi, 5 ta (Supabase) kutmoqda |
| 8++ | Groq qo'llab-quvvatlashi: bepul matn (Qwen 3.8) va ovoz→matn (Whisper), provayder `.env` orqali tanlanadi, OpenRouter kaliti ixtiyoriy | ☑ | 9 ta yangi test; umumiy: 66 o'tdi (Supabase bilan) |
| 8+ | Kod tekshiruvi (code review) tuzatishlari: webhook kaliti formati, logga sir tushishi, qayta ishga tushishda xabar yo'qolishi, kunlik hisobot takrorlanishi, ovoz/tugma xatolari | ☑ | 6 ta yangi test; umumiy: 52 o'tdi, 5 ta (Supabase) kutmoqda |
| 9 | Lokal sinov: haqiqiy bot bilan 1 ta matnli va 1 ta ovozli vazifa | ◐ qisman | Groq Qwen jonli sinovi: 4/4 o'zbekcha jumla to'g'ri tushunildi (0.4–1.1 s); bot `/start`ni qabul qilib, egasini tanidi. Javob yuborilmadi: lokal tarmoqdan `api.telegram.org` ga aloqa beqaror (ulanish 0.15 s – 15 s – timeout). Telegram bilan to'liq sinov Render'da (11-blok) o'tkaziladi |
| 10 | GitHub'ga yuklash, Render'ga joylash, UptimeRobot | ☑ | GitHub (`SHAHSIY-YORDAMCHIM-BOT`) ✓; Render Web Service `shahsiy-yordamchim-bot.onrender.com` (Frankfurt, Free) — `/start` va ovozli vazifa ishladi, `/health` → ok ✓; UptimeRobot `vazifa-bot` monitori, 5 daqiqa, holati Up ✓ |
| 10+ | Ovozni tushunishni yaxshilash: "🎤 Eshitdim" ko'rsatish, Whisper'ga o'zbekcha namuna (`prompt`), AI'ga eshitish xatolarini tuzatish ko'rsatmasi | ☑ | 3 ta yangi test; jonli sinov: 6/6 xatoli jumla to'g'ri tuzatildi ("Shfaqorga" → "Shifokorga", "telfon qilsh" → "telefon qilish") |
| 10++ | Professional hisobot: bajarilgan / bajarilmagan / bugungi / muddati o'tgan bo'limlari va shular bo'yicha so'rash | ☑ | 11 ta yangi test (1 tasi Supabase'da); jonli sinov: 6/6 so'rov to'g'ri bo'limga ajratildi; umumiy 78 test o'tdi |
| 11 | Yakuniy sinov: Render'da ishlashi va 08:00 hisobot | ◐ qisman | Render'da matn, ovoz ("🎤 Eshitdim") va vazifa qo'shish ishladi ✓; hisobot/✅ tugmasi va 08:00 hisobot — kutilmoqda |

---

## 13. 2-BOSQICH: INTERNETDAN QIDIRISH — BAJARILISH HOLATI

Batafsil reja: `docs/superpowers/specs/2026-09-28-bosqich2-qidiruv-design.md`. Qidiruv xizmati — Tavily (bepul, oyiga 1000 qidiruv), shahar aniqlash — OpenStreetMap Nominatim.

| Blok | Nima qilinadi | Holat | Tekshiruv natijasi |
|---|---|---|---|
| 2.1 | Tavily qidiruv moduli (`search.py`) va sozlama (`TAVILY_API_KEY`) | ☐ | — |
| 2.2 | Joylashuvdan shahar aniqlash (`geo.py`) | ☐ | — |
| 2.3 | AI: qidiruv niyatini aniqlash va natijalarni saralash | ☐ | — |
| 2.4 | Natijalar ko'rinishi (3 ta + "Yana ko'rsat") | ☐ | — |
| 2.5 | Bot mantiqi: shahar so'rash, qidiruv, xatolar | ☐ | — |
| 2.6 | Telegram: 📍 tugma, joylashuv, "Yana ko'rsat", ishga tushirish | ☐ | — |
| 2.7 | Jonli sinov (har yo'nalishdan 1 tadan) va Render'ga chiqarish | ☐ | — |
