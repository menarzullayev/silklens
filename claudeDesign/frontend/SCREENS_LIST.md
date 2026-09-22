# SilkLens Flutter — Screen Inventory

Generated: 2026-05-18
Source: `apps/mobile/lib/presentation/pages/`
Router: `apps/mobile/lib/presentation/router/app_router.dart`

Total screens: **22 dart files** (17 true screens / pages + 5 widgets/stubs/re-exports)

---

## AUTH FLOW

| # | Route Path | Widget Class | File | Description | Status |
|---|-----------|-------------|------|-------------|--------|
| 1 | `/` | `SplashPage` | `auth/splash_page.dart` | Animated logo + tagline on dark-navy gradient. Reads `app_locale` from SharedPrefs and navigates to `/onboarding` (locale already set) or `/language` (first launch). 1 800 ms minimum display time. | **Implemented** |
| 2 | `/language` | `LanguageSelectionPage` | `auth/language_selection_page.dart` | Language picker (UZ / EN / RU / ZH). Pre-selects device system locale; shows flag, native name, animated highlight ring. Saves selection to SharedPrefs and routes to `/onboarding`. | **Implemented** |
| 3 | `/onboarding` | `OnboardingPage` | `auth/onboarding_page.dart` | 3-page swipeable onboarding carousel (Explore, Camera AI, Community). Animated gradient background changes per page. CTA buttons: Next / Get Started → `/auth/sign-in`; Skip → `/auth/choice`. | **Implemented** |
| 4 | `/auth/choice` | `AuthChoicePage` | `auth/auth_choice_page.dart` | Auth gate screen: SilkLens logo + two large buttons (Sign In / Sign Up) and a "Continue as Guest" link. Fade-in entrance animation. | **Implemented** |
| 5 | `/auth/sign-in` | `SignInPage` | `auth/sign_in_page.dart` | Email + password form. Inline validation, password reveal toggle, Google Sign-In button (OAuth stub), "Forgot password" link, guest bypass. Navigates to `/home` on success. | **Implemented (auth call stubbed)** |
| 6 | `/auth/sign-up` | `SignUpPage` | `auth/sign_up_page.dart` | Registration form: email, password (min 8 chars), ToS checkbox. Navigates to `/auth/email-verify?email=…` after mock delay. | **Implemented (auth call stubbed)** |
| 7 | `/auth/forgot-password` | `ForgotPasswordPage` | `auth/forgot_password_page.dart` | Password reset: email field, submit sends reset link. Two states: form view and success confirmation card (green tick + recipient address). | **Implemented (reset call stubbed)** |
| 8 | `/auth/email-verify` | `EmailVerifyPage` | `auth/email_verify_page.dart` | 6-digit OTP input (auto-advance, auto-submit). Shows recipient email. Resend link available. Navigates to `/home` on successful verify. | **Implemented (verify call stubbed)** |

---

## MAIN APP — HERITAGE

| # | Route Path | Widget Class | File | Description | Status |
|---|-----------|-------------|------|-------------|--------|
| 9 | `/home` | `HeritageListPage` | `heritage/heritage_list_page.dart` | Discover feed: shimmer skeleton while loading, then card list of heritage sites (name, country, period). Bottom nav bar (Discover / Map / Camera / Saved / Profile). FAB opens camera. Tap card → `/home/heritage/:pubId`. | **Implemented (hardcoded demo data)** |
| 10 | `/home/heritage/:pubId` | `HeritageDetailPage` | `heritage/heritage_detail_page.dart` | Heritage site detail: hero image placeholder (200 px), title, description, location + date chips. Reads `pubId` from route params. Content loads from API (placeholder text shown). | **Stub** |
| 11 | _(no route)_ | `HeritageSearchPage` | `heritage/heritage_search_page.dart` | Search screen — scaffold with "Search coming soon" placeholder. | **Stub** |
| 12 | _(no route)_ | `SavedHeritagePage` | `heritage/saved_heritage_page.dart` | Saved / bookmarks screen — empty state "No saved items yet". | **Stub** |

---

## MAIN APP — MAP

| # | Route Path | Widget Class | File | Description | Status |
|---|-----------|-------------|------|-------------|--------|
| 13 | `/map` | `MapPage` | `map/map_page.dart` | Interactive map placeholder. Shows map icon + "Interactive map coming in FAZA 2" message. Full flutter_map integration planned for FAZA 2. | **Stub** |

