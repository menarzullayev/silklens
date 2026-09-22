# SilkLens — Frontend Gap Analysis & Implementation Task Board
> **JIRA-style · Generated:** 2026-05-23  
> **Asosi:** Flutter mobile (45 sahifa) + Next.js admin (15 route) chuqur tahlil  
> **Ticket format:** `SILK-NNNN` (barcha `PROGRESS.md` ga ham kiritiladi)

---

## 📊 Summary Dashboard

| Platform | Jami sahifa | ✅ To'liq | 🔄 Qisman | 🏗️ Demo/Stub | ❌ Yo'q |
|---|---|---|---|---|---|
| **Flutter Mobile** | 45 | 8 (auth) | 3 | 32 | 2 |
| **Next.js Admin** | 15 | 9 | 1 | 4 | 1 |
| **Jami** | **60** | **17** | **4** | **36** | **3** |

### Holat tushuntirishi
- ✅ **To'liq** — real API bilan bog'langan, production-ready
- 🔄 **Qisman** — UI tayyor, API qisman yoki stub
- 🏗️ **Demo** — chiroyli UI, hardcoded static data
- ❌ **Stub** — placeholder yoki butunlay yo'q

---

## 🏷️ Epiklar ro'yxati

| Epic | Platform | Tickets | Prioritet |
|---|---|---|---|
| EPIC-M1: Heritage Screens API Wiring | Flutter | 6 | 🔴 P1 |
| EPIC-M2: Camera & AR Recognition | Flutter | 3 | 🔴 P1 |
| EPIC-M3: Maps Real Data | Flutter | 2 | 🟠 P2 |
| EPIC-M4: Billing & Payments | Flutter | 4 | 🔴 P1 |
| EPIC-M5: Gamification API Wiring | Flutter | 5 | 🟠 P2 |
| EPIC-M6: Social Features API Wiring | Flutter | 4 | 🟠 P2 |
| EPIC-M7: Profile & Reviews | Flutter | 2 | 🟠 P2 |
| EPIC-M8: Settings & GDPR | Flutter | 4 | 🟠 P2 |
| EPIC-M9: Auth Extensions | Flutter | 3 | 🔴 P1 |
| EPIC-M10: New Feature Screens (backend ready) | Flutter | 16 | 🟠 P2 |
| EPIC-M11: Infrastructure & Quality | Flutter | 8 | 🔴 P1 |
| EPIC-A1: Admin Stub Pages | Admin | 5 | 🔴 P1 |
| EPIC-A2: i18n Completion | Admin | 4 | 🟠 P2 |
| EPIC-A3: Auth Improvements | Admin | 3 | 🟠 P2 |
| EPIC-A4: New Feature Admin Pages | Admin | 9 | 🟠 P2 |
| EPIC-A5: Quality & DX | Admin | 4 | 🟡 P3 |

**Jami: 82 ticket**

---

# 🔴 EPIC-M1: Heritage Screens — API Wiring

> **Holat:** UI to'liq tayyor. Providers mavjud. Sahifalar hardcoded data ishlatmoqda.

---

## SILK-0093 · HeritageListPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M1 |
| **Sahifa** | `lib/presentation/pages/heritage/heritage_list_page.dart` |
| **Severity** | 🔴 Critical |
| **Effort** | 3 kun |
| **Deps** | — |

### Holat
`HeritageListPage` `HookWidget` ishlatadi lekin `heritageListProvider`'ni o'qimaydi. `_demoData` static const'dan foydalanadi — 6 ta hardcoded karta.

### Muammo
```dart
// HOZIR (noto'g'ri):
final items = _demoData; // static

// KERAK:
final state = ref.watch(heritageListProvider);
```

