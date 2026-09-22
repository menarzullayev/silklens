# SilkLens — Complete Design System Prompt for Claude AI

> Use this prompt verbatim with Claude (or any AI design tool) to generate comprehensive UI/UX mockups for the SilkLens mobile application. The prompt is self-contained and provides all context needed to produce production-quality designs.

---

## THE PROMPT

---

You are a senior product designer specializing in cultural heritage mobile applications, with deep expertise in Flutter Material Design 3, travel UX, and cross-cultural visual systems. I need you to design the complete UI/UX system for **SilkLens** — an AI-powered global cultural heritage discovery platform built on Flutter for iOS and Android.

---

### WHAT IS SILKLENS

SilkLens (Silk Road + Lens) is the world's most ambitious cultural heritage app. Users point their smartphone camera at any monument, temple, ruin, or artwork anywhere on Earth and instantly receive:
- AI-powered recognition with multilingual context
- An audio guide narrated in the user's language (200 languages via NLLB-200 + Kokoro TTS)
- Augmented Reality overlay showing historical information on top of the live camera feed
- AI chat — ask the monument any question ("When were you built?" "Who commissioned you?")
- GPS navigation to the site and nearby heritage
- Community features: reviews, ratings, social feed, gamification

The platform is built by a single developer leveraging AI agents at 99% leverage. It is already in active development with:
- FastAPI backend: 100+ endpoints, 275 passing tests
- Flutter app: 24 screens wired (auth, heritage, camera, map, chat, gamification, billing)
- ~200 seeded heritage sites (Uzbekistan UNESCO sites + Central Asia)
- Full backend for: auth (Argon2 + JWT), RBAC, gamification (XP/badges/streaks/leaderboards), billing (Stripe + Payme + Click), AI services (vision/TTS/translation/chat), social graph, offline bundles

**Business model:** Freemium B2C (free tier + premium subscription) + B2B white-label API for tour agencies + B2G government contracts with tourism ministries.

**Brand philosophy:** SilkLens = Discovery, Culture, Heritage, Exploration. Tone: educated, adventurous, inclusive, trustworthy. The name evokes the Silk Road (history, trade routes, cultural exchange) and Lens (camera, discovery, optical clarity, scientific curiosity).

**Languages:** Uzbek, Russian, English, Chinese (launch) → Arabic, Persian, Turkish, German, French, Spanish → 200 languages via NLLB-200 AI. RTL support required.

**Geography:** Uzbekistan → Central Asia → Silk Road corridor (China/Iran/Turkey/India) → Europe → Global.

---

### CURRENT DESIGN SYSTEM (to preserve and extend)

The app currently uses a **Premium Dark Navy** color scheme extracted from the live codebase:

#### Exact Color Values (currently in code)
```
Deep Navy:         #0D2337   (primary background, status bar)
Brand Blue:        #1A3A5C   (secondary background, card surfaces)
Accent Blue:       #1E4976   (gradient endpoint, interactive states)
White 100%:        #FFFFFF   (primary text, primary button fill, logo)
White 65%:         rgba(255,255,255,0.65) — tagline text
White 55%:         rgba(255,255,255,0.55) — secondary labels
White 45%:         rgba(255,255,255,0.45) — borders, dividers
White 18%:         rgba(255,255,255,0.18) — glass surface fills
White 8%:          rgba(255,255,255,0.08) — subtle glow shadows
White 6%:          rgba(255,255,255,0.06) — radial gradient edge
```

#### Current Gradient (Splash and Auth screens)
```
LinearGradient: top → bottom
  stops: [#0D2337 @ 0%, #1A3A5C @ 50%, #0D2337 @ 100%]
Logo ring: RadialGradient [rgba(255,255,255,0.18) → rgba(255,255,255,0.06)]
Logo ring border: rgba(255,255,255,0.35), 1.5dp
Logo glow shadow: rgba(255,255,255,0.08), blur 32, spread 8
```

