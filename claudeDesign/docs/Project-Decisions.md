# SilkLens — Loyiha Qarorlari va Asoslanmalar
## AI Agentlar uchun To'liq Kontekst Hujjati

> **Maqsad:** Ushbu hujjat loyiha boshida o'tkazilgan 50 savollik interaktiv sessiya natijalarini
> va har bir qarorning asoslanmasini o'z ichiga oladi. AI agentlar ish jarayonida bu hujjatni
> o'qib, nima uchun shu yo'l tanlanganini to'liq tushunishlari va mustaqil qaror qabul
> qilishda ushbu falsafaga amal qilishlari kerak.

---

## Loyiha Falsafasi (Bu hujjatni o'qishdan oldin tushunish shart)

Barcha savollarga berilgan javoblardan bitta kuchli falsafa namoyon bo'ladi:

| Tamoyil | Ma'nosi |
|---|---|
| **Maksimal dinamiklik** | Hech narsa hardcode qilinmaydi. Hamma narsa admin paneldan boshqariladi |
| **Hamma variantni sinash** | Bitta yechimga bog'lanib qolmay, benchmark qilib eng yaxshisini tanlash |
| **MVP yo'q** | To'g'ridan to'g'ri production-quality yechim quriladi |
| **AI birinchi** | Kod yozishdan tortib content generatsiyagacha — AI 99% rol o'ynaydi |
| **Global ambitsiya** | O'zbekistondan emas, dunyodan boshlanadi xayolan |
| **Professional standart** | Har bir qaror eng yuqori professional darajada amalga oshiriladi |

**AI agentlarga muhim eslatma:** Loyiha egasi sizga vazifa berganda, agar u "eng yaxshisini tanla"
yoki "professional qil" desa — bu yuqoridagi falsafaga mos ravishda eng mukammal, kengaytiriladigan,
dinamik yechimni anglatadi. Hech qachon sodda, hardcode qilingan, yoki MVP darajasida yechim taklif
qilmang.

---

## Raund 1 — Ilova Asoslari

---

### Savol 1: Ilovaning asosiy nomi qanday bo'lsin?

**Berilgan javob:** `SilkLens`

**Variantlar:** Durona, SilkLens, Meroschi, Hali aniqlanmagan

**Nima uchun SilkLens tanlandi:**

```
SilkLens = Silk Road (Ipak Yo'li) + Lens (kamera/ko'z)

Semantik kuch:
├── "Silk" → O'zbekiston, Markaziy Osiyo, tarix, madaniyat
├── "Lens" → Kamera, ko'rish, kashf etish, optika
└── Birgalikda → "Ipak Yo'lini kamera orqali ko'rish"

Global brend sifatida afzalliklari:
├── Inglizcha — xalqaro bozorda muammo yo'q
├── 2 bo'g'in — yodda qolishi oson
├── ".com" domain mavjud bo'lish ehtimoli yuqori
├── App Store da izlash uchun qulay
└── Vizual logotip uchun kuchli metafora (ipak + linza)
```

**Muhim noziklik:** Ilova nomi admin paneldan dinamik boshqariladi. Ya'ni kod ichida
ilova nomi hech qachon hardcode qilinmasin. Konfiguratsiya orqali o'qilsin. Sabab: brend
o'zgarishi yoki white-label versiyalar uchun darhol tayyor bo'lish.

---

### Savol 2: Ilovaning ASOSIY funksiyasi nima bo'lsin?

**Berilgan javob:** Barchasi bosqichma-bosqich implement bo'ladi, ro'yxatdagidan ham ko'proq funksiyalar bo'ladi.

**Variantlar:** Kamera→Tanish→Ma'lumot / Xarita+Audio / Ikkalasi / AR overlay

**Nima uchun bu yondashuv tanlandi:**

Loyiha egasi bitta "asosiy funksiya" bilan cheklanishni rad etdi. Bu quyidagi strategik aqlni ko'rsatadi:

```
Noto'g'ri yondashuv: "Bizning asosiy funksiyamiz X"
To'g'ri yondashuv:   "Har bir funksiya o'z vaqtida, to'liq va professional implement bo'ladi"

Sabablar:
1. Raqobatchilar (Google Lens, Smartify) allaqachon bitta funksiyaga ixtisoslashgan
2. SilkLens raqobat ustunligi — funksiyalar TO'PLAMI, bitta funksiya emas
3. Foydalanuvchi ehtiyoji turlicha: biri AR istaydi, biri audio, biri xarita
4. Platforma bo'lib qolish uchun ekotizim kerak, bitta tool emas
```

**AI agentlarga yo'riqnoma:** Birorta funksiyani implement qilayotganda uni izolyatsiyada
emas, balki katta ekotizimning bir qismi sifatida loyihalashtiring. Masalan, kamera moduli
shu paytning o'zida AR uchun, tanish uchun va foto yuklash uchun ham asos bo'lsin.

---

### Savol 3: Birinchi navbatda qaysi foydalanuvchiga mo'ljallangan?