### Implementation
1. `heritageListProvider` ni `ConsumerWidget`'ga o'tkazish
2. `GET /v1/heritage?limit=20&country_code=UZ` dan data fetch
3. Pagination (infinite scroll) qo'shish
4. Category chips → kind_slug filter → `GET /v1/heritage?kind={slug}`
5. Search bar → `/search?q={query}` navigate
6. Loading shimmer state
7. Error state (tarmoq yo'q, server xato)
8. Empty state

### DoD
- [ ] Real API dan meros ro'yxati ko'rinadi
- [ ] Category filter ishlaydi
- [ ] Pull-to-refresh ishlaydi
- [ ] Pagination (LoadMore yoki infinite scroll)
- [ ] Shimmer loading ko'rinadi
- [ ] Error va empty state UI bor

---

## SILK-0094 · HeritageDetailPage → Real API + Audio

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M1 |
| **Sahifa** | `lib/presentation/pages/heritage/heritage_detail_page.dart` |
| **Severity** | 🔴 Critical |
| **Effort** | 4 kun |
| **Deps** | SILK-0093 |

### Holat
Detail sahifasi hardcoded Registon ma'lumotlari ko'rsatadi. 5 tab bor (Haqida/Faktlar/Sharhlar/Audio/AR) lekin barchasi static.

### Implementation
1. `heritageDetailProvider(pubId)` ni sahifaga ulash
2. `GET /v1/heritage/{pub_id}` dan real data
3. **Faktlar tab:** `heritage_facts` dan predicate'ga qarab — tarix, qurilish materiali, arxitektor
4. **Sharhlar tab:** `GET /v1/heritage/{id}/reviews` real sharhlar
5. **Audio tab:** TTS endpointdan audio URL olish, `just_audio` bilan play
6. Hero image: `MediaOut.signed_url`
7. Harita tugmasi → MapPage (`lat`, `lng` bilan)
8. "Yo'nalish" → tashqi Google Maps deep link
9. Review yozish (ReviewComposerSheet)

### DoD
- [ ] Real heritage data ko'rinadi
- [ ] Multilingual name/description til bo'yicha ko'rinadi
- [ ] Sharhlar real API'dan
- [ ] Audio play/pause ishlaydi (`just_audio`)
- [ ] Rasmlar cached_network_image bilan
- [ ] Share button ishlaydi

---

## SILK-0095 · SearchPage + SearchResultsPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M1 |
| **Sahifa** | `heritage/search_page.dart` + `heritage/search_results_page.dart` |
| **Severity** | 🔴 High |
| **Effort** | 3 kun |
| **Deps** | — |

### Holat
`SearchPage` local state, `SearchResultsPage` 6 hardcoded natija.

### Implementation
1. `GET /v1/search?q={query}&lang={locale}&limit=20`
2. Debounce 400ms (type-as-you-search)
3. `recentSearchesProvider` — so'nggi qidiruvlar (local Hive)
4. Country + kind filter → `GET /v1/search?country={code}&kind={slug}`
5. Empty result → zero-result state

### DoD
- [ ] Qidiruv real API'dan natija qaytaradi
- [ ] Debounce ishlaydi
- [ ] Filter chips ishlaydi
- [ ] So'nggi qidiruvlar saqlanadi va ko'rinadi

---

## SILK-0096 · AudioGuidePage → just_audio + TTS API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M1 |
| **Sahifa** | `lib/presentation/pages/heritage/audio_guide_page.dart` |
| **Severity** | 🔴 High |
| **Effort** | 3 kun |
| **Deps** | SILK-0094 |

### Holat
Audio player UI to'liq chiroyli — scrubber, speed 0.75x–2x, til bayroqlari. Lekin `_progress` local state, haqiqiy audio yo'q.

### Implementation
1. Heritage description → `POST /v1/ai/tts {text, language}` → `media_asset_id + signed_url`
2. `AudioPlayer` (just_audio) bilan `signed_url` play
3. `AudioPlayer.positionStream` → scrubber progressi
4. Speed 0.75x/1x/1.25x/1.5x/2x → `AudioPlayer.setSpeed()`
5. Til tugmalari → til o'zgarsa yangi TTS fetch
6. Background play (Android audio session)
7. Waveform animation (playing paytida)
8. Cache: MinIO'da saqlangan, ikkinchi marta fetch yo'q

### DoD
- [ ] Audio real TTS endpoint'dan
- [ ] Play/pause/seek ishlaydi
- [ ] Speed control ishlaydi
- [ ] Til o'zgartirish ishlaydi
- [ ] Background play ishlaydi (Android)

---

## SILK-0097 · OfflineModePage → Real Offline Bundle API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M1 |
| **Sahifa** | `lib/presentation/pages/heritage/offline_mode_page.dart` |
| **Severity** | 🟠 Medium |
| **Effort** | 4 kun |
| **Deps** | Backend SILK-0055 (done) |

### Holat
5 hardcoded kesh elementi. Backend `GET /v1/offline/bundles` tayyor.

### Implementation
1. `GET /v1/offline/bundles?region=uz_all&language={locale}` — bundle ro'yxati
2. Bundle card: nom, hajm (MB), versiya, yuklab olingan/yo'q
3. **Download** tugmasi → `GET /v1/offline/bundles/{id}/manifest` → fayllarni yuklab olish
4. Progress indicator (BytesReceived / TotalBytes)
5. Hive'da yuklab olingan fayl yo'llari saqlash
6. **Delete** → lokal fayllarni o'chirish
7. Offline rejim toggle → boshqa sahifalarda `ConnectivityPlus` check

### DoD
- [ ] Bundle ro'yxati real API'dan
- [ ] Download progress ko'rinadi
- [ ] Downloaded bundle offline rejimda ishlaydi
- [ ] Delete ishlaydi

---

## SILK-0098 · HeritageDetailPage: Kids Story + Cultural Tips tabs

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M1 |
| **Sahifa** | `heritage_detail_page.dart` ichida yangi tablar |
| **Severity** | 🟠 Medium |
| **Effort** | 2 kun |
| **Deps** | SILK-0094, Backend SILK-0068, SILK-0069 (done) |

### Implementation
1. **Bolalar tab:** `GET /v1/heritage/{id}/kids-story` → simplified story
2. **Madaniyat tab:** `GET /v1/heritage/{id}/cultural-tips` → etiquette cards
3. **Hikoyalar tab:** `GET /v1/heritage/{id}/stories` → local legends
4. Kids mode toggle → user_profiles.kids_mode → simplified content

---

# 🔴 EPIC-M2: Camera & AR Recognition

---

## SILK-0099 · CameraPage — Real Camera Implementation

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M2 |
| **Sahifa** | `lib/presentation/pages/camera/camera_page.dart` |
| **Severity** | 🔴 Critical |
| **Effort** | 5 kun |
| **Deps** | Backend SILK-0050 (done — Claude Vision) |

### Holat
12 satr `CameraPage` — `"Coming soon"` placeholder. `camera ^0.11.0` paket mavjud.

### Implementation
1. `CameraController` init (back camera)
2. Camera preview fullscreen (16:9 ratio)
3. **Capture button** → `XFile` → base64 → `POST /v1/ai/recognize {media_asset_id}`
4. Capture flow:
   - Media upload: `POST /v1/media/uploads (multipart)`
   - Recognize: `POST /v1/ai/recognize {media_asset_id, language}`
5. Result overlay: recognized site name + confidence badge
6. "Ko'proq bilish" → `HeritageDetailPage(pubId: result.heritage_pub_id)`
7. **AR overlay button** → `ArOverlayWidget` (stub initially, real ARCore FAZA-APEX)
8. Zoom pinch gesture
9. Flash toggle
10. Gallery from `image_picker`

### DoD
- [ ] Kamera ochiladi
- [ ] Capture ishlaydi, server'ga yuboriladi
- [ ] Recognition natijasi overlay'da ko'rinadi
- [ ] Heritage detail'ga navigate qiladi
- [ ] Permission denied graceful handling

---

## SILK-0100 · AI Photo Guide Screen

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M2 |
| **Sahifa** | Yangi: `camera/photo_guide_page.dart` |
| **Severity** | 🟠 Medium |
| **Effort** | 2 kun |
| **Deps** | SILK-0099, Backend SILK-0067 (done) |

### Implementation
1. Heritage pub_id bilan `POST /v1/ai/photo-guide {mode: "angle"}`
2. Compass overlay sahifada ko'rinadi (optimal burchak)
3. Tavsiya: vaqt, masofa, yo'nalish
4. "Before/After" mode → `overlay` response
5. Gallery'ga saqlash

---

## SILK-0101 · Voice Assistant Screen (ASR)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M2 |
| **Sahifa** | Yangi: `camera/voice_assistant_page.dart` |
| **Severity** | 🟠 Medium |
| **Effort** | 3 kun |
| **Deps** | Backend SILK-0066 (done — Whisper) |

### Implementation
1. Mikrofon tugmasi (press & hold to record)
2. `record` paketi → WebM audio → `POST /v1/media/uploads`
3. `POST /v1/ai/asr {media_asset_id, language}` → `text + command_intent`
4. Intent handling:
   - `EXPLAIN_PLACE` → TTS narration
   - `TRANSLATE` → translation dialog
   - `NEXT_STOP` → trip navigator
   - `NAVIGATE` → maps
5. Waveform animation recording paytida

---

# 🟠 EPIC-M3: Maps Real Data

---

## SILK-0102 · MapPage → Real Heritage Markers

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M3 |
| **Sahifa** | `lib/presentation/pages/map/map_page.dart` |
| **Severity** | 🟠 Medium |
| **Effort** | 3 kun |
| **Deps** | — |

### Holat
OSM xarita ishlaydi, 4 hardcoded marker.

### Implementation
1. `GET /v1/heritage?country_code=UZ&limit=100` → lat/lng markerlar
2. `FlutterMap MarkerLayer` — har bir heritage uchun custom gold marker
3. Marker tap → bottom sheet: nom + photo thumb + "Ko'rish" tugmasi
4. Cluster (ko'p marker bitta joyda bo'lsa) — `flutter_map_marker_cluster`
5. GPS user location → `geolocator` → "Yaqin obidalar"
6. Listings (hotel/restoran) → `GET /v1/listings?lat&lng&category`
7. Category filter chips (heritage / hotel / restoran / transport)
8. Search bar → `GET /v1/search?q=`

### DoD
- [ ] Heritage markerlar real API'dan
- [ ] Marker tap bottom sheet ishlaydi
- [ ] GPS joylashuv ishlaydi
- [ ] B2B listing markerlar ko'rinadi

---

## SILK-0103 · Trip Planner Screen (yangi sahifa)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M3 |
| **Sahifa** | Yangi: `map/trip_planner_page.dart` |
| **Severity** | 🟠 Medium |
| **Effort** | 4 kun |
| **Deps** | Backend SILK-0061 (done) |

### Implementation
1. Shaharlar tanlash (multi-select: Samarqand, Buxoro, Xiva...)
2. Sana va byudjet kirish
3. `POST /v1/trips {cities, start_date, end_date, budget_usd}` → AI plan
4. Kunlik jadval: drag-reorder stops
5. MapPage'da marshrut chiziq ko'rinishi (Polyline)
6. Trips ro'yxati: `GET /v1/trips`
7. Quick Plan: "Menda 2 soat bor" → `POST /v1/trips/quick-plan`

---

# 🔴 EPIC-M4: Billing & Payments

---

## SILK-0104 · PlansPage → Real Billing API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M4 |
| **Sahifa** | `lib/presentation/pages/billing/plans_page.dart` |
| **Severity** | 🔴 High |
| **Effort** | 2 kun |
| **Deps** | — |

### Holat
3 hardcoded plan karta. Toggle oylik/yillik ishlaydi (UI).

### Implementation
1. `GET /v1/billing/plans?pricing_zone=central_asia`
2. Plan feature list: `plan_features` dan
3. Joriy obuna: `GET /v1/billing/me/subscription`
4. Highlighted: joriy reja card
5. Toggle oylik/yillik → narxlar o'zgaradi

---

## SILK-0105 · CheckoutPage → Real Payment Integration

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M4 |
| **Sahifa** | `lib/presentation/pages/billing/checkout_page.dart` |
| **Severity** | 🔴 High |
| **Effort** | 5 kun |
| **Deps** | SILK-0104 |

### Holat
4 to'lov metodi UI bor. `flutter_stripe` import lekin integration yo'q.

### Implementation
1. **Karta (Stripe):**
   - `flutter_stripe`: `Stripe.instance.initPaymentSheet()`
   - `POST /v1/billing/subscriptions {plan_slug, payment_method_token}`
   - `Stripe.presentPaymentSheet()`
2. **Payme (UZS):**
   - `POST /v1/billing/subscriptions` → `payment_intent.external_url`
   - `url_launcher` bilan Payme webview
3. **Click (UZS):**
   - Shunga o'xshash Payme flow
4. **Kupon kodi input:**
   - `POST /v1/billing/coupons/validate {code}`
   - Chegirma ko'rsatish
5. **Idempotency-Key** header qo'shish
6. **Success/Failure** state handling
7. IAP: Apple/Google (future)

### DoD
- [ ] Stripe karta to'lov ishlaydi
- [ ] Payme to'lov ishlaydi
- [ ] Kupon kodi qabul qilinadi
- [ ] Success state → `ManageSubscriptionPage`

---

## SILK-0106 · InvoicesPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M4 |
| **Sahifa** | `lib/presentation/pages/billing/invoices_page.dart` |
| **Severity** | 🟠 Medium |
| **Effort** | 2 kun |
| **Deps** | — |

### Implementation
- `GET /v1/billing/me/invoices?limit=20&offset=0`
- Pagination
- Download PDF (signed URL)
- Status badge: paid/pending/failed

---

## SILK-0107 · ManageSubscriptionPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M4 |
| **Sahifa** | `lib/presentation/pages/billing/manage_subscription_page.dart` |
| **Severity** | 🟠 Medium |
| **Effort** | 2 kun |
| **Deps** | SILK-0104 |

### Implementation
- `GET /v1/billing/me/subscription`
- `GET /v1/billing/me/entitlements` → usage stats (AI calls, Audio, AR)
- Cancel: `POST /v1/billing/subscriptions/cancel {at_period_end: true}`
- Resume: `POST /v1/billing/subscriptions/resume`

---

# 🟠 EPIC-M5: Gamification API Wiring

---

## SILK-0108 · XPDashboard → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M5 |
| **Sahifa** | `lib/presentation/pages/gamification/xp_card.dart` |
| **Severity** | 🟠 Medium |
| **Effort** | 2 kun |

### Implementation
- `GET /v1/me/xp` → `{current_xp, lifetime_xp, level, next_level, xp_to_next_level, progress_pct}`
- `GET /v1/me/streak` → `{current_streak, longest_streak}`
- Level-up animatsiya (confetti + level_up_dialog)
- `POST /v1/me/streak/tick` → kunlik check-in reward

---

## SILK-0109 · BadgesPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M5 |
| **Effort** | 2 kun |

### Implementation
- `GET /v1/me/badges` → earned/in-progress badges
- Filter: All/Earned/In Progress
- Badge detail bottom sheet (criterion, rarity, XP reward)

---

## SILK-0110 · LeaderboardPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M5 |
| **Effort** | 2 kun |

### Implementation
- `GET /v1/leaderboards` → list
- `GET /v1/leaderboards/{slug}?period=weekly&limit=50`
- Period toggle: Daily/Weekly/Monthly/All-time
- Scope: Global/Friends

---

## SILK-0111 · MissionsPage → Gamification

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M5 |
| **Effort** | 2 kun |

### Implementation
- Daily/Weekly/Special missions (gamification backend'dan)
- XP progress bar
- "Claim" tugmasi

---

## SILK-0112 · StreakPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M5 |
| **Effort** | 1 kun |

### Implementation
- `GET /v1/me/streak`
- Haftalik kalendar real data bilan
- Freeze credits ko'rsatish

---

# 🟠 EPIC-M6: Social Features API Wiring

---

## SILK-0113 · ActivityFeedPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M6 |
| **Effort** | 3 kun |

### Implementation
- `GET /v1/social/feed?limit=20` (cursor-based pagination)
- `ActivityItemOut`: verb (visit/review/badge/follow) + target + actor
- Like: `POST /v1/social/reactions` (reaction_slug: "❤️")
- Comment: via `ReviewComposerSheet`
- Stories row: `GET /v1/social/following/{pub_id}` → latest activity
- Traveler discovery: `GET /v1/social/travelers/nearby` → nearby users button

---

## SILK-0114 · NotificationsPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M6 |
| **Effort** | 2 kun |

### Implementation
- `GET /v1/notifications?unread_only=false&limit=30`
- `POST /v1/notifications/{id}/read`
- `POST /v1/notifications/mark-all-read`
- FCM deep link → sahifaga navigate

---

## SILK-0115 · FollowingListPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M6 |
| **Effort** | 2 kun |

### Implementation
- `GET /v1/social/following/{pub_id}?limit=30`
- `GET /v1/social/followers/{pub_id}`
- Follow: `POST /v1/social/follow/{pub_id}`
- Unfollow: `DELETE /v1/social/follow/{pub_id}`
- Block: `POST /v1/social/block/{pub_id}`

---

## SILK-0116 · FriendInvitePage → Real QR + Invite

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M6 |
| **Effort** | 2 kun |

### Implementation
- `POST /v1/social/friends/invite {message}` → `{token, expires_at}`
- QR kod: `qr_flutter` bilan token ko'rsatish
- Deep link: `silklens://invite?token={token}`
- Share button: `share_plus`
- Accept: deep link → `POST /v1/social/friends/accept {token}`

---

# 🟠 EPIC-M7: Profile & Reviews

---

## SILK-0117 · UserProfilePage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M7 |
| **Effort** | 2 kun |

### Implementation
- `GET /v1/auth/me` → joriy user stats
- Profil rasmini upload: `POST /v1/media/uploads`
- `PATCH /v1/me/profile` → display_name, bio
- Travel preferences: age_group, dietary_prefs, travel_style
- Kids mode toggle: `POST /v1/me/kids-mode/enable`

---

## SILK-0118 · ReviewComposerSheet → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M7 |
| **Effort** | 2 kun |

### Implementation
- `POST /v1/heritage/{pub_id}/reviews {body_md, language_tag, ratings}`
- Foto qo'shish: `image_picker` → `POST /v1/media/uploads`
- Validatsiya: min 20 belgi
- Submit → success toast + review list refresh

---

# 🟠 EPIC-M8: Settings & GDPR

---

## SILK-0119 · NotificationPrefsPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M8 |
| **Effort** | 2 kun |

### Implementation
- `GET /v1/notifications/preferences` → kategoriyalar + kanallar
- `PATCH /v1/notifications/preferences [{category_slug, channel, enabled}]`
- `PUT /v1/notifications/quiet-hours {start_time, end_time, weekdays}`
- FCM token register: `POST /v1/notifications/push-devices {platform, installation_id, fcm_token}`

---

## SILK-0120 · PrivacyGDPRPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M8 |
| **Effort** | 2 kun |

### Implementation
- `GET /v1/me/consents` → consent list
- `POST /v1/me/data-export` → data export request
- `GET /v1/me/data-export/{id}` → export status polling
- Legal docs: `GET /v1/legal/privacy_policy`

---

## SILK-0121 · DeleteAccountPage → Real API

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M8 |
| **Effort** | 1 kun |

### Holat
Confirm tugma faqat `context.go('/')` qiladi.

### Implementation
- `POST /v1/me/account/delete {reason}` → 202 + grace_period
- 30 kun muddat haqida ogohlantirish
- Logout → auth state clear

---

## SILK-0122 · ForgotPasswordPage → Backend + UI

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile + Backend |
| **Epic** | EPIC-M8 |
| **Effort** | 3 kun |

### Holat
UI tayyor, `Future.delayed(1500ms)` mock, `TODO` comment bor.

### Backend kerak:
```
POST /v1/auth/forgot-password {email} → sends OTP
POST /v1/auth/reset-password {email, code, new_password}
```

### Implementation
1. Backend endpoint yaratish (migrations emas, Redis OTP ishlatish)
2. Flutter: `POST /v1/auth/forgot-password {email}`
3. OTP kiritish sahifasi (email_verify_page bilan o'xshash)
4. Yangi parol kirish sahifasi

---

# 🔴 EPIC-M9: Auth Extensions

---

## SILK-0123 · Facebook Login → Flutter

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M9 |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0053 (done) |

### Implementation
1. `flutter_facebook_auth` paketi qo'shish
2. Android/iOS Facebook App ID konfig
3. `FacebookAuth.instance.login()` → access_token
4. `POST /v1/auth/facebook {access_token}`
5. `LoginWithFacebook` use case → `AuthRepositoryImpl`

---

## SILK-0124 · Apple Sign In → Flutter

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M9 |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0054 (BLOCKED — Apple Dev Account) |

### Implementation
1. `sign_in_with_apple` paketi
2. iOS: `Info.plist` + App Capabilities
3. `SignInWithApple.getAppleIDCredential()` → identity_token
4. `POST /v1/auth/apple {identity_token}`

---

## SILK-0125 · Instagram Login → Flutter (opsional)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M9 |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0053 (done) |

### Implementation
- `flutter_web_auth_2` yoki `webview_flutter`
- Instagram Basic Display OAuth flow
- `POST /v1/auth/instagram {access_token}`

---

# 🟠 EPIC-M10: New Feature Screens (Backend tayyor)

---

## SILK-0126 · TicketingPage (Muzey chiptalar)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `billing/tickets_page.dart` |
| **Effort** | 3 kun |
| **Deps** | Backend SILK-0065 (done) |

### Implementation
- `GET /v1/ticket-types?heritage_pub_id={id}` → chipta turlari
- `POST /v1/tickets/purchase {ticket_type_id, visit_date}` → ticket + QR
- `GET /v1/tickets/me` → mening chiptalarim
- QR display: `qr_flutter` bilan `qr_payload` ko'rsatish
- Fullscreen QR scan mode

---

## SILK-0127 · EmergencyPage (Xavfsizlik)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `settings/emergency_page.dart` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0057 (done) |

### Implementation
- `GET /v1/emergency?country_code=UZ&language={locale}`
- `GET /v1/emergency/nearest?lat&lng&kind=hospital`
- Bir martalik telefon qilish: `url_launcher` `tel:` scheme
- Maps: `url_launcher` Google Maps link
- OFFLINE cache qilinadi (kritik feature)

---

## SILK-0128 · CulturalTipsPage

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `settings/cultural_tips_page.dart` |
| **Effort** | 1 kun |
| **Deps** | Backend SILK-0069 (done) |

---

## SILK-0129 · WeatherGuidePage

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `map/weather_guide_page.dart` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0074 (done) |

### Implementation
- `GET /v1/ai/weather-guide?lat&lng&language`
- Ob-havo kartasi + tavsiyalar
- Health tips: `GET /v1/ai/health-tips`

---

## SILK-0130 · ExpenseTrackerPage

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `settings/expense_tracker_page.dart` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0072 (done) |

---

## SILK-0131 · MoodTravelPage

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `home/mood_travel_page.dart` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0078 (done) |

---

## SILK-0132 · MemoryBookPage

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `profile/memory_book_page.dart` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0076 (done) |

---

## SILK-0133 · FoodGuidePage

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `map/food_guide_page.dart` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0070 (done) |

---

## SILK-0134 · CarbonFootprintPage

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `settings/carbon_page.dart` |
| **Effort** | 1 kun |
| **Deps** | Backend SILK-0085 (done) |

---

## SILK-0135 · GovernmentInfoPage

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `settings/government_page.dart` |
| **Effort** | 1 kun |
| **Deps** | Backend SILK-0086 (done) |

---

## SILK-0136 · CrowdForecastWidget (HeritageDetail ichida)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Effort** | 1 kun |
| **Deps** | Backend SILK-0075 (done) |

### Implementation
- `GET /v1/heritage/{id}/crowd-forecast` → widget sifatida detail sahifasida
- `POST /v1/me/check-in {heritage_pub_id}` → sahifaga kirganda avtomatik

---

## SILK-0137 · AIUtilitiesPage (Bozor, Scam, Lost&Found)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Sahifa** | Yangi: `settings/ai_utilities_page.dart` |
| **Effort** | 3 kun |
| **Deps** | Backend SILK-0080 (done) |

### Implementation
- **Savdolashish:** `POST /v1/ai/fair-price {item, market}`
- **Scam tekshirish:** `POST /v1/ai/scam-check {venue_name, quoted_price_usd}`
- **Lost & Found:** `GET /v1/ai/lost-found?item_type={passport}&lat&lng`
- TabBar: Bozor | Xavfsizlik | Yo'qolgan narsa

---

## SILK-0138 · ReviewAnalysisPage (HeritageDetail tab)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M10 |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0071 (done) |

---

# 🔴 EPIC-M11: Infrastructure & Quality

---

## SILK-0139 · FCM Push Notifications Integration

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M11 |
| **Severity** | 🔴 Critical |
| **Effort** | 3 kun |
| **Deps** | Backend SILK-0059 (done) |

### Holat
`sentry_flutter` bor, FCM yo'q.

### Implementation
1. `firebase_messaging` paket qo'shish
2. `google-services.json` (Android) + `GoogleService-Info.plist` (iOS) setup
3. `FirebaseMessaging.instance.getToken()` → `POST /v1/notifications/push-devices`
4. Foreground notification: `flutter_local_notifications`
5. Background handler: `@pragma('vm:entry-point')`
6. Deep link: notification → sahifaga navigate

### DoD
- [ ] FCM token registratsiya ishlaydi
- [ ] Foreground push ko'rinadi
- [ ] Background push tap → sahifaga navigate
- [ ] Token refresh handle qilinadi

---

## SILK-0140 · German + Korean Locale (de/ko) Flutter

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M11 |
| **Severity** | 🔴 High |
| **Effort** | 3 kun |
| **Deps** | Backend SILK-0079 (done) |

### Holat
Mijoz talabi: 6 til. Hozir uz/ru/en/zh bor.

### Implementation
1. `app_de.arb` + `app_ko.arb` yaratish (barcha 130+ key)
2. `l10n.yaml` ga `de` va `ko` qo'shish
3. `LanguageSelectionPage` → 6 til + bayroq ikonka
4. API calls'da `Accept-Language: de` yoki `ko` header

---

## SILK-0141 · Hardcoded Strings → ARB l10n Fix

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M11 |
| **Severity** | 🟠 Medium |
| **Effort** | 3 kun |

### Muammo
Ko'plab sahifalarda hardcoded o'zbek matni bor (ARB string'lari ishlatilmagan).

### Implementation
- `EmailVerifyPage` hardcoded o'zbek → `AppLocalizations`
- Barcha 🏗️ Demo sahifalar uchun ARB string'larni ishlatish
- Missing key'larni `app_en.arb`'ga qo'shish (4 til hammasi)

---

## SILK-0142 · Release Signing Setup (Android)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M11 |
| **Severity** | 🔴 Critical (App Store uchun) |
| **Effort** | 1 kun |

### Holat
`android/app/build.gradle` da `signingConfigs.debug` production release uchun ham ishlatilmoqda.

### Implementation
1. `silklens.keystore` yaratish (`keytool`)
2. `key.properties` (gitignore'd) → `storePassword`, `keyAlias`, `keyPassword`
3. `build.gradle` → `release { signingConfig signingConfigs.release }`
4. `android:usesCleartextTraffic` → prod'da `false`
5. iOS: Xcode signing sertifikati

---

## SILK-0143 · Missing Assets (Onboarding, Textures)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M11 |
| **Severity** | 🟠 Medium |
| **Effort** | 2 kun (dizayner bilan) |

### Holat
`assets/onboarding/.gitkeep` — rasm yo'q. `assets/textures/.gitkeep` — bo'sh.

### Implementation
- Onboarding: 3 ta PNG rasm (Registon, Kalon, Ichan Qal'a) 1080×1920
- Texture: O'zbek naqshlari (islamic geometry SVG/PNG)
- Bundled fonts (Google Fonts offline)

---

## SILK-0144 · Isar Migration (Hive → Isar v4)

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M11 |
| **Severity** | 🟡 Low |
| **Effort** | 3 kun |

### Holat
`pubspec.yaml` da `hive_flutter` + `isar` ikkisi ham bor. `isar_database.dart` Isar tayyorlangan lekin `cached_heritage.dart` Hive ishlatadi.

### Implementation
- Hive → Isar v4 migratsiya
- Offline cache schema: Heritage, Branding, Translations
- `IsarDatabase` to'liq implementation

---

## SILK-0145 · Sentry + Analytics Integration

| Maydon | Qiymat |
|---|---|
| **Platform** | Flutter Mobile |
| **Epic** | EPIC-M11 |
| **Severity** | 🟠 Medium |
| **Effort** | 2 kun |

### Implementation
1. `SENTRY_DSN` → `.env` dan
2. `SentryFlutter.init()` main.dart'da
3. Screen tracking: `GoRouter` + Sentry navigator observer
4. User context: authenticated user'ni Sentry'ga set
5. Analytics events: `POST /v1/analytics/track` (custom events)

---

# 🔴 EPIC-A1: Admin Panel — Stub Sahifalar

---

## SILK-0146 · Admin Users Management Page

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A1 |
| **Route** | `/users` |
| **Severity** | 🔴 High |
| **Effort** | 4 kun |

### Holat
Faqat placeholder text.

### Backend endpoints (mavjud):
- Hozircha foydalanuvchi list endpoint yo'q (faqat `GET /v1/auth/me` va admin functions)
- **Avval kerak:** `GET /v1/admin/users` → user list endpoint yaratish (yangi backend route)

### Implementation
1. Backend: `GET /v1/admin/users?limit&offset&search&trust_tier&residency_region`
2. Admin: Jadval: pub_id, email, display_name, trust_tier, created_at, is_verified
3. Filter: trust_tier, verified, residency
4. User detail drawer: roles, sessions, MFA methods
5. Actions: ban user, change trust_tier, revoke sessions

---

## SILK-0147 · Admin Analytics Dashboard

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A1 |
| **Route** | `/analytics` |
| **Severity** | 🔴 High |
| **Effort** | 4 kun |

### Holat
"Events pipeline tayyorlanmoqda" placeholder.

### Backend endpoints (mavjud):
- `GET /v1/investors/traction` — KPI snapshots
- `analytics_events_raw` table mavjud
- `search_query_log` table mavjud

### Implementation
1. **Traction cards:** MAU, heritage count, ARR → `/v1/investors/traction`
2. **Heritage views chart:** `recharts LineChart` (hozircha static, keyinroq real)
3. **Search analytics:** top queries, zero-result queries
4. **AI usage:** `ai_token_usage` daily chart
5. **Revenue:** invoices total

---

## SILK-0148 · Admin Moderation Queue

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A1 |
| **Route** | `/moderation` |
| **Severity** | 🟠 Medium |
| **Effort** | 3 kun |

### Backend endpoints (mavjud):
- `moderation_queue` table mavjud
- Endpoint kerak: `GET /v1/admin/moderation/queue`

### Implementation
1. Backend: `GET /v1/admin/moderation/queue?status=pending&kind`
2. Admin: UGC moderation jadval (review/comment/photo)
3. Actions: approve/reject/ban_user
4. Auto-mod verdict ko'rsatish

---

## SILK-0149 · Admin Monetization Page

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A1 |
| **Route** | `/monetization` |
| **Severity** | 🟠 Medium |
| **Effort** | 3 kun |

### Backend endpoints (mavjud):
- `GET /v1/billing/plans`
- `GET /v1/admin/tenants/{slug}/revenue-share`
- `GET /v1/investors/traction`

### Implementation
1. Plan management: feature matrix editor
2. Revenue overview: subscriptions, invoices totals
3. Coupon management: `POST/GET /v1/billing/coupons`
4. Reseller revenue share table

---

## SILK-0150 · Admin Heritage People & Materials (new)

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A1 |
| **Route** | `/heritage/people` |
| **Severity** | 🟡 Low |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0092 (done — migration 0105) |

---

# 🟠 EPIC-A2: Admin i18n Completion

---

## SILK-0151 · Admin en.json Translation

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A2 |
| **Effort** | 1 kun |

### Holat
`apps/admin/messages/uz.json` — to'liq. `en.json`, `ru.json`, `zh.json` — yo'q.

---

## SILK-0152 · Admin ru.json Translation

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A2 |
| **Effort** | 1 kun |

---

## SILK-0153 · Admin zh.json Translation

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A2 |
| **Effort** | 1 kun |

---

## SILK-0154 · Admin de.json Translation (optional)

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A2 |
| **Effort** | 1 kun |

---

# 🟠 EPIC-A3: Admin Auth Improvements

---

## SILK-0155 · Admin Google OAuth Working

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A3 |
| **Effort** | 2 kun |

### Holat
Google login tugmasi UI'da bor, `AUTH_GOOGLE_ID` stub. Server Action hardcoded demo credential'ga fallback.

### Implementation
1. `AUTH_GOOGLE_ID` + `AUTH_GOOGLE_SECRET` env vars to'g'ri set
2. `signInWithProviderAction` → real `signIn('google', ...)`
3. `POST /v1/auth/google {access_token}` orqali backend auth

---

## SILK-0156 · Admin Static → API-based Permissions

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A3 |
| **Effort** | 2 kun |

### Holat
`permissionsForTrustTier()` statik ro'yxat qaytaradi.

### Implementation
1. Backend: `GET /v1/auth/me/permissions` endpoint
2. Admin: auth.ts JWT callback'da API'dan permissions fetch
3. Cache: JWT'da saqlash (30 daqiqa TTL)

---

## SILK-0157 · Admin API Types Auto-generation

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A3 |
| **Effort** | 2 kun |

### Holat
`types/api.ts` qo'lda yozilgan.

### Implementation
1. `openapi-typescript` paketi qo'shish
2. `pnpm openapi-typescript http://localhost:8000/openapi.json -o src/types/api.gen.ts`
3. `package.json`'ga script: `"generate:types": "openapi-typescript ..."`
4. CI'da avtomatik generate

---

# 🟠 EPIC-A4: Admin New Feature Pages

---

## SILK-0158 · Admin Emergency Contacts Management

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A4 |
| **Route** | `/emergency` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0057 (done) |

---

## SILK-0159 · Admin Cultural Tips Management

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A4 |
| **Route** | `/cultural-tips` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0069 (done) |

---

## SILK-0160 · Admin Government Info Management

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A4 |
| **Route** | `/government` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0086 (done) |

---

## SILK-0161 · Admin Coupon Management

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A4 |
| **Route** | `/billing/coupons` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0089 (done) |

---

## SILK-0162 · Admin Trips Overview (analytics)

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A4 |
| **Route** | `/analytics/trips` |
| **Effort** | 1 kun |

---

## SILK-0163 · Admin Ticket Types Management

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A4 |
| **Route** | `/heritage/tickets` |
| **Effort** | 2 kun |
| **Deps** | Backend SILK-0065 (done) |

---

## SILK-0164 · Admin Crowd Data View

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A4 |
| **Route** | `/analytics/crowd` |
| **Effort** | 1 kun |
| **Deps** | Backend SILK-0075 (done) |

---

## SILK-0165 · Admin Heritage Storyteller Content

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A4 |
| **Route** | `/heritage/[pub_id]` — yangi "Stories" tab |
| **Effort** | 2 kun |

---

## SILK-0166 · Admin Languages Registry

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A4 |
| **Route** | `/settings/languages` |
| **Effort** | 1 kun |
| **Deps** | Backend SILK-0064 (done) |

---

# 🟡 EPIC-A5: Admin Quality & DX

---

## SILK-0167 · Playwright E2E Tests (Admin)

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A5 |
| **Effort** | 3 kun |

### Holat
`playwright.config.ts` mavjud, testlar yozilmagan.

### Implementation
- Login flow testi
- Heritage CRUD testi
- Feature flags toggle testi
- Permission guard testi

---

## SILK-0168 · Admin Branding Slug from Session

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A5 |
| **Effort** | 1 kun |

### Holat
`branding.ts` da `DEFAULT_SLUG = 'silklens'` hardcoded.

### Fix
```typescript
// from session.tenantSlug instead of hardcoded
```

---

## SILK-0169 · DataTable Unification

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A5 |
| **Effort** | 2 kun |

### Holat
`DataTable` generic component yaratilgan lekin `HeritageListPage` o'z jadvalini ishlatadi.

### Fix
Heritage jadvalini `DataTable` generic'ga o'tkazish.

---

## SILK-0170 · Admin i18n Key Completion (uz.json gaps)

| Maydon | Qiymat |
|---|---|
| **Platform** | Next.js Admin |
| **Epic** | EPIC-A5 |
| **Effort** | 1 kun |

### Holat
`uz.json`'da `nav.featureFlags` key etishmaydi (sidebar render error mumkin).

---

---

# 📊 Prioritized Roadmap

## Sprint 1 (2 hafta) — Auth + Core Infrastructure

| Ticket | Task | Effort |
|---|---|---|
| SILK-0139 | FCM Push Flutter | 3 kun |
| SILK-0140 | German/Korean locale Flutter | 3 kun |
| SILK-0142 | Android Release Signing | 1 kun |
| SILK-0123 | Facebook Login Flutter | 2 kun |
| SILK-0155 | Admin Google OAuth | 2 kun |
| SILK-0157 | Admin API Types Auto | 2 kun |
| **Jami** | | **13 kun** |

## Sprint 2 (2 hafta) — Heritage Core

| Ticket | Task | Effort |
|---|---|---|
| SILK-0093 | HeritageListPage API | 3 kun |
| SILK-0094 | HeritageDetailPage API + Audio | 4 kun |
| SILK-0096 | AudioGuidePage just_audio | 3 kun |
| **Jami** | | **10 kun** |

## Sprint 3 (2 hafta) — Billing + Payments

| Ticket | Task | Effort |
|---|---|---|
| SILK-0104 | PlansPage API | 2 kun |
| SILK-0105 | Checkout Stripe/Payme | 5 kun |
| SILK-0106 | InvoicesPage API | 2 kun |
| **Jami** | | **9 kun** |

## Sprint 4 (2 hafta) — Maps + Search + Camera

| Ticket | Task | Effort |
|---|---|---|
| SILK-0102 | MapPage real markers | 3 kun |
| SILK-0095 | Search real API | 3 kun |
| SILK-0099 | Camera recognition | 5 kun |
| **Jami** | | **11 kun** |

## Sprint 5 (2 hafta) — Gamification + Social

| Ticket | Task | Effort |
|---|---|---|
| SILK-0108 | XP Dashboard API | 2 kun |
| SILK-0109 | Badges API | 2 kun |
| SILK-0110 | Leaderboard API | 2 kun |
| SILK-0113 | Activity Feed API | 3 kun |
| SILK-0114 | Notifications API | 2 kun |
| **Jami** | | **11 kun** |

## Sprint 6 (2 hafta) — Settings + New Features

| Ticket | Task | Effort |
|---|---|---|
| SILK-0119 | NotificationPrefs API | 2 kun |
| SILK-0120 | Privacy/GDPR API | 2 kun |
| SILK-0126 | TicketingPage | 3 kun |
| SILK-0127 | EmergencyPage | 2 kun |
| SILK-0103 | TripPlannerPage | 4 kun |
| **Jami** | | **13 kun** |

## Sprint 7 (2 hafta) — Admin Stubs + i18n

| Ticket | Task | Effort |
|---|---|---|
| SILK-0146 | Admin Users Page | 4 kun |
| SILK-0147 | Admin Analytics | 4 kun |
| SILK-0151-0153 | Admin 3 locale | 3 kun |
| **Jami** | | **11 kun** |

## Sprint 8+ — Remaining Phase 2/3

Qolgan 40+ ticket: mood travel, memory book, carbon, review analysis, admin new pages, Playwright tests va boshqalar.

---

# 📈 Effort Summary

| Epic | Ticket soni | Ish kuni |
|---|---|---|
| EPIC-M1 Heritage | 6 | 19 |
| EPIC-M2 Camera/AR | 3 | 10 |
| EPIC-M3 Maps | 2 | 7 |
| EPIC-M4 Billing | 4 | 11 |
| EPIC-M5 Gamification | 5 | 9 |
| EPIC-M6 Social | 4 | 9 |
| EPIC-M7 Profile | 2 | 4 |
| EPIC-M8 Settings | 4 | 8 |
| EPIC-M9 Auth | 3 | 6 |
| EPIC-M10 New Features | 16 | 26 |
| EPIC-M11 Infrastructure | 8 | 20 |
| EPIC-A1 Admin Stubs | 5 | 16 |
| EPIC-A2 i18n | 4 | 4 |
| EPIC-A3 Auth | 3 | 6 |
| EPIC-A4 New Pages | 9 | 16 |
| EPIC-A5 Quality | 4 | 7 |
| **JAMI** | **82** | **178 kun** |

**Agent leverage bilan (3-5x):** ~35-60 kun ≈ **6-10 sprint (12-20 hafta)**

---

*Generated: 2026-05-23 · Next update: har sprint oxirida*