#### Current Typography
```
App Name "SilkLens" (Splash):  46sp, weight 800, letterSpacing 4
App Name (Auth Choice):        34sp, weight 800, letterSpacing 2
Tagline:                       15sp, weight 400, letterSpacing 2
Primary Button:                16sp, weight 700
Secondary Button:              16sp, weight 600
Section Heading:               24sp, bold
Body:                          16sp, regular
Caption:                       14sp, grey
Planned font family:           Inter (Google Fonts) — not yet bundled
```

#### Current Spacing System
```
Screen horizontal padding:  28dp
Primary button height:      54dp
Button border radius:       14dp
Logo circle (splash):       128dp diameter
Logo circle (auth):         80dp diameter
Standard vertical gaps:     8 / 12 / 16 / 24 / 36dp
Minimum tap target:         48×48dp (accessibility)
```

---

### THE 27 SCREENS REQUIRING DESIGN

Design ALL of the following screens. Group them into sections:

#### Section 1: Auth Flow (8 screens)
1. **Splash Screen** — Animated logo reveal (compass icon in glowing circle), "SilkLens" wordmark, "Cultural Heritage Explorer" tagline, subtle loading indicator. 1.8-second display minimum.
2. **Language Selection** — First-run only. Grid or list of 4 initial languages (UZ/RU/EN/ZH) with flags and native script. "More coming soon" footer. Friendly, welcoming.
3. **Onboarding (3 slides)** — Slide 1: "Discover" — monuments with camera frame overlay. Slide 2: "Recognize" — AI identification result. Slide 3: "Explore" — map with heritage pins. Each has headline, body text, and illustration area.
4. **Auth Choice** — Sign In button (white filled), Sign Up button (outlined), Guest Continue link. Logo centered above. Current dark gradient maintained.
5. **Sign In** — Email field + Password field + Show/Hide toggle. Google OAuth button (branded). Biometric button (fingerprint/Face ID icon, appears when device supports it). Forgot Password link. Create account link below.
6. **Sign Up** — Display Name, Email, Password, Confirm Password. Terms of Service checkbox with link. Submit button. Sign In link.
7. **Forgot Password** — Email field only. "Send reset link" button. Back navigation. Success state (checkmark illustration + "check your email" message).
8. **Email OTP Verify** — 6 individual input boxes (like bank-grade OTP UI). Auto-advance on digit entry. Resend timer (60s countdown). User's masked email shown above.

#### Section 2: Main App — Heritage Discovery (4 screens)
9. **Heritage List (Home)** — Bottom navigation bar (Home / Map / Camera / Social / Profile). Heritage cards with hero image, site name (multilingual), country flag, period label, category badge (Archaeological / Religious / Palace / Natural). Shimmer skeleton loading state. Search bar. Filter chips (country, kind, UNESCO only).
10. **Heritage Detail** — Full-bleed hero image with parallax scroll. Back button. Bookmark/save icon. Share icon. Site name large. Location chip (country + admin region). Period label. UNESCO badge if applicable. Confidence score (AI data quality). Tabbed content: Description (markdown) / Facts / Photos / Reviews. Sticky action bar at bottom: Audio Guide button (play/pause) + "Ask AI" button + Navigate button.
11. **Heritage Search** — Search field with voice input icon. Recent searches. Category filter pills. Country filter. Results list with compact cards. "No results" empty state with suggestion to broaden.
12. **Saved Heritage** — Grid of bookmarked sites with heart indicator. Empty state: compass illustration + "Start exploring to save sites."

#### Section 3: Camera & AI Recognition (2 screens)
13. **Camera Viewfinder** — Full-bleed camera preview with NO margins. Floating close button (top-left). Circular capture button (large, bottom-center, 72dp). Gallery pick icon (bottom-left). Flash toggle (top-right). Scanning animation frame (animated corners in brand color, pulses while analyzing). "Point camera at any monument" helper text (appears briefly, fades after 3s).
14. **Recognition Result** — Bottom sheet sliding up over camera preview. Site name (large, bold). AI confidence bar. Short description (2-3 lines). Category badge + country flag. "View Full Details" CTA button (full-width, filled). "Search similar" secondary button. Dismiss handle at top of sheet.