---

## MAIN APP — CAMERA / AI RECOGNITION

| # | Route Path | Widget Class | File | Description | Status |
|---|-----------|-------------|------|-------------|--------|
| 14 | `/camera` | `CameraPage` | `camera/camera_page.dart` | AI heritage recognition camera. Currently shows "Coming soon" placeholder. Planned: live viewfinder + heritage identification overlay. | **Stub** |

---

## MAIN APP — AI CHAT

| # | Route Path | Widget Class | File | Description | Status |
|---|-----------|-------------|------|-------------|--------|
| 15 | _(no route)_ | `ChatPage` | `chat/chat_page.dart` | AI chat interface — "Coming soon" placeholder. | **Stub** |

---

## MAIN APP — GAMIFICATION

| # | Route Path | Widget Class | File | Description | Status |
|---|-----------|-------------|------|-------------|--------|
| 16 | _(no route)_ | `BadgesPage` | `gamification/badges_page.dart` | Earned badges gallery — "Coming soon" placeholder. | **Stub** |
| 17 | _(no route)_ | `LeaderboardPage` | `gamification/leaderboard_page.dart` | XP leaderboard ranking — "Coming soon" placeholder. | **Stub** |

---

## MAIN APP — PROFILE / SOCIAL

| # | Route Path | Widget Class | File | Description | Status |
|---|-----------|-------------|------|-------------|--------|
| 18 | _(no route)_ | `ProfilePage` | `profile/profile_page.dart` | Current user profile — "Coming soon" placeholder. | **Stub** |
| 19 | _(no route)_ | `UserProfilePagePage` | `profile/user_profile_page.dart` | Public profile of another user — "Coming soon" placeholder. | **Stub** |

---

## MAIN APP — BILLING

| # | Route Path | Widget Class | File | Description | Status |
|---|-----------|-------------|------|-------------|--------|
| 20 | _(no route)_ | `PlansPagePage` | `billing/plans_page.dart` | Subscription plans selection — "Coming soon" placeholder. | **Stub** |
| 21 | _(no route)_ | `CheckoutPagePage` | `billing/checkout_page.dart` | Payment checkout flow — "Coming soon" placeholder. | **Stub** |
| 22 | _(no route)_ | `ManageSubscriptionPagePage` | `billing/manage_subscription_page.dart` | Active subscription management — "Coming soon" placeholder. | **Stub** |
| 23 | _(no route)_ | `InvoicesPagePage` | `billing/invoices_page.dart` | Invoice history list — "Coming soon" placeholder. | **Stub** |

---

## COMPONENT / WIDGET FILES (not full screens)

| Widget | File | Purpose |
|--------|------|---------|
| `StreakWidget` | `gamification/streak_widget.dart` | Empty widget placeholder for daily streak display (renders `SizedBox.shrink()`). |
| `XpCard` | `gamification/xp_card.dart` | Empty widget placeholder for XP summary card (renders `SizedBox.shrink()`). |
| `FollowButton` | `profile/follow_button.dart` | Reusable Follow/Unfollow elevated button for social graph actions, takes `pubId` + `isFollowing`. |
| `ReviewComposerSheet` | `profile/review_composer_sheet.dart` | Bottom sheet placeholder for writing a heritage site review — "Coming soon". |
| `HomeShellPage` (root pages/) | `home_shell_page.dart` | Empty stub (real shell is in `router/app_router.dart`). Re-exported by `home_page.dart`. |

---

## ROUTE SUMMARY (from app_router.dart)

```
/                          → SplashPage
/language                  → LanguageSelectionPage
/onboarding                → OnboardingPage (auth/onboarding_page.dart)
/auth/choice               → AuthChoicePage
/auth/sign-in              → SignInPage
/auth/sign-up              → SignUpPage
/auth/forgot-password      → ForgotPasswordPage
/auth/email-verify?email=  → EmailVerifyPage
/home                      → HeritageListPage
/home/heritage/:pubId      → HeritageDetailPage
/map                       → MapPage
/camera                    → CameraPage
```

12 registered routes. All transitions use custom animations (no/fade/slide-up/slide-right/fade-scale).

---

## STATUS SUMMARY

| Status | Count |
|--------|-------|
| Fully implemented (real logic, animations, validation) | 8 |
| Stub / placeholder ("Coming soon") | 11 |
| Widget / component (not a screen) | 5 |
| **Total dart files** | **33** |