**Berilgan javob:** Ikkalasi teng (mahalliy O'zbek + xorijiy turist)

**Variantlar:** Xorijiy turistlar / Mahalliy O'zbeklar / Ikkalasi teng / Maktab o'quvchilari

**Nima uchun "ikkalasi teng" tanlandi:**

```
Bozor segmentlari va ularning qiymati:

Xorijiy turistlar:
├── Premium to'lash imkoniyati yuqori
├── Ingliz tili birinchi
├── Samarqand, Buxoro, Xivada kontsentratsiyalangan
└── Daromad: $5-15/foydalanuvchi

Mahalliy O'zbeklar:
├── Katta son (36 million kishi)
├── Organik tarqalish (og'izdan-og'izga)
├── O'z yurtini bilish istagi — ta'lim bozori
└── Daromad: $1-3/foydalanuvchi

Ikkalasiga xizmat qilish afzalligi:
├── Turistlar mahalliylar orqali ilovani topadi (va aks holda)
├── Ko'p tilli baza qurilishi shart bo'ladi — bu raqobat ustunligi
├── Yil bo'yi foydalanuvchi — mahalliylar (turistlar mavsumiy)
└── Network effect: mahalliy + xorijiy = to'liq ekotizim
```

**Texnik oqibat:** UI/UX, kontent va monetizatsiya ikki xil persona uchun ishlashi kerak.
A/B testing orqali har bir segment uchun alohida onboarding oqimini sinab ko'ring.

---

### Savol 4: Qaysi platform birinchi chiqarilsin?

**Berilgan javob:** Flutter bilan ikkalasi bir vaqtda (iOS + Android)

**Variantlar:** Android / iOS / Ikkalasi bir vaqtda / Web app

**Nima uchun Flutter + parallel chiqarish:**

```
O'zbekiston bozori: Android 85%+ → Android muhim
Xorijiy turistlar:  iPhone ko'proq → iOS muhim
Xulosa: ikkalasini tashlab bo'lmaydi

Flutter tanlash asoslanmasi:
├── Bitta Dart kodi → iOS + Android + Web + Desktop
├── Google tomonidan — uzoq muddatli qo'llab-quvvatlash kafolatli
├── Kamera, AR, geolokatsiya uchun yetuk plaginlar mavjud
├── Hot reload — tez development
├── Native-ga yaqin performance
└── O'zbekistonda Flutter dasturchilar bozori o'sib bormoqda

Kelajakda framework o'zgarishi hisobga olingan:
Loyiha egasi aytdi: "kelajakda boshqa frameworklarga o'tib ketishimiz mumkin"
Shu sababli:
├── Business logic — Pure Dart, UI ga bog'lanmagan (Clean Architecture)
├── API layer — REST/GraphQL, frameworkdan mustaqil
└── Backend — frameworkdan butunlay ajralgan (headless)
```

---

## Raund 2 — Asosiy Xususiyatlar

---

### Savol 5: Obida tanishda qaysi AI yondashuv asosiy bo'lsin?

**Berilgan javob:** 4-5 xil variantlarni sinab ko'ramiz. Bepulidan boshlab eng yaxshisigacha.

**Variantlar:** Mahalliy model / Cloud API / Gibrid / Vector search

**Nima uchun benchmark yondashuvi tanlandi:**

```
Muammo: Hozir qaysi model eng yaxshi — bilish imkonsiz, chunki:
├── LLaVA, InternVL, Qwen-VL, Llama-3.2-Vision — barchasi rivojlanmoqda
├── GPU server spesifikatsiyasi (RTX 4090) — real sinov kerak
├── O'zbekiston obidalarida qaysi model ko'proq biladi — noma'lum
└── Latency vs accuracy tradeoff — faqat sinov ko'rsatadi

To'g'ri yondashuv:
Benchmark framework yaratish:
├── Test dataset: 200+ obida fotosi, 5 toifada qiyinlik
├── Metrikalar: aniqlik %, javob vaqti ms, RAM/GPU ishlatish
├── Modellar: LLaVA-1.6, InternVL-2, Qwen-VL-Plus, GPT-4V, Google Vision
└── Avtomatik tanlov: eng yaxshi model konfiguratsiyada saqlanadi

Admin paneldan model tanlash:
├── Xarajat vs sifat tradeoff ni admin belgilaydi
├── A/B test: 50% foydalanuvchi model A, 50% model B
└── Real vaqtda almashtirish (downtime yo'q)
```

**AI agentlarga yo'riqnoma:** Vision model integratsiya qilayotganda abstraktsiya qatlami
yarating. `VisionModelProvider` interface orqali ishlang, konkreg model emas. Yangi model
qo'shish 1 fayl o'zgarishi bilan bo'lishi kerak.

---

### Savol 6: Audio guide ovozi qanday bo'lsin?

**Berilgan javob:** 4-5 xil variantlarni sinab ko'ramiz. Bepulidan boshlab eng yaxshisigacha.

**Variantlar:** Kokoro/Piper (mahalliy) / ElevenLabs / Real inson ovozi / Foydalanuvchi tanlaydi

**Asoslanma:**

```
TTS (Text-to-Speech) landscape 2026:
├── Kokoro-82M: Ochiq litsenziya, GPU da real-time, 10+ til
├── Piper TTS:  Tez, engil, ONNX format, CPU da ham ishlaydi
├── ElevenLabs: Eng tabiiy ovoz, lekin $0.30/1000 belgi
├── OpenAI TTS: $15/1M belgi, yaxshi sifat
└── Fish Speech: Ochiq, multi-lingual, real-time

Strategiya — qatlam-qatlam yondashuv:
1-qatlam: Piper/Kokoro (serverda, bepul) → keng til qo'llab-quvvatlash
2-qatlam: OpenAI TTS (premium foydalanuvchilar uchun)
3-qatlam: ElevenLabs (VIP/B2B uchun — muzey rasmiy ovozi)

Muhim: Ovoz fayllarini cache qilish
├── Bir marta generatsiya → CDN/MinIO da saqlash
├── Bir xil matn ikkinchi marta generatsiya qilinmaydi
└── Xarajat = birinchi generatsiya narxi, keyin bepul
```

---

### Savol 7: Offline rejim qanchalik muhim?

**Berilgan javob:** Barcha holatlarni real sinab ko'ramiz. Dinamik bo'ladi.

**Asoslanma:**

```
Offline muhimligi — real stsenariylar:

Xorijiy turist Samarqandda:
├── SIM karta yo'q yoki roaming qimmat ($5-20/MB)
├── WiFi faqat mehmonxonada
└── Muzey ichida signal yo'q

Mahalliy foydalanuvchi:
├── Hududiy: Xiva, Shahrisabz — 4G zaif
├── Ichki muzeylar: signal yo'q
└── Transport (avtobus, poyezd) — uzilishlar

Texnik yechim — qatlam-qatlam offline:
Daraja 1 (har doim offline):
  ├── Asosiy matn tavsiflari (compress JSON)
  ├── Thumbnail fotolar (WebP, 50KB/ta)
  └── GPS koordinatalar va xarita vektorlari

Daraja 2 (yuklab olingan paketlar):
  ├── To'liq fotolar (1-2MB/ta)
  ├── Audio fayllar (MP3, 128kbps)
  └── Shahar xaritasi (offline tiles)

Daraja 3 (faqat online):
  ├── AI real-time tanish (kamera)
  ├── AI chat (savol-javob)
  └── Yangi kontent yangilanishlari

Admin paneldan sozlash:
├── Qaysi kontent offline saqlansin — konfiguratsiya
└── Paket hajmi chegarasi — foydalanuvchi sozlaydi
```

---

### Savol 8: Qaysi tillar birinchi versiyada bo'lsin?

**Berilgan javob:** O'zbek, rus, ingliz, xitoy — va boshqa barcha davlatlar tili dinamik qo'shiladi. Tarjimadan muammo yo'q.

**Asoslanma:**

```
To'rtta til tanlash sabablari:

O'zbekcha: Milliy til, mahalliy foydalanuvchilar
Ruscha:    O'zbekistonda keng tarqalgan, MDH turistlari
Inglizcha: Global lingua franca, barcha xorijiylar
Xitoycha:  O'zbekistonga xitoylik turistlar oqimi +300% (2023-2025)

"Tarjimadan muammo yo'q" — bu katta strategik qaror:
├── NLLB-200 (Meta AI): 200 tilga offline tarjima, bepul
├── Yangi til = 1 soatda qo'shish mumkin
└── Foydalanuvchi interfeysi ham dinamik (admin paneldan)

i18n arxitekturasi:
├── Barcha stringlar kod ichida emas — localization faylida
├── Flutter: flutter_localizations + ARB fayllar
├── Backend: i18next yoki custom i18n service
└── Yangi til qo'shish: yangi ARB fayl → deploy → tayyor

Kontent tarjima pipeline:
Asl matn (O'zbek) → NLLB-200 (avtomatik) → Tekshiruv flaglanadi
                                          → Admin tasdiqlaydi
                                          → Publish bo'ladi
```

---

## Raund 3 — Kontent va Ma'lumotlar

---

### Savol 9: Obidalar haqidagi ma'lumot qayerdan olinadi?

**Berilgan javob:** Barcha kombinatsiyalarni sinab ko'ramiz. Dinamiklik muhim.

**Asoslanma:**

```
Kontent manbai — diversifikatsiya strategiyasi:

Nima uchun bitta manbaga bog'lanmaslik:
├── Wikipedia: Ba'zi obidalar uchun ma'lumot yo'q yoki noto'g'ri
├── AI generatsiya: Hallyusinatsiya xavfi (noto'g'ri tarixiy fakt)
├── Ekspert: Qimmat va sekin
└── Barchasi birgalikda: To'liq va ishonchli

Ko'p qatlamli kontent pipeline:
1. Wikipedia API → Mavjud bo'lsa oladi
2. Wikidata → Strukturaviy ma'lumot (qurilgan yil, arxitektor, koordinat)
3. Claude API → Mavjud ma'lumotni boyitadi, teshiklarni to'ldiradi
4. Vektordan qidiruv → O'xshash obidalardan ma'lumot to'plash
5. Admin tekshiruvi → Muhim faktlar tasdiqlangandan keyin publish

Sifat nazorati:
├── Har bir faktga ishonchlilik balli (0-100%)
├── Agar ball past → "Tekshirilmagan ma'lumot" belgisi
└── Foydalanuvchi xato topsa → flag qiladi → admin ko'rib chiqadi

Kontent versioning:
├── Har o'zgarish tarixda saqlanadi
├── Rollback imkoniyati
└── Kim, qachon o'zgartirganini ko'rish mumkin
```

---

### Savol 10: Foto/video bazasi qanday to'planadi?

**Berilgan javob:** Barcha holatlarni qilib ko'rishga harakat qilamiz.

**Asoslanma:**

```
Media to'plash strategiyasi:

Wikimedia Commons scraping:
├── 100,000+ O'zbekiston fotosi mavjud
├── CC litsenziya — tijorat uchun ham bepul
└── Avtomatik import pipeline: bot → metadata → DB

UGC (User Generated Content):
├── Foydalanuvchi suratga oladi → yuklay oladi
├── AI moderatsiya: noto'g'ri kontent filtrlash
└── Eng yaxshi fotolar "featured" sifatida tanlanadi

Field trip (o'z suratlarimiz):
├── Samarqand, Buxoro, Xiva → professional foto
├── Dron suratlar (3D view uchun)
└── AI model training uchun labeled dataset

Media storage arxitekturasi:
├── MinIO (serverda): original fayllar
├── Cloudflare CDN: foydalanuvchilarga tez yetkazish
├── Rasm optimizatsiyasi: WebP, lazy loading, progressive
└── Thumbnail pipeline: 3 o'lcham (thumb/medium/full)

Copyright himoyasi:
├── Har foto uchun litsenziya ma'lumoti saqlanadi
├── Tijorat ishlatishdan oldin tekshiruv
└── DMCA takedown mexanizmi mavjud
```

---

### Savol 11: Foydalanuvchi o'zi kontent qo'sha oladimi? (UGC)

**Berilgan javob:** To'liq dinamik boshqaruv admin paneldan. Iloji boricha maximum funksionallik muhim.

**Asoslanma:**

```
Nima uchun to'liq UGC tanlandi:

Network effect:
├── Ko'p UGC → ko'p kontent → ko'p foydalanuvchi → ko'p UGC
├── TripAdvisor, Yelp, Wikimapia muvaffaqiyati shu asosda
└── Raqobatchilar (Google Lens) UGC yo'q — bizning ustunligimiz

Funksional UGC:
├── Foto yuklash (obida uchun)
├── Video (30 soniya max) yuklash
├── Matnli sharh (ko'p tilda)
├── Reyting (1-5 yulduz, turli parametrlar bo'yicha)
├── Tavsiya (boshqa foydalanuvchilarga)
└── Xato xabar (noto'g'ri ma'lumot uchun)

Admin boshqaruvi (dinamik):
├── UGC ni on/off qilish (global yoki ma'lum kontent uchun)
├── Pre-moderation yoki post-moderation tanlash
├── Avtomatik approve threshold sozlash
├── Spam/bot himoya darajasi sozlash
└── Eng faol foydalanuvchilarni "Trusted Contributor" qilish

AI Moderatsiya:
├── NSFW content detection (Vision AI)
├── Spam matn detection (NLP)
├── Noto'g'ri geoteg detection (koordinat tekshiruvi)
└── Duplicate content detection (embedding similarity)
```

---

### Savol 12: Obidalar soni MVP uchun qancha bo'lsin?

**Berilgan javob:** Butun O'zbekiston va butun dunyo bo'ylab dataset to'plashga harakat qilamiz — maksimal.

**Asoslanma:**

```
Nima uchun MVP yo'q, to'liq global dataset:

"MVP qilmaymiz" — kuchli strategik qaror:
├── AI agentlar bilan 30 ta obida yozish ham, 500,000 ta yozish ham bir xil vaqt ketadi
├── Kichik dataset bilan launch → foydalanuvchi "kontent kam" deb chiqib ketadi
└── Global ambitsiya bor ekan — nima uchun Samarqand 30 ta bilan boshlansin?

Global dataset miqyosi:
├── O'zbekiston: ~3,000 ro'yxatga olingan obida
├── Markaziy Osiyo: ~10,000 obida
├── UNESCO World Heritage: 1,199 sayt (2024)
├── Wikidata "heritage site": 500,000+ ob'ekt
└── Maqsad: Dunyo bo'yicha barcha obidalar

Avtomatik to'plash pipeline:
├── Wikidata SPARQL query → koordinat + nom + kategoriya
├── Wikipedia API → matn
├── Wikimedia Commons → fotolar
├── OpenStreetMap → qo'shimcha ma'lumot
└── AI → boyitish, tarjima, tasniflash

Dataset sifati:
Har bir obida uchun minimum ma'lumot:
├── Nom (barcha tillarda)
├── Koordinat (lat/lng)
├── Asosiy tasvir (min 1 foto)
├── Qisqa tavsif (100 so'z, min 4 tilda)
└── Kategoriya (me'morchilik / arxeologiya / tabiiy / diniy)
```

---

## Raund 4 — Texnik Stack

---

### Savol 13: Frontend uchun qaysi framework?

**Berilgan javob:** Katta ehtimol bilan Flutter. Kelajakda boshqa frameworklarga o'tib ketishimiz mumkin — hisobga olish kerak.

**Asoslanma:**

```
Flutter tanlash sabablari (asosiy):
├── iOS + Android bitta codebase — development 2x tezroq
├── Google tomonidan — uzoq muddatli support kafolatli
├── Kamera, GPS, AR uchun yetuk plugin ekotizimi
├── Dart null-safety — type-safe, xatolar kamroq
├── WebAssembly support — kelajakda web versiya
└── 2026 yilda Flutter 4.x — stable va mature

"Kelajakda boshqa framework" iborasi uchun arxitektura:
Clean Architecture tamoyili:

lib/
├── domain/          # Biznes logika — FRAMEWORKDAN MUSTAQIL
│   ├── entities/    # Ma'lumot modellari (pure Dart)
│   ├── usecases/   # Biznes qoidalar
│   └── repositories/ # Abstract interfacelar
├── data/            # Ma'lumot manbasi (API, DB, cache)
│   └── repositories/ # Implementatsiyalar
└── presentation/    # UI (Flutter — bu qism almashtiriladi)
    ├── pages/
    └── widgets/

Agar React Native ga o'tilsa:
├── domain/ — o'zgarishsiz qoladi (pure logika)
├── data/ — minimal o'zgarish (API layer bir xil)
└── presentation/ — qayta yoziladi (faqat shu qism)
```

---

### Savol 14: Backend uchun qaysi texnologiya?

**Berilgan javob:** Texnologiyani ham barchasini sinab ko'ramiz.

**Asoslanma:**

```
Backend tanlash — benchmark yondashuvi:

Sinab ko'riladigan texnologiyalar:
┌─────────────┬──────────────┬───────────────┬──────────────┐
│ FastAPI     │ Django       │ NestJS        │ Go/Fiber     │
├─────────────┼──────────────┼───────────────┼──────────────┤
│ AI/ML ideal │ Admin panel  │ Real-time     │ Eng tez      │
│ Python      │ built-in     │ TypeScript    │ Minimal RAM  │
│ async       │ ORM kuchli   │ Microservices │ AI kam       │
│ OpenAPI     │ sekin        │ uchun yaxshi  │ kutubxona    │
└─────────────┴──────────────┴───────────────┴──────────────┘

Tavsiya etilgan arxitektura (barcha uchun):
├── FastAPI: Asosiy API + AI endpoints
├── Django: Admin panel (Django Admin tayyordan keladi)
├── Go: Yuqori load endpointlar (xarita tiles, media)
└── Barchasi bir-biridan REST/gRPC orqali ajralgan (microservices)

Nima uchun microservices:
├── Har bir servis mustaqil scale bo'ladi
├── FastAPI ishlamasa, admin panel ishlayveradi
└── Yangi texnologiya faqat bir servicing o'zgartirishni talab qiladi
```

---

### Savol 15: Asosiy ma'lumotlar bazasi?

**Berilgan javob:** Barcha database turlari bilan to'liq moslashuv bo'lishi kerak. One click bilan tanlash imkoniyati bo'lsin adminda. Dinamiklik yaxshi.

**Asoslanma:**

```
Bu javob database arxitekturasiga juda kuchli talablar qo'yadi.

Nima uchun multi-database arxitektura:
├── PostgreSQL + pgvector: AI embedding va asosiy ma'lumotlar
├── Redis:                  Cache, session, real-time
├── Elasticsearch:          Full-text qidiruv, 200 tilda
├── MongoDB:               Moslashuvchan kontent sxema
└── ClickHouse:            Analitika va statistika

Repository Pattern (abstraktsiya):
class HeritageRepository:
    async def get_by_id(self, id: str) -> Heritage: ...
    async def search(self, query: str) -> List[Heritage]: ...
    async def save(self, item: Heritage) -> None: ...

# Implementatsiyalar:
class PostgresHeritageRepository(HeritageRepository): ...
class MongoHeritageRepository(HeritageRepository): ...
class ElasticHeritageRepository(HeritageRepository): ...

# Admin paneldan tanlash:
ACTIVE_HERITAGE_REPO = config.get("heritage_repository", "postgres")

"One click" almashtirish:
├── Konfiguratsiya o'zgaradi
├── Servis restart bo'ladi
├── Yangi DB ga avtomatik ulanadi
└── Ma'lumot migratsiya skripti ishga tushadi
```

---

### Savol 16: Admin panel va CMS qanday qurilsin?

**Berilgan javob:** Sinab ko'ramiz hammasini, eng yaxshi variantni tanlaymiz.

**Asoslanma:**

```
Admin panel — loyihaning "bosh miyasi"

Admin panel nima qilishi kerak (to'liq ro'yxat):
├── Kontent CRUD (obidalar, fotolar, audiolar)
├── Foydalanuvchi boshqaruvi (rol, huquq, ban)
├── AI sozlamalari (model tanlash, parametrlar)
├── Monetizatsiya (narxlar, planlar, to'lovlar)
├── Analytics dashboard (real-time)
├── B2B boshqaruvi (partnerlar, API key)
├── Moderatsiya (UGC tekshiruv)
├── Tizim sozlamalari (konfiguratsiya)
└── Monitoring (server holati, xatolar)

Baholangan variantlar:
Django Admin:
├── + Tez quriladi, Python bilan integratsiya
├── + ORM bilan tayyor CRUD
└── − Murakkab custom funksiyalar uchun cheklangan

Directus / Strapi:
├── + Headless CMS, API asosida
├── + Plugin tizimi
└── − Katta loyiha uchun cheklangan customization

Custom React/Next.js:
├── + To'liq nazorat
├── + Har qanday funksiya mumkin
└── − Ko'proq development vaqti

Tavsiya etilgan: Django Admin (tez boshlash) + React custom (kengayib borish bilan)
```

---

## Raund 5 — Monetizatsiya

---

### Savol 17: Ilova qanday pul ishlaydi?

**Berilgan javob:** Admin panel orqali to'liq dinamik boshqaruv bo'ladi.

**Asoslanma:**

```
Bu javob biznes modelning to'liq moslashuvchanligini talab qiladi.

Monetizatsiya qatlamlari (barchasi admindan boshqariladi):

B2C (Foydalanuvchi):
├── Free tier: asosiy funksiyalar
├── Premium: kengaytirilgan funksiyalar ($X/oy)
└── Pay-per-use: alohida xususiyatlar uchun to'lov

B2B (Biznes):
├── Featured listing: mehmonxona, restoran, transport
├── White-label API: turizm agentliklari
├── Sponsored content: obida yonida reklama
└── Data insights: anonimlashtirigan statistika

B2G (Davlat):
├── Milliy turizm platformasi shartnomasi
├── Grant loyihalari
└── Smart city integratsiya

Affiliate:
├── Booking.com: mehmonxona bronlash komissiyasi
├── GetYourGuide: ekskursiya sotish komissiyasi
├── Klook: faoliyat bron komissiyasi
└── Transport: aviabilet, poyezd komissiyasi

Admin monetizatsiya paneli:
├── Har bir kanal on/off
├── Region bo'yicha alohida narxlash
├── A/B test: narx variantlari sinash
├── Promo kodlar va chegirmalar
└── Real-time daromad ko'rsatkichlari
```

---

### Savol 18: Premium obuna narxi qanday bo'lsin?

**Berilgan javob:** Admin panel orqali dinamik boshqaruv bo'ladi.

**Asoslanma:**

```
Dinamik narxlash (Dynamic Pricing) — bu strategik ustunlik:

Sabab 1 — Bozor testlash:
├── $1.99 ni sinab ko'rish → konversiya X%
├── $4.99 ni sinab ko'rish → konversiya Y%
└── Optimal narx = eng yuqori LTV (lifetime value) beruvchi

Sabab 2 — Region bo'yicha narx:
├── O'zbekiston: $0.99/oy (xarid quvvati past)
├── Evropa/AQSh: $4.99/oy
├── Xitoy: CNY 15/oy
└── Bir xil xizmat, turli narx — PPP (Purchasing Power Parity)

Sabab 3 — Vaqtga qarab narx:
├── Tourist season (may-sentyabr): standart narx
├── Off-season: 50% chegirma → retention oshadi
└── Yangi yil/Navruz: promo kampaniya

Texnik implementatsiya:
├── Stripe: global to'lovlar
├── Payme/Click: O'zbekiston to'lovlari
├── Google/Apple in-app: mobil to'lovlar (30% komissiya)
└── Konfiguratsiyadan narx o'qiladi (hardcode yo'q)
```

---

### Savol 19: B2B yo'nalishda asosiy mijoz kim bo'ladi?

**Berilgan javob:** Barchasini jamlaymiz. Mehmonxonalar ariza qoldirib to'lov qilib foydalanishlari ham mumkin bo'ladi.

**Asoslanma:**

```
B2B ekotizim — marketplace model:

Mehmonxonalar:
├── Featured card obida yonida ko'rinadi
├── "Eng yaqin mehmonxonalar" bo'limida prioritet joy
├── Narxlash: oylik abonement yoki CPC (click per click)
└── Ariza → admin tasdiqlash → to'lov → faollashish

Restoranlar:
├── "Bu obida yonida milliy taom" — tavsiya
├── Menu va foto yuklay oladi
└── Bron qilish tugmasi (Restoran.uz integratsiya)

Transport:
├── Taksi kompaniyalari: obidaga borish narxi
├── Avtobuslar: marshrutlar va jadvallar
└── Ijaraga mashina: kunlik ijaralar

Turizm agentliklari:
├── API key orqali SilkLens funksiyalarini o'z ilovalarida ishlatish
├── White-label: o'z brendlari bilan
└── Revenue sharing model

B2B onboarding:
1. Ariza shakli (ilovada yoki vebsaytda)
2. Admin tekshiruvi (avtomatik yoki qo'lda)
3. To'lov rekvizitlari kiritish
4. Dashboard kirish
5. Kontent qo'shish va boshqarish
```

---

### Savol 20: Ilova qachon pul ishlashni boshlaydi?

**Berilgan javob:** Admin boshqaruvida bo'lishi kerak.

**Asoslanma:**

```
Monetizatsiya vaqti — admin strategik qaror sifatida:

Nega admindan boshqarilishi kerak:
├── Bozor tayyor emasligini admin sezadi
├── Foydalanuvchi soni yetarli bo'lganda qo'shiladi
└── A/B test: yarmi to'lovli, yarmi bepul — qaysi biri yaxshiroq

"Feature flag" yondashuvi:
├── monetization.enabled = false   → hamma bepul
├── monetization.enabled = true    → planlar faol
└── monetization.soft_paywall = true → ko'radi, lekin to'lay olmaydi (urgency)

Freemium → Premium o'tish psixologiyasi:
1. Foydalanuvchi ilovani sevib qoladi (free)
2. Premium funksiya kerak bo'ladi
3. Paywall — lekin narx past
4. To'laydi va qoladi
Optimal paywall vaqti: foydalanuvchi 7 kun ichida 10+ obida ko'rsa
```

---

## Raund 6 — UX va Dizayn

---

### Savol 21: Ilovaning vizual uslubi qanday bo'lsin?

**Berilgan javob:** Vizual uslubni ham dinamik qilamiz. Har xil variantlarni taqdim qilamiz.

**Asoslanma:**

```
Dinamik tema tizimi — texnik implementatsiya:

ThemeData (Flutter):
├── Light tema
├── Dark tema
├── Milliy tema (naqshlar, to'q ranglar)
└── Accessibility tema (kontrast yuqori)

Design Token arxitekturasi:
tokens/
├── colors.json     # Barcha ranglar (admin o'zgartiradi)
├── typography.json # Shrift, o'lcham, qalinlik
├── spacing.json    # Margin, padding qoidalari
└── radius.json     # Border radius qoidalari

Admin paneldan:
├── Asosiy rang (#hexcode) → butun ilova o'zgaradi
├── Shrift tanlash (Google Fonts)
├── Dark/Light default rejim
└── Milliy aksent elementlari on/off

White-label uchun:
├── B2B partner o'z ranglarini qo'yadi
├── Logo yuklanadi
└── Splash screen o'zgaradi
Natija: Boshqa brend, bir xil ilova — admin paneldan 5 daqiqada.
```

---

### Savol 22: Onboarding qanday bo'lsin?

**Berilgan javob:** Barcha variantlarni sinab ko'ramiz.

**Asoslanma:**

```
Onboarding — birinchi taassurot, eng muhim UX qadam:

A/B test stsenariylari:
A: Skip onboarding → darhol xaritaga
B: 3 splash → signup
C: Interaktiv demo → kamera ochiladi
D: Personalizatsiya → til/shahar tanlash

Metrikalar:
├── Completion rate (necha % onboardingni tugatadi)
├── Day-1 retention (ertasiga qaytib keladimi)
└── Time-to-first-value (birinchi obidani necha daqiqada ko'radi)

Onboarding printsipi (bizning holatimiz):
"Shazam onboardingi": darhol kamera → birinchi tanish → "voy!"
Bu eng kuchli onboarding chunki:
├── Foydalanuvchi darhol qadriyat oladi
├── Registration keyinga qoladi
└── WOW moment birinchi 30 soniyada

Feature flag:
├── onboarding.variant = "A" | "B" | "C" | "D"
└── Admin paneldan o'zgartirish → real-time A/B test
```

---

### Savol 23: Asosiy navigatsiya qanday bo'lsin?

**Berilgan javob:** Barcha variantlarni sinab ko'ramiz.

**Asoslanma:**

```
Navigatsiya — UX ning skeleti:

Sinab ko'riladigan variantlar:

Bottom Navigation (klassik):
[Kamera] [Xarita] [Qidiruv] [Profil]
├── + Tanish, standart
└── − Kamera asosiy bo'lmaydi

Shazam uslubi (kamera markazda):
       [KAMERA]
[Xarita]     [Profil]
├── + Kamera — asosiy funksiya sifatida belgilangan
└── − Qidiruv ko'rinmaydi

Tab + Gesture:
├── + Zamonaviy, gesture-first
└── − O'rganish egri chizig'i

Google Maps uslubi:
├── + Xarita asosiy
└── − Kamera ikkinchi planga tushadi

Tavsiya: Kamera markazda (Shazam uslubi)
Sabab: SilkLens ning eng kuchli funksiyasi kamera orqali tanish.
Birinchi ochilganda foydalanuvchi "nima qilish kerak" ni darhol tushunsin.

Lekin admin paneldan navigation layout o'zgartirish mumkin bo'lsin.
```

---

### Savol 24: Gamification elementlari bo'lsinmi?

**Berilgan javob:** Gamification bo'ladi albatta, professional bo'ladi. Hali juda zo'r bo'ladi.

**Asoslanma:**

```
Gamification — foydalanuvchini qaytib kelishga undash mexanizmi:

To'liq gamification tizimi:

XP (Tajriba Ballari):
├── Obida ko'rish: +10 XP
├── Birinchi marta ko'rish: +50 XP (bonus)
├── Sharh yozish: +20 XP
├── Foto yuklash: +30 XP
└── Do'stga tavsiya: +100 XP

Darajalar (Levels):
1. Sayohatchi      (0-500 XP)
2. Kashfiyotchi    (500-2000 XP)
3. Meros Qo'riqchisi (2000-5000 XP)
4. Ipak Yo'li Gidi (5000-15000 XP)
5. Ustoz Sayyoh   (15000+ XP)

Badgelar (Medallar):
├── "Samarqand istilochisi" — 10 ta Samarqand obidasi
├── "Ipak Yo'li" — 3 ta shahar
├── "Dunyogashta" — 5 mamlakat
├── "Tarixchi" — 100 ta sharh
└── "Milliy Hazina" — 1000 ta obida ko'rgan

Leaderboard:
├── Haftalik (yangi boshlovchilar uchun imkoniyat)
├── Oylik (regulyar foydalanuvchilar uchun)
├── Do'stlar orasida (ichki raqobat)
└── Shahar bo'yicha (mahalliy jamoat hissi)

Streak:
├── 7 kun ketma-ket kirib obida ko'rish → maxsus badge
├── 30 kunlik streak → premium 1 oy bepul
└── Streak yo'qolishidan oldin push notification

Achievements real-time trigger:
├── Yangi badge → animatsiya + bildirishnoma
└── Do'st ustingizdan o'tdi → "Do'stingiz siz bilan raqobatda!"
```

---

## Raund 7 — Launch Strategiyasi

---

### Savol 25: MVP birinchi qayerda launch qilinadi?

**Berilgan javob:** MVP qilmaymiz. Darhol professional production uchun to'liq tayyor holatga keltirib chiqaramiz. AI agentlar bilan MVP yasab o'tirishga hojat yo'q.

**Bu qaror nima uchun to'g'ri:**

```
Eski fikr:   "MVP → Feedback → Iterate → Grow"
SilkLens:    "Professional v1.0 → Launch → Scale"

Nima o'zgardi:
├── AI agentlar bilan 1 haftalik ish = oldingi 6 oylik ish
├── Kapital yetarli (server, AI tools — hamma bor)
├── Yagona dasturchi review qiladi — bottleneck yo'q
└── MVP dan kelgan feedback: "kontent kam, funksiya kam" — bu boshidanoq to'liq qurilsa yo'qoladi

Professional v1.0 nima anglatadi:
├── Barcha asosiy funksiyalar ishlaydi
├── 5,000+ obida tayyor (faqat O'zbekiston emas)
├── Ko'p til ishlaydi
├── Audio guide mavjud
├── Offline rejim mavjud
├── Crash free: 99.9% uptime
└── App Store rating: 4.5+

"MVP yasab o'tirishga hojat yo'q" iborasi — AI agentlarga signal:
Biror funksiyani "minimal" qilib yozishga harakat qilmang.
Birinchi marta yozganda ham production-quality yozing.
```

---

### Savol 26: Birinchi foydalanuvchilar qayerdan keladi?

**Berilgan javob:** Barcha mumkin bo'lgan nuqtalardan foydalanuvchilarni jalb qilishimiz kerak.

**Asoslanma:**

```
Multi-channel foydalanuvchi jalb qilish strategiyasi:

Organik kanallar:
├── App Store ASO: "uzbekistan travel guide", "silk road app"
├── Google Play ASO: 200+ keyword optimization
├── SEO: web versiya yoki landing page
└── Word-of-mouth: yaxshi ilova o'z-o'zidan tarqaladi

Ijtimoiy media:
├── Instagram: har kun 1 ta obida hikoyasi (Reels format)
├── TikTok: "Siz bilmagan O'zbekiston" seriyasi
├── Telegram: O'zbekiston tarix kanali
├── YouTube: virtual tour videolar
└── X/Twitter: tarixiy faktlar

Influencer:
├── O'zbekiston sayohat vlogerlar (100K+ obunachilar)
├── Xorijiy O'zbekiston sayohati kontenti yaratuvchilar
└── Tarix va madaniyat blogerlar

B2B orqali:
├── Turizm agentliklari → mijozlariga tavsiya qiladi
├── Mehmonxonalar → wi-fi parolini berganda tavsiya qiladi
└── Havo yo'llari → uçuş davomida reklama

Press & PR:
├── "O'zbekistonda birinchi AI turizm ilovasi" — matbuot xabari
├── UNESCO bilan hamkorlik e'loni
└── Xalqaro sayohat mediasida review

Tahlil va optimallashtirish:
├── UTM parametrlar: har kanal alohida kuzatiladi
├── CAC (Customer Acquisition Cost) har kanal uchun
└── Admin dashboard: kanal samaradorligini ko'rish
```

---

### Savol 27: Raqobatchilardan farqlanish uchun asosiy 'WOW effekti' nima?

**Berilgan javob:** WOW effektlarimiz ko'p bo'ladi.

**Asoslanma:**

```
WOW momentlarning to'liq ro'yxati:

1. Kamera → 1 soniyada tanish (Shazam effekti)
   Foydalanuvchi: "Bu nima?" → telefon ko'rsatadi → 1 soniya → tarix, audio, xarita

2. AI Chat: Obida bilan "suhbat"
   "Bu minora qachon qurilgan?" → "1127 yilda Qorakxoniylar davrida..."
   Foydalanuvchi sanab turganday his qiladi

3. AR: Obidaning 500 yil oldingi ko'rinishi
   Hozirgi kamera orqali — virtual rekonstruksiya overlay

4. Marshrut Sehri
   "2 kunim bor, 3 nafar bola bilan, Samarqandda nimalar ko'raman?"
   → AI 5 daqiqada optimal marshrut + mehmonxona + restoran tavsiyasi

5. Gamification surpizi
   Birinchi obida ko'rilganda → animatsiya → "Sayohatchi" unvoni beriladi

6. Offline surprise
   Internet yo'q, lekin ilova ishlaydi → "Bu qanday?"

7. 200 til
   Nemischa savolga nemischa javob → turistlar uchun sehrli

8. Tarixiy foto qiyoslash
   Obidaning 1900-yilgi va hozirgi fotosi — slider bilan solishtiruv
```

---

### Savol 28: Davlat / rasmiy tashkilotlar bilan hamkorlik qilinsinmi?

**Berilgan javob:** Deyarli barchasi bilan hamkorlik bo'ladi. Hamma qo'llab-quvvatlaydi jahon miqyosida.

**Asoslanma:**

```
Hamkorlik strategiyasi — qatlam-qatlam:

Milliy darajada:
├── O'zbekiston Turizm va Sport vazirligi
├── UNESCO O'zbekiston bo'limi
├── O'zME (O'zbek Milliy Entsiklopediyasi)
└── Qo'riqxonalar va milliy parklar boshqarmalari

Xalqaro darajada:
├── UNESCO World Heritage Centre (Parij)
├── UNWTO (Jahon Turizm Tashkiloti)
├── Aga Khan Cultural Services
└── Silk Road International Bureau (UNESCO)

Akademik:
├── Toshkent Davlat Sharqshunoslik Universiteti
├── O'zbekiston Fanlar Akademiyasi
└── Xalqaro arxeologiya ekspeditsiyalari

Texnologiya:
├── Google (Maps Platform partneri)
├── Mapbox (reseller)
└── Huawei (Xitoy bozori uchun HMS)

Hamkorlik protokoli:
1. Ilova professional holda ko'rsatiladi
2. Rasmiy maktub + NDA
3. Pilot: bitta muzey yoki sayt
4. Natijalar ko'rsatiladi → katta shartnoma
5. MOU (Memorandum of Understanding) imzolanadi
```

---

## Raund 8 — Ilg'or Xususiyatlar

---

### Savol 29: AR xususiyatlari qanday bo'lsin?

**Berilgan javob:** Hali chuqur o'ylab ko'ramiz. Maximum imkoniyatlardan foydalanamiz.

**Asoslanma:**

```
AR — differensiyatorning eng kuchli qismi:

AR texnologiya stack:
├── ARCore (Android): Google tomonidan, kuchli plane detection
├── ARKit (iOS): Apple tomonidan, eng sifatli depth sensing
└── Flutter: ar_flutter_plugin yoki sceneview_flutter

AR funksiyalar (implementatsiya tartibi):

Bosqich 1 (tez):
├── Floating info cards: obida ustida belgi ko'rinadi
├── Distance indicator: "Siz obidadan 50m uzokdasiz"
└── Navigation arrow: AR orqali yo'l ko'rsatish

Bosqich 2 (o'rta):
├── Historical photo overlay: 1900-yilgi foto slice bilan
├── 3D model superimpose: obidaning virtual kengaytmasi
└── Time-lapse: kunlik yorug'lik o'zgarishi simulatsiyasi

Bosqich 3 (ilg'or):
├── Full 3D reconstruction: xarobadan hozirgi holga rekonstruksiya
├── AR quest: topishmoq va g'ildirak o'yinlar
└── Multi-user AR: bir nechta odam bir xil AR ko'radi

3D model manbai:
├── Sketchfab: 1000+ O'zbekiston obidasi 3D modeli mavjud
├── Photogrammetry: dron + kamera → 3D model (AI asosida)
└── Open Heritage by Google Arts: UNESCO saytlari 3D skanlar
```

---

### Savol 30: Ijtimoiy tarmoq elementlari bo'lsinmi?

**Berilgan javob:** Albatta, bu borada maximum qulayliklar qilamiz.

**Asoslanma:**

```
Ijtimoiy features — viral o'sish mexanizmi:

Ichki ijtimoiy:
├── Profil: borilgan joylar xaritada (Visited World uslubi)
├── Feed: do'stlar nimalar ko'rdi
├── Guruh sayohat: real-time birgalikda sayohat
└── Tavsiyalar: "Do'stingiz bu joyni yoqtirdi"

Share mexanizmlari (viral loop):
├── Obida kartochkasi: chiroyli branded rasm → Instagram story
├── "Men bu yerda bo'ldim" sticker: AR/foto bilan
├── Sayohat statistikasi: "2026 yilda 47 ta obida ko'rdim" (Spotify Wrapped uslubi)
└── Deep link: share qilingan link ilovani ochadi, obidani ko'rsatadi

Tashqi platformalar:
├── Instagram: story va post uchun tayyor format (9:16 va 1:1)
├── Telegram: kanal + bot integratsiya
├── X/Twitter: OpenGraph metadata — preview chiroyli ko'rinadi
└── WhatsApp: link preview + qisqa tavsif

Nima uchun bu muhim:
Har bir ulashish = organik reklama.
Maqsad: bir foydalanuvchi 1 oy ichida 3 kishiga tavsiya qilsin (NPS > 50)
```

---

### Savol 31: Marshrut va navigatsiya funksiyalari?

**Berilgan javob:** To'liq mukammal bo'ladi bu ham.

**Asoslanma:**

```
Navigatsiya — to'liq ekotizim:

AI Marshrut Planlovchi:
Input: "3 kunim bor, 2 nafar, budget o'rtacha, tarix yoqadi"
Output:
├── Kun 1: Registon → Gur-Emir → Sherdor → tushlik (tavsiya) → Shah-i-Zinda
├── Kun 2: Bibixonim → Siyob bozori → Ulug'bek rasadxonasi
├── Kun 3: Afrosiyob → Doniyor maqbarasi → xarid
└── Mehmonxona, restoran, transport — barchasi birlashtirilgan

Navigatsiya turlari:
├── Piyoda: optimal yo'l, balandlik farqi hisobga olinadi
├── Taksi: narx taklifi + Yandex/Uber buyurtma
├── Avtobus: marshrutlar, jadvallar, to'xtash joylari
├── Велосипед: ijaraga olish joylari (kelajakda)
└── Sayyohlik avtobuslari: marshrutlar va narxlar

Xarita texnologiyasi:
├── OpenStreetMap: asosiy xarita (bepul, offline)
├── Mapbox: custom styling (SilkLens dizayni bilan)
├── Google Maps: fallback va Places API
└── Indoor navigation: muzey ichida yo'l ko'rsatish (kelajakda)
```

---

### Savol 32: Mehmonxona, restoran, transport integratsiyasi?

**Berilgan javob:** Professional implement bo'ladi.

**Asoslanma:**

```
Ekotizim integratsiya — "Super App" yo'lida birinchi qadam:

Mehmonxonalar:
├── Booking.com API: narxlar, mavjudlik, bron
├── Airbnb API: alternativ turar joy
├── Mahalliy mehmonxonalar: to'g'ridan to'g'ri (B2B panel orqali)
└── SilkLens Premium: mehmonxona bron qilganda cash-back

Restoranlar:
├── Yandex Food / Wolt: deliver buyurtma
├── Restoran.uz: O'zbekiston uchun mahalliy
├── Menyu PDF/foto: rasmiy menyu ko'rish
└── "Milliy taom" filtri: palov, lagman, somsa...

Transport:
├── Yandex Taxi / Uber: API orqali to'g'ridan narx + buyurtma
├── Aviabiyet: Aviasales/Skyscanner embed
├── Poyezd: O'zbekiston temir yo'llari API
└── Rent a car: mahalliy ijaraga avtomobil

Souvenir va savdo:
├── "Sertifikatlangan souvenir do'kon" belgisi
├── "Bu yerda soxta mahsulot emas" — ishonch belgisi
└── Online buyurtma: tashrif qilmasdan ham xarid

Integratsiya arxitekturasi:
├── Har bir servis Plugin sifatida — on/off from admin
├── API aggregator: bir joydan barchani boshqarish
└── Fallback: bir API ishlamasa, ikkinchisiga o'tish
```

---

## Raund 9 — Ma'lumotlar va Xavfsizlik

---

### Savol 33: Foydalanuvchi autentifikatsiyasi qanday bo'lsin?

**Berilgan javob:** Barcha mumkin bo'lgan autentifikatsiyalarni implement qilamiz.

**Asoslanma:**

```
Auth — foydalanuvchi ilovaga kirish to'siqsiz bo'lishi kerak:

Implementatsiya ro'yxati:
├── Email + parol (universal fallback)
├── Google OAuth (eng keng tarqalgan)
├── Apple Sign-In (iOS uchun majburiy — App Store qoidasi)
├── Telegram Login Widget (O'zbekistonda dominant)
├── Facebook OAuth (MDH foydalanuvchilari)
├── Phone + OTP SMS (Esign/eskiz yo'q foydalanuvchilar)
└── Mehmon rejimi (hech narsa kiritmay foydalanish)

Texnik implementatsiya:
├── JWT + Refresh Token (stateless, scalable)
├── OAuth 2.0 / OpenID Connect standard
├── MFA (ikki faktorli — premium xususiyat sifatida)
└── Biometric (Face ID / Fingerprint) — lokal qurilmada

Auth provider abstraktsiya:
class AuthProvider:
    async def sign_in(method: AuthMethod) -> User: ...
    async def sign_out() -> None: ...
    async def get_current_user() -> Optional[User]: ...

Yangi auth usuli qo'shish = 1 ta provider class yozish.
Admin paneldan: qaysi auth metodlar yoqiq/o'chiq.
```

---

### Savol 34: Foydalanuvchi ma'lumotlari qayerda saqlanadi?

**Berilgan javob:** Barcha mumkin bo'lgan variantlarni qilamiz.

**Asoslanma:**

```
Ma'lumot saqlash — foydalanuvchi tanlasin:

Darajalar:
1. Qurilmada (Device-only):
   └── Hech qanday server yo'q, to'liq privacy

2. Serverda (Cloud sync):
   └── Barcha qurilmalarda bir xil, backup bor

3. Gibrid (Local-first + sync):
   └── Offline ishlaydi, online bo'lganda sync qiladi
   └── Bu eng yaxshi UX — biz tavsiya qilamiz

4. Foydalanuvchi tanlaydi:
   └── Privacy sozlamalarda o'zi belgilaydi

Texnik: Local-first arxitekturasi
├── Flutter: Isar (tez, native NoSQL)
├── Conflict resolution: CRDT (Conflict-free Replicated Data Type)
├── Sync: WebSocket yoki background fetch
└── Encryption: AES-256, foydalanuvchi kaliti bilan

Qaysi ma'lumot qayerda:
Faqat local:     Qidiruv tarixi, yoqtirgan obidalar
Server + local:  Gamification, yutuqlar (leaderboard uchun)
Faqat server:    To'lov ma'lumotlari (PCI DSS)
```

---

### Savol 35: Analitika va foydalanuvchi kuzatuvi?

**Berilgan javob:** Barcha mumkin bo'lgan variantlarni qilamiz.

**Asoslanma:**

```
Analitika — ma'lumotga asoslangan qarorlar uchun:

Firebase Analytics (bepul):
├── Foydalanuvchi oqimi (funnel)
├── Retention: D1, D7, D30
├── Custom events: obida_viewed, audio_played, ar_opened
└── Audience: demografiya, qurilma, til

Mixpanel (event-based):
├── Har bir tugma va harakatni kuzatish
├── Cohort analysis: "bu haftada kelganlar qanday qildi?"
└── A/B test natijalarini ko'rish

Mahalliy analitika (o'z serverimizda):
├── GDPR: ma'lumot EU ga chiqmaydi
├── Umuniy: uchinchi tomon ko'rmaydi
└── ClickHouse: real-time analitika, sekundiga milliardlab event

Crash reporting — Sentry:
├── Stack trace: xato qayerdan chiqdi
├── User context: kim, qachon, qaysi versiya
└── Performance: sekin funksiyalar

Admin analytics dashboard:
├── Real-time: hozir necha kishi online
├── Top obidalar: eng ko'p ko'rilganlar
├── Revenue metrics: daromad, konversiya
└── AI performance: tanish aniqlik foizi
```

---

### Savol 36: GDPR va O'zbekiston ma'lumotlar qonuniga muvofiqlik?

**Berilgan javob:** Barcha mumkin bo'lgan variantlarni qilamiz.

**Asoslanma:**

```
Legal compliance — birinchi kunda, keyinga qoldirmasdan:

O'zbekiston:
├── "Shaxsga doir ma'lumotlar to'g'risida" qonun (2019)
├── Ma'lumotlar O'zbekistonda saqlanishi shart (ba'zi kategoriyalar)
└── Saqlash muddati: foydalanuvchi so'roviga qarab o'chirish

GDPR (Evropa):
├── Consent: foydalanuvchi rozi bo'lishi kerak
├── Right to be forgotten: ma'lumot o'chirish
├── Data portability: ma'lumotni export qilish
└── Privacy by design: arxitekturada boshidanoq

CCPA (Kaliforniya):
├── "Mening ma'lumotlarimni sotmang"
└── Kaliforrniyalik foydalanuvchilar uchun alohida oqim

Texnik implementatsiya:
├── Consent management: CookieBot yoki custom
├── Data deletion: "Hisobni o'chirish" → 30 kun ichida to'liq o'chirish
├── Data export: JSON format, 24 soat ichida
└── Privacy policy: har til uchun, oddiy tilda

Privacy by design printsipi:
├── Faqat kerakli ma'lumot to'planadi
├── Ma'lumot minimizatsiya: manzil o'rniga faqat shahar
└── Anonymization: analitika uchun ID hash qilinadi
```

---

## Raund 10 — Development Jarayoni

---

### Savol 37: Kod versiya nazorati va branching strategiyasi?

**Berilgan javob:** Professional variantni tanlaymiz.

**Asoslanma:**

```
GitFlow — professional standart:

Branch tuzilmasi:
main          ← Faqat production-ready kod
develop       ← Integratsiya branch (barcha feature shu yerga merge)
feature/xxx   ← Yangi funksiya (develop dan chiqadi)
hotfix/xxx    ← Kritik xato tuzatish (main dan chiqadi)
release/x.x.x ← Release tayyorgarlik (develop dan chiqadi)

Commit message konvensiya (Conventional Commits):
feat: obida tanish AI endpoint qo'shildi
fix: audio guide iOS da to'xtab qolish xatosi tuzatildi
refactor: database layer abstraktsiya qo'shildi
docs: API hujjatlari yangilandi
test: vision model benchmark testlar

AI agentlar uchun qoida:
├── Har bir o'zgarish alohida feature branch da
├── Kichik, mantiqiy commit lar (1 funksiya = 1 commit)
├── PR description: nima qilindi, nima uchun, qanday test qilindi
└── Self-review: PR ochishdan oldin o'z kodingizni o'qing

GitHub qoidalari:
├── main branch ga to'g'ridan push yo'q
├── Har PR uchun minimum 1 review (AI review + developer)
└── CI/CD yashil bo'lmasa merge yo'q
```

---

### Savol 38: Testing strategiyasi qanday bo'lsin?

**Berilgan javob:** Barcha mumkin bo'lgan variantlarni qilamiz.

**Asoslanma:**

```
Testing piramidasi — SilkLens uchun:

Unit tests (asos):
├── Domain logika: 100% coverage maqsad
├── Usecase lar: har bir scenario test qilinadi
├── Utility funksiyalar: edge case lar
└── Vositalar: pytest (Python), flutter_test (Dart)

Integration tests (o'rta):
├── API endpointlar: har bir route test qilinadi
├── Database: CRUD operatsiyalar
├── AI model: mock bilan test (real API chaqirilmaydi)
└── Vositalar: pytest + httpx, Postman/Newman

E2E tests (cho'qqi):
├── Foydalanuvchi oqimi: ro'yxatdan o'tish → obida ko'rish → audio tinglash
├── Flutter: integration_test paketi + Patrol
├── API: Playwright (web admin uchun)
└── Har release dan oldin to'liq suite

Performance tests:
├── Load test: k6 bilan 10,000 parallel foydalanuvchi
├── AI response time: 95th percentile < 2 soniya
└── App startup: cold start < 3 soniya

Test ma'lumotlar:
├── Fixtures: test uchun doimiy obidalar va foydalanuvchilar
├── Factories: dinamik test ma'lumot generatsiya
└── Seeder: test muhitini bir buyruq bilan to'ldirish
```

---

### Savol 39: CI/CD pipeline qanday qurilsin?

**Berilgan javob:** Barcha mumkin bo'lgan variantlarni qilamiz.

**Asoslanma:**

```
CI/CD — "push qil, ishonch bilan chiqar" prinsipi:

GitHub Actions (asosiy CI):
name: CI
on: [push, pull_request]
jobs:
  test:      lint → unit test → integration test
  build:     Docker image build
  security:  Trivy scan, Bandit, secret scan

GitLab Runner (self-hosted, asosiy CD):
├── Server resurslari cheksiz (o'z serverimiz)
├── Deploy: Docker Swarm rolling update
└── Rollback: bir buyruq bilan oldingi versiyaga qaytish

Codemagic (iOS build):
├── Flutter iOS build (Mac uchun)
├── Code signing (sertifikat)
├── TestFlight yuklash
└── 500 daqiqa/oy bepul (yetarli)

Deployment strategiyasi:
├── Blue-Green: yangi versiya yonida eski ishlaydi
├── Canary: 5% traffic yangi versiyaga → xato yo'q → 100%
└── Feature flags: kod deploy bo'lgan, lekin funksiya o'chiq

Monitoring trigger:
├── Deploy bo'ldi → Sentry yangi release belgisi
├── Xato ko'tarildi → Telegram bot xabar beradi
└── Uptime tushdi → SMS + Telegram alert
```

---

### Savol 40: Monitoring va alerting?

**Berilgan javob:** Barcha mumkin bo'lgan variantlarni qilamiz.

**Asoslanma:**

```
Monitoring — "biror narsa yuz bermasa bilamiz" prinsipi:

Grafana + Prometheus (infrastruktura):
Dashboard lar:
├── Server: CPU, RAM, disk, network
├── API: request/sec, response time, error rate
├── AI: inference time, GPU ulushi, model accuracy
├── Database: query time, connection pool, cache hit rate
└── Business: active users, revenue, conversions

Alert qoidalari:
├── API error rate > 1% → Telegram alert
├── Response time > 2s (95th percentile) → alert
├── GPU memory > 90% → kritik alert
└── Disk > 80% → ogohlantirish

Sentry (application monitoring):
├── Backend: Python exceptions
├── Flutter: Dart exceptions + crash reports
└── Performance: slow transactions flaglash

UptimeRobot (tashqi monitoring):
├── 5 daqiqada bir test
├── Tushib qolsa: SMS + Telegram + Email
└── Status page: foydalanuvchilar ham ko'ra oladi

Distributed tracing:
├── OpenTelemetry: bitta so'rov qayerda necha vaqt ketdi
└── Jaeger: trace visualization
```

---

## Raund 11 — Kontent Boshqaruvi

---

### Savol 41: Yangi obida qo'shish jarayoni qanday bo'lsin?

**Berilgan javob:** Barcha mumkin bo'lgan variantlarni qilamiz.

**Asoslanma:**

```
Kontent ingestion — ko'p kanalli:

1. Qo'lda (Admin UI):
   Form: nom, koordinat, kategoriya, tavsif, fotolar
   → Validation → AI boyitish taklifi → Publish

2. AI avtomatik:
   a) GPS koordinat kiritiladi
   b) Google Street View / satellite rasmlar olinadi
   c) Vision AI: "Bu nima?" → kategoriya, nom tahlili
   d) Wikipedia/Wikidata: ma'lumot to'plash
   e) Claude: boyitilgan tavsif generatsiya
   f) Admin: tasdiqlaydi yoki o'zgartiradi
   g) Publish

3. Bulk import:
   Formatlari: JSON, CSV, Excel, GeoJSON, KML (Google Earth)
   Pipeline: parse → validate → deduplicate → enrich → import
   Dashboard: progress, xatolar, muvaffaqiyatlar

4. API (tashqi):
   Partner tashkilotlar (muzeylar) o'z sistemasidan yuboradi
   → SilkLens API → validatsiya → staging → tasdiqlash → live

5. Foydalanuvchi taklifi:
   "Bu joyni bilasizmi?" → form → admin tekshiruv → qo'shiladi

Kontent pipeline monitoring:
├── Har kunda nechta yangi obida qo'shildi
├── Qaysi manbadan ko'proq keldi
└── Tasdiqlash kutayotganlar soni
```

---

### Savol 42: Ko'p tilli kontent qanday boshqariladi?

**Berilgan javob:** Barcha mumkin bo'lgan variantlarni qilamiz.

**Asoslanma:**

```
i18n pipeline — til to'siqsiz kontent:

Avtomatik tarjima (birlamchi):
Asl matn (O'zbek yoki Ingliz)
→ NLLB-200 (mahalliy, 200 til, GPU da)
→ Tarjima sifat balli (BLEU score)
→ Sifat past bo'lsa → DeepL API fallback
→ DeepL ham past → Google Translate

Sifat nazorati:
├── Har tarjimaga confidence score
├── 80%+ → avtomatik publish
├── 50-80% → "Tasdiqlash kutilmoqda" belgisi
└── 50%- → manual tarjima talab etiladi

Tarjima xotirasi (Translation Memory):
├── Bir marta tarjima qilingan ibora → saqlanadi
├── Keyingi marta xuddi shu ibora → xotiradan olinadi (bepul)
└── Izchillik: bir xil terminlar bir xil tarjima qilinadi

Admin tarjima paneli:
├── Til bo'yicha tavsiflar ko'rsatiladi
├── Inline editing: tarjimani to'g'ridan o'zgartirish
├── Approve / Reject tugmalari
└── Machine translated belgisi (foydalanuvchi bilsin)

Yangi til qo'shish (30 daqiqa ichida):
1. Admin panelda yangi til qo'shiladi
2. NLLB-200 avtomatik barcha mavjud kontentni tarjima qiladi
3. Review queue ga tushadi
4. Tasdiqlangach — live
```

---

### Savol 43: Kontent moderatsiya (UGC uchun)?

**Berilgan javob:** Barcha mumkin bo'lgan variantlarni qilamiz. Dinamik bo'ladi sozlamalar.

**Asoslanma:**

```
Moderatsiya — admin sozlamalarida to'liq nazorat:

Admin dan sozlanadigan rejimlar:

Rejim A — Pre-moderation (ehtiyotkor):
UGC → Kutish → Admin tekshiradi → Publish
├── + Hech qanday noto'g'ri kontent ko'rinmaydi
└── − Kechikadi (admin ulgurmasligi mumkin)

Rejim B — Post-moderation (tez):
UGC → Darhol ko'rinadi → Background tekshiruv → Olib tashlash
├── + Tezroq, foydalanuvchi darhol ko'radi
└── − Biroz vaqt noto'g'ri kontent ko'rinadi

Rejim C — AI-gated (smart):
UGC → AI tekshiradi → Score yuqori? → Darhol
                    → Score past?  → Admin kutadi
├── + Tezlik + sifat balansi
└── − AI xatosi bo'lishi mumkin

Moderatsiya filtrlari (sozlanadi):
├── NSFW: 0-100% threshold (admin belgilaydi)
├── Spam: takroriy kontent filtri
├── Geotag: koordinat obida yaqinida bo'lishi shart
├── Til: qaysi tillar ruxsat etilgan
└── Foydalanuvchi trust level: yangi vs eski

AI moderatsiya stack:
├── Foto: Vision AI (NSFW, violence, fake)
├── Matn: NLP (spam, hate speech, advertisement)
└── Audio (kelajakda): SpeechBrain (noto'g'ri gap)
```

---

### Savol 44: Yangilanishlar va versioning qanday bo'lsin?

**Berilgan javob:** Bu borada professional yondashuv qilamiz.

**Asoslanma:**

```
Update arxitekturasi — "always fresh, never broken":

Kontent yangilanishi (real-time, app update kerak emas):
├── Obida ma'lumoti o'zgardi → CDN invalidation → foydalanuvchi keyingi ochganda yangi
├── Yangi obida qo'shildi → push notification (optsional)
└── Narx o'zgardi → darhol kuchga kiradi

App versioning (semantic versioning):
MAJOR.MINOR.PATCH
├── MAJOR: breaking change (API o'zgardi, DB migratsiya)
├── MINOR: yangi funksiya (backward compatible)
└── PATCH: xato tuzatish

Forced update mexanizmi:
├── Backend: minimum_app_version = "2.0.0"
├── Ilova versiyasi eski → "Yangilang" dialog
├── Kritik xavfsizlik → majburiy yangilash
└── Admin paneldan: qaysi versiya minimum belgilash

OTA (Over-the-air) kontent yangilanishi:
├── Flutter: dart_define bilan remote config
├── Firebase Remote Config: flag va string lar
└── Ilova to'xtamasdan yangi kontent keladi

API versioning:
/api/v1/heritage   ← Eski versiya saqlanib qoladi
/api/v2/heritage   ← Yangi versiya parallel ishlaydi
Eski app v1 ga, yangi app v2 ga → ikkalasi ishlaydi
```

---

## Raund 12 — Biznes va Kelajak

---

### Savol 45: Keyingi 6 oyda qaysi mintaqaga kengayish?

**Berilgan javob:** Global, butun dunyo bo'ylab.

**Asoslanma:**

```
Global-first yondashuv — nima uchun to'g'ri:

Tradicional startup yo'li:
Bir shahar → Mamlakat → Region → Global (2-3 yil)

SilkLens yo'li:
Global dataset (avtomatik) → har mamlakatda foydalanuvchi → organik o'sish

Bu mumkin chunki:
├── Wikidata: 500,000+ obida, 195 mamlakat — bepul
├── NLLB-200: 200 til tarjima — bepul, mahalliy
├── AI kontent generatsiya: skalasi cheksiz
└── Dataset to'plash — AI agentlar bajaradi

Kengayish prioriteti (foydalanuvchilar oqimiga qarab):
1-oy:  O'zbekiston (to'liq) + Markaziy Osiyo
2-oy:  Ipak Yo'li: Xitoy, Eron, Turkiya, Hindiston
3-oy:  Evropa: Italiya, Gretsiya, Ispaniya (UNESCO saytlari)
4-oy:  Arab davlatlari, Afrika (Misr, Marokash)
5-oy:  Amerika (Meksika, Peru — Maya, Inka sivilizatsiyalari)
6-oy:  Osiyo-Tinch okeani (Yaponiya, Tailand, Kambodja)

Har mamlakat uchun minimum:
├── 50+ obida (asosiy UNESCO va mashhur saytlar)
├── Mahalliy til + Ingliz
└── Asosiy tavsif va fotolar
```

---

### Savol 46: Investitsiya va moliyalash rejasi?

**Berilgan javob:** Barcha mumkin bo'lgan variantlar ko'rib chiqiladi.

**Asoslanma:**

```
Moliyalash strategiyasi — bosqichma-bosqich:

Hozir (Bootstrapped):
├── Server: universitetda bepul
├── AI tools: max plan sotib olingan
├── Developer: 0 xarajat (o'zimiz)
└── Boshqa: $136/yil (Apple + Google + domain)

Imkoniyatlar (parallel ko'rib chiqiladi):

Grant yo'nalishi:
├── UNESCO: "Digitizing Cultural Heritage" dasturlari
├── USAID: O'rta Osiyo madaniy meros dasturlari
├── O'zbekiston hukumati: IT Park innovatsiya granti
├── World Bank: turizm rivojlantirish fondlari
└── Aga Khan Foundation: Markaziy Osiyo madaniyat

Angel/VC:
├── O'zbekiston: IT Park investitsiya, Uzum Ventures
├── Mintaqa: Baring Vostok, Da Vinci Capital
└── Global: madaniy meros va travel tech sektori

Davlat shartnomasi (B2G):
├── O'zbekiston Turizm vazirligi: yillik kontrakt
└── Milliy platforma: davlat subsidiyasi

Accelerator:
├── Y Combinator: Cultural Heritage / Travel Tech
├── Plug and Play: Tourism vertikali
└── Google for Startups: AI-powered ilova
```

---

### Savol 47: 5 yildan keyin SilkLens nima bo'lishi kerak?

**Berilgan javob:** Barcha mumkin bo'lgan variantlarni qilamiz.

**Asoslanma:**

```
Kelajak stsenariylari (barchasi ochiq):

Stsenariy A — Global #1 Cultural App:
├── 50M+ foydalanuvchi, 100+ mamlakat
├── UNESCO rasmiy digital partneri
└── IPO yoki katta fond investitsiyasi

Stsenariy B — Acquisition (sotish):
├── Google: Maps va Arts & Culture ga integratsiya
├── TripAdvisor: kontent va AI qo'shish
├── Airbnb: Experiences funksiyasi uchun
└── O'zbekiston davlati: milliy platforma sifatida

Stsenariy C — Platform (API economy):
├── SilkLens SDK — boshqa ilovalar integratsiya qiladi
├── Heritage data API — akademik va biznes mijozlar
└── AI model litsenziyalash

Stsenariy D — Social Mission:
├── Non-profit + commercial wing
├── UNESCO/ICOMOS bilan rasmiy tuzilma
└── Madaniy meros digitalizatsiyasi — misiyamiz

Qaror qilish vaqti: 2-3 yildan keyin, bozor ko'rsatadi.
Hozir barcha yo'l ochiq qolsin — arxitektura ham shunga mos bo'lsin.
```

---

### Savol 48: Loyihaning eng katta muvaffaqiyat ko'rsatkichi nima?

**Berilgan javob:** Barchasi professional tarzda qilinadi.

**Asoslanma:**

```
Muvaffaqiyat — ko'p o'lchovli:

Texnik ko'rsatkichlar:
├── Obida tanish aniqligi: >90%
├── App crash rate: <0.1%
├── API uptime: 99.9%
└── App Store rating: 4.8+

Foydalanuvchi ko'rsatkichlari:
├── NPS (Net Promoter Score): >50
├── D30 retention: >40%
├── Session uzunligi: >10 daqiqa
└── Haftada 3+ kirish

Biznes ko'rsatkichlari:
├── MRR (oylik daromad): o'sish grafigi muhim
├── CAC:LTV nisbati: >3:1
├── Premium konversiya: >5%
└── B2B MRR: umumiy daromadning >30%

Ijtimoiy ta'sir:
├── O'zbekiston turizm oqimiga ta'sir (iqtisodiyot)
├── Digitallashtirilgan obidalar soni
├── Ta'lim sektorida ishlatiladigan maktablar
└── Xalqaro matbuotda eslatishlar soni
```

---

## Raund 13 — Yakuniy Qarorlar

---

### Savol 49: Birinchi hafta nima qilinadi?

**Berilgan javob:** Arxitektura va texnik stack loyihalash.

**Asoslanma:**

```
Nima uchun arxitektura birinchi:

"Measure twice, cut once" printsipi:
├── Noto'g'ri arxitektura → keyinchalik refactoring → 2x vaqt
├── To'g'ri poydevor → barcha funksiyalar shu ustiga quriladi
└── AI agentlar to'g'ri arxitektura bo'lsa samaraliroq ishlaydi

Birinchi hafta deliverables:
1. ADR (Architecture Decision Records) hujjatlar
2. Monorepo tuzilmasi GitHub da
3. Docker Compose: barcha servislar local da ishlaydi
4. Database schema: obidalar, foydalanuvchilar, media, i18n
5. AI model benchmark: GPU serverda qaysi model ishlaydi
6. CI/CD pipeline: push → test → build avtomatik

Arxitektura qarorlari hujjatlashtiriladi chunki:
├── AI agentlar keyingi sessiyada nima uchun shu qaror qilinganini biladi
├── Qaror o'zgartirish kerak bo'lsa — sabab ma'lum
└── Yangi developer (yoki agent) onboarding tezroq

Birinchi hafta — koddan ko'ra ko'proq dizayn.
```

---

### Savol 50: Loyiha nomi va brend parametrlari.

**Berilgan javob:** Loyiha nomi, logotip va shu kabi barcha barcha parametrlar admin nazoratida to'liq dinamik tarzda boshqarilishi kerak.

**Asoslanma:**

```
Bu qaror katta strategik ahamiyatga ega:

White-label imkoniyati:
├── Toshkent shahar hokimligi: "Visit Tashkent" brendi bilan
├── Samarqand turizm: "Samarkand Guide" brendi bilan
├── Xitoy partneri: Xitoy tili va brendi bilan
└── Barchasi bir xil texnik platforma, boshqa brend

Dynamic branding texnikasi:
├── Remote config: app_name, logo_url, primary_color, splash_image
├── Flutter: ThemeData runtime da o'zgaradi
├── Splashscreen: startda config yuklanadi → brend ko'rsatiladi
└── App icon: Dynamic App Icon (iOS 10.3+, Android 13+)

Admin brending panel:
├── Ilova nomi (barcha tillarda)
├── Logotip (SVG, PNG — light/dark versiya)
├── Asosiy rang (#hex)
├── Splash screen (video yoki rasm)
├── Onboarding matnlari
└── Footer va "Haqida" sahifasi matnlari

Texnik implementatsiya:
Config server → ilova startup da yuklanadi → ThemeData o'rnatiladi
Har konfiguratsiya o'zgarishi → 5 daqiqada ilovada ko'rinadi
App Store ga yangi versiya yuklash shart emas
```

---

### Savol 51: AI agentlar loyihada qanday rol o'ynaydi?

**Berilgan javob:** AI agentlar loyihada 99% rol o'ynaydi. Men faqat review qilib, xato topsam yoki qo'shimcha qilish kerak bo'lsa aytib turaman.

**Bu hujjatni o'qiyotgan AI agentga maxsus yo'riqnoma:**

```
Siz SilkLens loyihasida asosiy ijrochi sifatida ishlaysiz.
Loyiha egasi strategik yo'nalish beradi, siz bajarasiz.

Sizning majburiyatlaringiz:
├── Mustaqil qaror qabul qilish: "qanday qilsam?" deb so'ramang
├── Professional standartda yozish: "minimal" yoki "MVP" emas
├── Hujjatlashtirish: har qadamni izohlang
├── Test yozish: kod bilan birga test ham
└── Qarorlaringizni asoslang: nima uchun bu yondashuv?

Qaror qabul qilish ierarxiyasi:
1. Bu hujjatda javob bor → shu bo'yicha qiling
2. Roadmap.md da ko'rsatilgan → shu bo'yicha qiling
3. Loyiha falsafasiga mos → eng professional variantni tanlang
4. Noaniqlik bor → qisqa savollar bering

Nima qilmang:
├── Hardcode qilmang (narx, nom, rang, model nomi)
├── "TODO: keyinroq" deb qoldirmang
├── Sodda yechim bilan qoniqmang
└── Faqat bajarish emas — yaxshiroq qilish yo'lini toping

Muloqot uslubi:
├── Nima qilganingizni qisqa aytib o'ting
├── Muhim qarorlarni asoslang
└── Xato bo'lsa darhol aytib keling
```

---

### Savol 52: Roadmap formati qanday bo'lsin?

**Berilgan javob:** Barchasi professional uslubda bo'lishi kerak.

**Asoslanma:**

```
Professional roadmap mezonlari:

Tuzilma:
├── Faza + haftalik breakdown (ikki darajali)
├── Har faza uchun aniq deliverables
├── KPI va muvaffaqiyat mezonlari
└── Risklar va yechimlar

Ko'rsatkichlar:
├── Har hafta uchun tekshirib bo'ladigan natijalar
├── Metrikalar: aniqlik, vaqt, son
└── Foydalanuvchi nuqtai nazaridan natija

Kelajakka qarab:
├── 1-hafta: juda aniq (kunlik)
├── 1-oy: aniq (haftalik)
├── 6-oy: yo'nalish (oylik)
└── 1 yil+: vizyon (choraklik)

Tirik hujjat:
├── Har sprint da yangilanadi
├── Bajarilgan ← belgisi qo'yiladi
└── Yangi fursatlar qo'shiladi
```

---

## Xulosa: Loyiha Ruhi

Ushbu hujjatni o'qigan har bir AI agent yoki developer
quyidagi uchta tamoyilni yodlab olsin:

```
1. MAKSIMAL   — Har narsani maksimal darajada qiling.
                "Yetarlicha" emas, "eng yaxshi".

2. DINAMIK    — Hech narsa qotib qolmasin.
                Hamma narsa admin paneldan o'zgartirilsin.

3. PROFESSIONAL — Kod, arxitektura, hujjat, test —
                   barchasi professional standartda.
```

> Bu hujjat 2026-05-18 kuni o'tkazilgan 13 raundlik (50 savol)
> interaktiv sessiya asosida tuzilgan.
> Loyiha egasi: menarzullayev
> Hujjat versiyasi: 1.0
