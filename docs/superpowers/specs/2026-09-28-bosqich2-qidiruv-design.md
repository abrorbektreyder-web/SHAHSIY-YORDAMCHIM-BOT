# 2-bosqich: Internetdan qidirish — Texnik reja

**Sana:** 2026-09-28
**Holat:** Tasdiqlangan (egasi bilan brainstorming orqali kelishilgan)
**Asosiy TZ:** `2026-09-28-telegram-vazifa-boti-TZ.md` (10-bo'limdagi 2-bosqich)

---

## 1. Maqsad

Bot egasining so'roviga ko'ra internetdan qidiradi va **3 ta eng mos variantni** havolasi bilan ko'rsatadi: aviabiletlar, mehmonxonalar, restoran/kafelar, YouTube videolari (kino, Qur'on suralari, qo'shiqlar) va umumiy ma'lumot. Bot hech narsa sotib olmaydi va band qilmaydi.

## 2. Kelishilgan qarorlar

| Mavzu | Qaror |
|---|---|
| Qidiruv xizmati | Faqat **Tavily** (bepul: oyiga 1000 kredit; `basic` qidiruv = 1 kredit). YouTube ham Tavily orqali, `include_domains=["youtube.com"]` |
| Byudjet | Faqat bepul xizmatlar |
| Shahar aytilmasa (mehmonxona, restoran) | Bot **har safar** so'raydi: shahar nomini yozish yoki "📍 Joylashuvni yuborish" tugmasi. Joylashuv eslab qolinmaydi |
| Koordinata → shahar | OpenStreetMap **Nominatim** reverse geocoding (kalitsiz, `User-Agent` majburiy, sekundiga ≤1 so'rov) |
| Natija | 6 ta natija olinadi, AI eng mos tartibda saralaydi; birinchi 3 tasi ko'rsatiladi, "Yana ko'rsat" tugmasi keyingi 3 tasini ko'rsatadi (qo'shimcha qidiruvsiz) |
| Ishonchlilik | Havola va sarlavhalar **faqat qidiruv natijasidan** olinadi; AI faqat tartib va 1–2 qatorli izoh beradi, narx/reyting faqat natija matnida bo'lsa yoziladi |
| Kalit yo'q bo'lsa | `TAVILY_API_KEY` bo'sh — qidiruv o'chiq, bot "hali mavjud emas" deb halol javob beradi |

## 3. Oqim

```
Xabar (matn/ovoz)
  → AI.understand → Intent(kind="search", category, query, place)
      category ∈ flight | hotel | restaurant | youtube | general
  → qidiruv o'chiq?            → "Internetdan qidirish hali yoqilmagan"
  → hotel/restaurant va place yo'q? → "Qaysi shaharda?" + 📍 tugma; so'rov kutib turadi
        ├─ 📍 joylashuv keldi → Nominatim → shahar → qidiruv
        │     (shahar aniqlanmasa → "Shahar nomini yozing", kutish davom etadi)
        └─ qisqa matn (≤3 so'z) keldi → shu shahar nomi → qidiruv
           (uzunroq matn → kutish bekor qilinadi, xabar odatdagidek qayta ishlanadi)
  → Tavily.search(query [+ shahar], category, max_results=6)
  → AI.rank_results(so'rov, natijalar) → [(natija, izoh), ...]  (AI xato bersa — Tavily tartibi, izohsiz)
  → 1-sahifa (1–3) + "Yana ko'rsat" tugmasi → 2-sahifa (4–6)
```

## 4. Komponentlar

- `bot/search.py` — `SearchResult(title, url, content)`, `SearchError`, `TavilyClient(api_key, http).search(query, category, max_results=6)`.
- `bot/geo.py` — `Geocoder(http).city(lat, lon) -> str | None` (xatoda `None`).
- `bot/ai_client.py` — `Intent`ga `category`, `query`, `place` maydonlari; `rank_results(request, results) -> list[tuple[int, str]]`.
- `bot/logic.py` — `handle_text(..., searcher=None)`: `search` intent; `run_search(intent, place, ai, searcher)`; `looks_like_place(text)`; `Reply`ga `more` (2-sahifa matni) va `pending` (kutilayotgan qidiruv) maydonlari.
- `bot/views.py` — `format_search_pages(category, title, items) -> list[str]`.
- `bot/handlers.py` — joylashuv xabari handleri, kutilayotgan qidiruv holati (xotirada, bitta egasi uchun), "Yana ko'rsat" callback'i, 📍 reply-klaviatura.
- `bot/config.py` / `main.py` — ixtiyoriy `TAVILY_API_KEY`, `searcher` va `geo` dispatcher'ga uzatiladi.
- `content/uz.py` — yangi matnlar va AI ko'rsatmalari.

## 5. Xatolar

- Tavily xatosi yoki limit tugashi → "Qidiruvda xato bo'ldi, birozdan keyin urinib ko'ring."
- Natija yo'q → "Hech narsa topilmadi, boshqacharoq so'rab ko'ring."
- Nominatim xatosi → shahar nomini yozishni so'raydi.
- AI saralash xatosi → natijalar Tavily tartibida, izohsiz ko'rsatiladi (qidiruv yo'qolmaydi).
- Bot qayta ishga tushsa, kutilayotgan qidiruv va "Yana ko'rsat" ma'lumoti yo'qoladi (xotirada saqlanadi) — qayta so'rash kifoya.

## 6. Testlash

- `search.py`, `geo.py`, `rank_results` — `httpx.MockTransport` bilan (tarmoqqa chiqmasdan).
- `logic.py` — soxta AI va soxta qidiruvchi bilan: o'chiq qidiruv, shahar so'rash, muvaffaqiyatli qidiruv va sahifalar, bo'sh natija, xato.
- `views.py` — sahifa formati, HTML xavfsizligi, raqamlash.
- Jonli sinov: haqiqiy Tavily kaliti bilan har bir yo'nalishdan 1 tadan so'rov.

## 7. Qamrovdan tashqari

- Jonli, aniq bilet narxlari (maxsus aviabilet API'lari) — keyinroq.
- Band qilish — 4-bosqich.
- Joylashuvni eslab qolish.
- Qidiruv natijasini vazifaga aylantirish tugmasi.