#### Section 4: Map (1 screen)
15. **Interactive Map** — Full-screen map (dark terrain tiles preferred). Heritage site pins (custom markers: compass icon with glow in brand color). Cluster bubbles for dense areas. Bottom search/filter bar (search field + filter button, floats over map). Tap pin → mini heritage card popup anchored to pin. My location button. Current location blue dot. Legend (optional).

#### Section 5: AI Chat (1 screen)
16. **Heritage Chat** — Conversation-style layout. Context header at top (heritage site name + thumbnail — "Talking to: Registan, Samarkand"). Chat messages: user bubbles (brand blue, right-aligned) + AI responses (dark surface, left-aligned, with site avatar). Input bar at bottom with send button. Typing indicator (3 animated dots). "Suggested questions" chips appear when conversation is empty.

#### Section 6: Social (3 screens)
17. **Social Feed** — Activity cards: "[Friend] discovered [Site]" with thumbnail. "[Friend] earned [Badge]". "[Friend] wrote a review." Like + comment + share on each card. Stories row at top (friends' recent discoveries). Floating camera FAB.
18. **User Profile (Own)** — Avatar (large circle) + display name + bio. Stats row: Visited / Badges / XP / Followers. World map heatmap showing visited countries. Recent activity grid (photos of visited sites). Follow/Unfollow button if viewing another user. Badges row (3 most recent earned).
19. **Review Composer (Bottom Sheet)** — Star rating (1-5, large touch targets). Dimension sliders: Architecture, Preservation, Accessibility, Storytelling (each 0-10). Photo attach strip (up to 5 photos). Text review area. Anonymous toggle. Submit button. Sheet handle at top.

#### Section 7: Gamification (2 screens)
20. **Badges Collection** — Grid layout (3 columns). Badge cards: icon (64dp), badge name, "earned on [date]" or grey lock overlay for unearned + progress hint. Animated shimmer on newly earned badges. Filter: All / Earned / Locked. "Share achievement" button on earned badges.
21. **Leaderboard** — Segment control: This Week / This Month / Friends / My City. Top 3 highlighted with gold/silver/bronze treatment (podium or ranked chips). Rank list items: position number, avatar, display name, XP score. "Your position" sticky bar at bottom if user is outside top 10.

#### Section 8: Billing (4 screens)
22. **Plans Comparison** — Current plan indicated. Free vs Premium (vs Enterprise if applicable). Features checklist for each tier. Price (region-adjusted; e.g., $0.99/mo Uzbekistan, $4.99/mo Global). Annual discount badge ("Save 40%"). CTA button per tier. "All plans include..." footer.
23. **Checkout** — Order summary card (plan name + price). Payment method selector: Credit Card / Payme / Click (shown based on user region). Stripe card fields (number, expiry, CVV). Apple Pay / Google Pay if available. Legal footnote (auto-renews, cancel anytime). "Subscribe Now" button (large, brand accent).
24. **Manage Subscription** — Current plan tile (name + renewal date + amount). Usage stats (heritage viewed this month, audio guides played, AI chats used). Cancel subscription flow (with retention modal: "Are you sure? You'll lose..."). Change plan button. Billing history link.
25. **Invoice List** — Chronological list. Each row: date, amount, plan, status (Paid/Pending/Refunded), download PDF icon. Empty state for free users.

#### Section 9: Settings & Profile Detail (2 screens)
26. **Settings** — Profile section (avatar, display name, email). Preferences: Language (current selection), Theme (Dark/Light/System), Notifications (toggles per type: push/email/SMS). Account: Change password, Biometric login toggle, Connected accounts (Google). Privacy: Export data, Delete account. About: Version, Terms, Privacy Policy, Open source licenses.
27. **Onboarding Completion / Welcome** — Full-screen success state after first sign-up. Confetti animation. "Welcome to SilkLens, [Name]!" Personalization prompt: "What are you most interested in?" — 4 category pills (Architecture / Religion / Nature / Archaeology). CTA: "Start Exploring."

---

### FOUR DESIGN VARIANTS

Produce complete mockups for ALL 27 screens in EACH of the following 4 variants. Each variant is a full design system, not just a color change.

---

#### VARIANT A — Premium Dark (Refine Current Theme)
**Concept:** The existing dark navy palette elevated to world-class quality. Think Apple at night. Museum-grade.

**Color System:**
- Background primary: `#0A1929` (deeper than current `#0D2337`)
- Background surface: `#0F2744` (card surfaces)
- Background elevated: `#162F52` (modals, sheets)
- Brand accent: `#2563EB` (vivid blue — replaces current muted blue)
- Gold accent: `#F59E0B` (UNESCO badges, premium indicators, XP stars)
- Success: `#10B981`
- Error: `#EF4444`
- Text primary: `#FFFFFF`
- Text secondary: `rgba(255,255,255,0.70)`
- Text tertiary: `rgba(255,255,255,0.45)`
- Borders: `rgba(255,255,255,0.12)`
- Glass surfaces: `rgba(255,255,255,0.06)` with backdrop blur

**Typography:**
- Font: **Inter** (all weights 400/500/600/700/800)
- Display: 48sp weight 800
- Headline: 28sp weight 700
- Title: 20sp weight 600
- Body: 16sp weight 400
- Caption: 12sp weight 400 (secondary color)

**Special elements:**
- Heritage cards: glass morphism with subtle blue-white gradient border at top
- Camera viewfinder: animated corner brackets in `#2563EB` with pulse glow
- Map pins: glowing blue teardrop with compass needle inside
- XP bar: gradient left-to-right `#2563EB` → `#7C3AED` (blue to purple)
- Audio waveform visualizer on heritage detail when playing
- Micro-shimmer on card load (left→right white gradient sweep)

---

#### VARIANT B — Cultural / Earthy (Silk Road Heritage Feel)
**Concept:** Warm terracotta, aged gold, desert sand, lapis lazuli. Inspired by Samarkand tilework, Persian manuscript illumination, and the physical colors of the Silk Road landscape.

**Color System:**
- Background primary: `#1A0F0A` (very dark warm brown, like old leather)
- Background surface: `#2D1B12` (dark terracotta)
- Background elevated: `#3D2418` (warm dark card)
- Terracotta accent: `#C2501F` (primary actions, active states)
- Gold: `#D4A017` (premium, UNESCO, achievements, highlights)
- Lapis Lazuli: `#1B4B8A` (links, secondary actions — Silk Road blue)
- Sand: `#E8C99A` (secondary text, subtle fills)
- Ivory: `#F5ECD7` (primary text on dark backgrounds)
- Copper: `#B87333` (badges, meta labels)
- Success: `#4A7C59`
- Error: `#C0392B`

**Typography:**
- Primary font: **Playfair Display** for headings (serif — editorial, cultural authority)
- Secondary font: **Inter** or **Nunito** for body and UI labels
- Heritage site names: Playfair Display 24sp italic
- Body: Inter 16sp regular in `#E8C99A` on dark backgrounds
- Decorative: Consider Naskh-style letter forms for section dividers (as SVG ornament, not actual Arabic font)

**Special elements:**
- Cards: warm dark background with aged-gold hairline border at top and bottom
- Section dividers: arabesque geometric pattern (SVG, 1px gold line with central diamond motif)
- Heritage category badges: terracotta pill with gold text
- Map tiles: warm sepia terrain (custom Mapbox style) with gold pin markers shaped like miniature minarets
- Camera overlay: arch-shaped frame (pointed arch, like Islamic architecture) instead of square brackets
- Onboarding illustrations: flat art with Silk Road motifs — caravans, camels, domes, crescent moons, geometric star patterns
- Achievement badges: medallion style with geometric Islamic border pattern
- Audio guide button: gramophone/scroll icon (cultural metaphor)
- Bottom navigation: warm dark bar with gold active indicator dot above tab

---

#### VARIANT C — Modern Light (Clean, Google-like, Accessible)
**Concept:** Brilliant white, minimal chrome, lots of breathing room. Maximum accessibility. Think Google Arts & Culture meets Apple Maps. For users who want to focus entirely on the content (photography and text).

**Color System:**
- Background primary: `#FFFFFF`
- Background surface: `#F8F9FA` (Google Grey 50 equivalent)
- Background elevated: `#FFFFFF` (cards, same as bg — differentiated by shadow)
- Brand primary: `#1A73E8` (Google Blue — familiar, trustworthy)
- Brand secondary: `#34A853` (cultural green — UNESCO / nature heritage)
- Amber accent: `#FBBC04` (gamification, stars, achievements)
- Text primary: `#202124` (near-black)
- Text secondary: `#5F6368` (medium grey)
- Text tertiary: `#9AA0A6` (light grey)
- Divider: `#E8EAED`
- Error: `#D93025`
- Card shadow: `rgba(0,0,0,0.10)` 0px 2px 8px

**Typography:**
- Font: **Google Sans** (or **DM Sans** as open equivalent)
- Display: 40sp weight 700
- Headline: 24sp weight 600
- Title: 18sp weight 500
- Body: 16sp regular `#202124`
- Caption: 13sp regular `#5F6368`

**Special elements:**
- Heritage cards: white card with photo top-half, bottom half text. Elevated shadow. No borders.
- Top app bar: white with bottom shadow, search integrated inline
- Bottom nav: white bar, no border, subtle shadow. Active tab: blue with filled icon + label.
- Empty states: illustrated (Material Design Spot Illustrations style) in blue + green
- Map: Google Maps light style with blue pin markers
- Camera: minimal HUD — white rounded square frame + white circular capture button
- Subscription plans: side-by-side comparison cards, premium plan highlighted with brand blue border
- FAB (camera, compose): round, brand blue, white icon, heavy elevation shadow

---

#### VARIANT D — Immersive (Full-Bleed Photography + Glass Morphism)
**Concept:** Heritage photography is the hero. Every screen is built around full-bleed, edge-to-edge imagery. UI elements float over images using glass morphism (frosted glass blur). Cinematic, editorial, National Geographic quality feel.

**Color System:**
- Backgrounds: Heritage photos (full bleed) — no solid background colors visible
- Glass surface: `rgba(12,18,26,0.65)` with `backdropFilter: blur(20dp)` (dark frosted glass)
- Glass surface light: `rgba(255,255,255,0.15)` with `backdropFilter: blur(16dp)` (light frosted glass for contrast)
- Glass border: `rgba(255,255,255,0.20)` (hairline glass edge highlight)
- Accent: `#60A5FA` (sky blue — feels natural over landscape photography)
- Gold: `#FBBF24` (stars, achievements — visible over any photo)
- Text primary: `#FFFFFF` (always white — readable over glass)
- Text secondary: `rgba(255,255,255,0.75)`
- Overlay gradient: `linear-gradient(to top, rgba(0,0,0,0.85) 0%, transparent 60%)` — bottom scrim over hero images

**Typography:**
- Font: **SF Pro Display** (iOS system) / **Roboto** (Android) — use system font for native feel
- Heritage site name on hero: 32sp, weight 700, white, on bottom scrim
- Floating labels: 14sp, glass pill backgrounds
- Body text (below fold): white on glass surface, 16sp

**Special elements:**
- Heritage list: vertical scroll of full-bleed photo cards (edge-to-edge). Site name at bottom of each card on gradient scrim. Cards are 240dp tall (3 fit in viewport with peek of 4th).
- Heritage detail: sticky full-bleed hero image (parallax), text content scrolls over in glass sheet
- Camera viewfinder: bare — no chrome, just the view. Thin glass bar at bottom with capture, gallery, flash controls.
- Recognition result: large glass bottom sheet (80% screen height). Big confident typography over site background image.
- Map: satellite/aerial imagery style with blurred glass sidebar for search
- Social feed: each activity card is a blurred background derived from the heritage photo
- Auth screens: landmark photography (Registan, Great Wall, Colosseum, Taj Mahal) as full-bleed background, glass card overlay for form fields
- Onboarding: cinematic slideshow of stunning heritage photography, minimal text overlay
- Dark mode IS the mode — there is no light variant for this theme; it is inherently immersive

---

### REQUIRED DESIGN DELIVERABLES

For each of the 4 variants, provide:

#### 1. Design Token File
```
tokens/
  colors.json         — all named colors with hex/rgba values
  typography.json     — font family, sizes, weights, line heights for each role
  spacing.json        — base unit (4dp), named spacings (xs/sm/md/lg/xl/2xl)
  radius.json         — border radius for button/card/modal/badge/avatar
  elevation.json      — shadow definitions (0/1/2/3/4 levels)
  animation.json      — duration/easing for each transition type
```

#### 2. Component Library (All variants)
Specify visual design for each component with exact measurements:

**Navigation:**
- Bottom navigation bar — height, icon size, active/inactive states, indicator style
- Top app bar — height (56dp standard), title alignment, action icons
- Back button style — iOS vs Android differences

**Buttons (5 types):**
- Primary filled button — 54dp height, 14dp radius, full-width and compact variants
- Secondary outlined button — matching dimensions, border weight
- Text button — for tertiary actions
- Icon button — 48×48dp minimum
- FAB (Floating Action Button) — 56dp, extended FAB for camera

**Cards:**
- Heritage card (list) — image height, text layout, badge placement
- Heritage card (compact) — for map popup and search results
- Achievement/badge card — icon, title, description, earned state

**Input Fields:**
- Text field (outlined) — 52dp height, 12dp radius, label behavior, error state
- OTP input box — 48×48dp each, 8dp gap, active/filled/error states
- Search bar — integrated vs standalone variants

**Data Display:**
- XP progress bar — height 8dp, gradient fill, milestone markers
- Streak counter — flame icon + number
- Confidence meter — horizontal bar for AI recognition result
- Rating display (read) — star row with half-star support
- Rating input — large touch-target stars (40dp each)
- Leaderboard rank chip — #1 gold, #2 silver, #3 bronze

**Feedback:**
- Shimmer skeleton — for card loading (exact shimmer gradient spec)
- Offline banner — dismissible, top or bottom position
- Toast notification — success/error/info variants
- Empty state — illustration + headline + body + optional CTA
- Loading indicator — branded circular progress

**Media:**
- Audio guide player bar — play/pause, waveform visualization, position scrubber
- Photo grid (review attach) — 3-column, add button, delete icon on each
- Heritage hero image — aspect ratio, loading placeholder, caption overlay

#### 3. Screen Mockups
All 27 screens × 4 variants = 108 total screens. For each screen provide:
- Phone frame: 393×852dp (iPhone 15 Pro scale reference)
- Safe area: 44dp top, 34dp bottom (iOS values; Android differs but design to same)
- Navigation bar awareness at bottom
- Both content-full and empty states where applicable
- Annotation layer: call out component names and key measurements

#### 4. Navigation Flow Diagram
A single diagram showing:
- All screen nodes
- Transition arrows labeled with trigger (tap / swipe / camera result / auth success)
- Entry points (deep links, notifications)
- Modal vs push navigation distinction
- Bottom tab navigation hub

#### 5. Micro-Animation Descriptions
For each significant animation, specify:
- Trigger: what causes it
- Duration: in milliseconds
- Easing curve: (Curves.easeOutCubic / Spring / etc.)
- Properties animated: opacity, scale, translateY, etc.
- Any shimmer, glow, or particle effects

Key animations to specify:
1. **Splash logo reveal** — scale 0.72→1.0 + fade-in over 1400ms, easeOutBack; tagline fades in at 50% through
2. **Auth slide-up** — screen slides from y+8% with fade, easeOutCubic 300ms (currently wired)
3. **Home entry** — scale 0.96→1.0 + fade, easeOutCubic 400ms (currently wired)
4. **Badge unlock** — scale 0→1.15→1.0 with golden particle burst, 600ms
5. **Recognition result reveal** — bottom sheet spring-up, simultaneous confidence bar count-up animation
6. **XP award** — counter tick-up animation + brief gold flash on XP card
7. **Streak milestone** — flame icon scale pulse + warm glow ring, 800ms
8. **Audio play button** — icon morphs from play triangle to waveform/bars, 200ms
9. **Camera scan frame** — corner brackets animate inward → pulsing while processing → checkmark on success
10. **Map pin appear** — pins drop in with spring bounce, staggered by 50ms each

#### 6. Dark Mode Variants
For Variant A (Premium Dark), provide dark mode — this IS the dark mode.
For Variant B (Cultural/Earthy), provide dark mode — this IS effectively dark already; ensure light text contrast.
For Variant C (Modern Light), provide explicit dark mode mappings:
- Background: `#121212` → `#1E1E1E` → `#2C2C2C`
- Text: white → grey hierarchy
- Cards: slightly elevated from background
For Variant D (Immersive), always dark — no light variant.

---

### TECHNICAL CONSTRAINTS (Non-Negotiable)

1. **Flutter Material Design 3** — All components must be expressible as M3 Flutter widgets. Specify `ThemeData` `colorScheme` values for each variant.

2. **Minimum tap target: 48×48dp** — Every interactive element (buttons, icons, nav items, list items) must meet this minimum. Annotate any element that appears visually smaller but uses padding to reach 48×48.

3. **Portrait orientation primary** — All screen designs are portrait. Landscape allowed for camera and map but not required in this delivery.

4. **RTL language support** — All layouts must be mirrored-safe for Arabic/Persian future support. Avoid absolute left/right positioning — use leading/trailing semantics. Navigation arrows must flip. Annotations should note RTL behavior.

5. **Safe area compliance** — Status bar (44dp iOS) and home indicator (34dp iOS) areas must be respected. Content must not overlap either.

6. **Dynamic theming** — Design as if colors come from a design token system. The admin panel can change primary colors at runtime. Designs should demonstrate token-based thinking, not hardcoded appearance.

7. **Offline state awareness** — Every screen that loads remote data must have:
   - Loading state (shimmer skeleton)
   - Loaded state
   - Error state (with retry action)
   - Offline state (cached data indicator or offline banner)

8. **Accessibility** — Minimum WCAG AA contrast (4.5:1 for normal text, 3:1 for large text). Indicate any exception with reasoning.

---

### BRAND GUIDELINES

#### Voice & Tone
- **Educated but not academic**: Complex history made approachable
- **Adventurous but not reckless**: Encouraging exploration with safety
- **Inclusive**: Works for 7-year-olds and PhD archaeologists alike
- **Trustworthy**: AI data quality indicators, source attribution, confidence scores
- **Celebratory**: Every discovery is worthy of celebration (gamification)

#### Iconography Direction
- **Compass**: Primary brand metaphor — navigation, discovery, orientation. Compass rose used in app icon, logo, empty states.
- **Silk Road patterns**: Geometric Islamic star patterns as decorative borders, section dividers, badge frames
- **Architectural silhouettes**: Domes, minarets, arches, pagodas — as empty state illustrations and category icons
- **Lens/aperture**: Secondary brand metaphor — the camera, the act of looking, focus
- **Map and route**: Journey, connection, the road itself
- **Flame**: Streaks (Duolingo-style) — urgency, continuity
- **Medallion/shield**: Achievement badges — honor, accomplishment

#### Category Icon Set (custom icons needed)
| Category | Icon Concept |
|---|---|
| Archaeological | Broken column or artifact shard |
| Religious | Dome with crescent or generic temple outline |
| Palace/Royal | Crown silhouette or fortress gate |
| Natural Heritage | Mountain + tree |
| UNESCO Listed | UN olive branch wreath in blue |
| Museum | Columns and pediment |
| Industrial | Gear + chimney (e.g., historic factories) |
| Underwater | Wave + anchor |

#### Photography Style
For mockup placeholder images:
- Golden hour lighting preferred (warm, cinematic)
- Avoid tourist-crowded shots — architectural purity
- Mix of iconic global sites: Registan (Samarkand), Great Wall, Colosseum, Angkor Wat, Taj Mahal, Petra, Machu Picchu, Alhambra, Acropolis
- For Uzbekistan-specific: Registan, Shah-i-Zinda, Bibi-Khanym, Kalon Minaret, Ark Fortress

---

### DELIVERABLE FORMAT

Structure your output as follows:

**1. Design System Overview** — 1 page per variant summarizing the complete token system with color swatches, type scale, and spacing system.

**2. Component Library** — Each component shown in all relevant states (default, hover, active, disabled, error, loading).

**3. Key Screen Mockups** — Prioritize these 12 screens first (one per variant = 48 total):
   1. Splash
   2. Onboarding (slide 1)
   3. Auth Choice
   4. Heritage List (Home)
   5. Heritage Detail
   6. Camera Viewfinder
   7. Recognition Result
   8. Map
   9. AI Chat
   10. Badges Collection
   11. Leaderboard
   12. Plans Comparison

Then complete the remaining 15 screens.

**4. Navigation Flow Diagram** — Single diagram for the entire app (variant-agnostic since navigation structure is the same across all variants).

**5. Animation Spec Sheet** — Text descriptions for all 10 key animations listed above.

**6. Dark Mode Mappings** — Token delta tables for Variant C (the only one with a meaningful light→dark shift).

**7. Flutter ThemeData Specification** — For each variant, provide the key `ThemeData` / `ColorScheme` values that a Flutter developer would use to implement the theme. Include:
   - `colorScheme.primary`
   - `colorScheme.onPrimary`
   - `colorScheme.surface`
   - `colorScheme.background`
   - `colorScheme.surfaceVariant`
   - `textTheme.displayLarge` / `headlineLarge` / `titleLarge` / `bodyLarge` / `labelLarge`
   - `cardTheme.shape` (border radius)
   - `elevatedButtonTheme` shape and padding
   - `navigationBarTheme` indicator color and height

---

### REFERENCE APPLICATIONS FOR INSPIRATION

Study these apps for specific UX patterns (do not copy — extract principles):

| App | What to Borrow |
|---|---|
| **Duolingo** | Gamification UI — streak flame animation, XP bar, badge unlock dopamine loop, leaderboard layout with rivalry context |
| **Google Arts & Culture** | Heritage card quality — full-bleed art photography, editorial typography, "Explore Nearby" map, color palette extraction from artwork |
| **Atlas Obscura** | Discovery tone — "hidden wonders" framing, editorial headlines with curiosity hooks, layered content depth |
| **iNaturalist** | Camera → ID flow — real-time scanning animation, result confidence meter, community validation indicators |
| **Shazam** | Core UX metaphor — single large CTA centered on screen, instant feedback, minimal cognitive load during recognition |
| **Airbnb** | Photography-first card design — how to make photography the hero while maintaining scannable text hierarchy |
| **BeReal / Instagram** | Camera UX — how to make the camera feel native and immediate, not like a feature |
| **Apple Maps (Dark Mode)** | Map design — dark terrain, pin design, card popups anchored to map |
| **Spotify** | Audio playback UX — mini-player persistence, waveform visualization, play state transitions |
| **Headspace** | Calm, trusted design — how to make a tech product feel warm and trustworthy |

---

### FINAL INSTRUCTION

Produce the most comprehensive, production-ready mobile UI/UX design system you can for SilkLens. This app will be submitted to the App Store and Google Play and must look indistinguishable from a top-tier venture-backed startup. The single developer building this app is leveraging AI agents for 99% of the work — your designs will be the visual foundation that the entire team builds from.

Every design decision should serve three goals:
1. **Discoverability** — Make it irresistible to explore more heritage
2. **Trust** — Make AI-powered information feel authoritative and accurate
3. **Delight** — Make every interaction feel rewarding and worth returning to

Begin with the Design System Overview for all 4 variants, then proceed to the component library, then screen mockups.
