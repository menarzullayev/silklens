# /brainstorming — AI Brainstorming Skill

Bu skill foydalanuvchiga har qanday mavzu, muammo yoki loyiha bo'yicha tizimli va kreativ brainstorming sessiyasini o'tkazishda yordam beradi.

## Qanday ishlatish

```
/brainstorming <mavzu yoki muammo>
```

**Misol:**
```
/brainstorming Yangi mobil ilova uchun marketing strategiyasi
/brainstorming Jamoada samaradorlikni oshirish
/brainstorming SaaS mahsulot uchun pricing modeli
```

---

## Skill bajarishi kerak bo'lgan amallar

Foydalanuvchi `/brainstorming <mavzu>` deb yozganda, quyidagi bosqichlarni ketma-ket bajaring:

### 1. Mavzuni tahlil qilish (30 soniya)

Mavzuni qabul qilib, uni uch qirradan tushunib oling:
- **Nima?** — asosiy muammo yoki maqsad nima
- **Kim uchun?** — bu kimga tegishli (foydalanuvchi, mijoz, jamoa)
- **Nega?** — nima uchun bu muhim

### 2. Tezkor g'oyalar generatsiyasi — "Brainstorm Burst"

Kamida **10 ta g'oya** ishlab chiqing. Ularni hech qanday filtrlamasdan, erkin tarzda ro'yxatlang. Har bir g'oya qisqa (1-2 jumla) bo'lsin.

Format:
```
💡 G'oya 1: [sarlavha] — [qisqa tavsif]
💡 G'oya 2: ...
...
```

### 3. Kategoriyalash

G'oyalarni 3-4 ta guruhga ajrating:
- **Darhol amalga oshirilishi mumkin** (quick wins)
- **O'rta muddatli** (1-3 oy)
- **Katta vizion** (uzoq muddatli)
- **Noodatiy / eksperimental**

### 4. Top 3 g'oyani chuqur tahlil qilish

Eng istiqbolli 3 ta g'oya uchun quyidagi formatda tahlil bering:

```
### G'oya: [Nomi]

**Nima uchun kuchli:**
- ...

**Qanday amalga oshirish:**
1. ...
2. ...
3. ...

**Kerakli resurslar:** ...
**Potensial to'siqlar:** ...
**Muvaffaqiyat ko'rsatkichi:** ...
```

### 5. SWOT Express

Umumiy yechim uchun qisqacha SWOT:

| | Ichki | Tashqi |
|---|---|---|
| **+** | Kuchli tomonlar | Imkoniyatlar |
| **−** | Zaif tomonlar | Tahdidlar |

### 6. Keyingi qadam (Next Action)

Sessiyani **1 ta aniq harakat** bilan yakunlang:

```
✅ Tavsiya etilgan birinchi qadam:
[Aniq, o'lchanadigan, bugun boshlanishi mumkin bo'lgan harakat]
```

### 7. Qo'shimcha savollar (ixtiyoriy)

Foydalanuvchiga chuqurroq o'ylashga undash uchun 3 ta strategik savol bering:

```
🔍 O'ylash uchun savollar:
1. ...
2. ...
3. ...
```

---

## Stil va ton qoidalari

- **Ijobiy va ilhomlantiruvchi** tonda yozing — hech qanday g'oyani darhol rad etmang
- **Aniq va amaliy** bo'ling — abstrakt gaplardan saqlaning
- Foydalanuvchi tilida javob bering (o'zbek, rus, ingliz — qay birida yozsa)
- Ro'yxat va jadvallardan keng foydalaning — vizual aniqlik muhim
- Har bir sessiya **maksimum 5-7 daqiqada o'qilishi** kerak

## Qo'shimcha rejimlar

Foydalanuvchi quyidagi flaglarni qo'sha oladi:

| Flag | Tavsif |
|------|---------|
| `--deep` | Har bir g'oyani yanada batafsil tahlil qilish |
| `--fast` | Faqat top 5 g'oya, qisqa format |
| `--team` | Jamoa sessiyasi uchun moslashtirilgan format |
| `--tech` | Texnik loyihalar uchun maxsus tahlil (arxitektura, stack, MVP) |
| `--business` | Biznes/startup konteksti uchun (ROI, bozor, raqobat) |

**Misol:**
```
/brainstorming Yangi feature uchun g'oyalar --tech --fast
```
