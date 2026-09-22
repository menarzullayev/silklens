# SilkLens Design Tokens
> Extracted from `apps/mobile/lib/presentation/` — 2026-05-18

---

## Color Palette (extracted from code)

### Background / Surface Gradient (auth & splash screens)
- **Primary Dark**: `#0D2337` — deepest background, system nav bar, page scaffold
- **Primary Mid**: `#1A3A5C` — gradient midpoint, brand accent (`_brand` constant)
- **Primary Light**: `#1E4976` — gradient top stop, onboarding page highlight
- Additional midpoints used in gradients: `#1B4F72`, `#154360`

### Theme Token Presets (ThemeTokens — `lib/presentation/theme/theme_tokens.dart`)
| Preset | Primary | Secondary | Accent |
|---|---|---|---|
| **SilkLens Default** | `#B78628` (Silk Road Gold) | `#1F3A93` (Lapis Lazuli Blue) | `#D96C2C` (Terracotta) |
| **Milliy (national)** | `#0E4D92` (deep cobalt) | `#C9A227` (golden) | `#7D0A0A` (crimson) |

### Semantic Colors
- **White**: `#FFFFFF`
- **Error / Validation Red**: `#FF6B6B` — field borders on error, error text, error icons
- **Success Green**: `#4CAF50` — email verification success state
- **Error Banner Red**: `#E53935` — offline banner background
- **Google Blue**: `#4285F4` — Google sign-in button icon color

### Shimmer / Skeleton Colors
- **Shimmer Base**: `#1E3A52`
- **Shimmer Highlight**: `#2A5070`

---

## Typography (from code)

### Default Font Family
- `Roboto` (both `silkLensDefault` and `milliy` presets)
- Overridable at runtime via admin panel branding (`fontFamily` token)
- Inter font family commented-ready in `pubspec.yaml` (weights 400 / 500 / 700)

### Heading Sizes
| Use | Size | Weight |
|---|---|---|
| Page title (language select) | `32sp` | `w800` |
| Page title (auth pages, onboarding) | `28sp` | `w800` |
| Flag emoji display | `28sp` | — |

### Body / Label Sizes
| Use | Size | Weight |
|---|---|---|
| Primary button label | `16sp` | `w700` |
| Language tile name | `16sp` | `w700` (selected) / `w500` (unselected) |
| Body / subtitle | `15sp` | `w500` |
| Secondary body | `14sp` | `w600` (links) / unset (regular) |
| Small / caption / helper | `13sp` | `w500` |

---

## Spacing & Radius (from code)

### Horizontal Page Padding
| Context | Value |
|---|---|
| Dense screens (cards, tabs) | `12dp` symmetric |
| Default fields & content | `16dp` symmetric |
| Standard content sections | `20dp` symmetric |
| Auth page content column | `24dp` symmetric |
| Auth form wrapper | `28dp` symmetric |
| Onboarding slide text | `32dp` symmetric |

### EdgeInsets Patterns
- `EdgeInsets.all(16)` — general container padding
- `EdgeInsets.all(20)` — confirmation / info card padding
- `EdgeInsets.fromLTRB(12, 12, 12, 14)` — heritage card interior
- `EdgeInsets.only(top: 8, right: 16)` — skip-button top offset
- `EdgeInsets.symmetric(horizontal: 4)` — dot indicator margin
- `EdgeInsets.symmetric(horizontal: 12, vertical: ?)` — inline chip / tab
- `EdgeInsets.symmetric(horizontal: 16, vertical: 16)` — text field content padding

### Border Radius
| Component | Radius |
|---|---|
| Text input fields | `12dp` (all four corners) |
| Buttons (primary CTA, outlined) | `14dp` |
| Cards / containers | `14dp` |
| Confirmation / info boxes | `14dp` |
| Onboarding progress dots | `4dp` |
| Shimmer skeleton boxes | `4dp–12dp` (small text: 4, image: 12) |

### Icon Sizes
| Usage | Size |
|---|---|
| Inline text / chip icons | `16dp` |
| Standard action icons | `20dp` |
| App bar / nav icons | `24dp` |
| Medium feature icons | `26dp` |
| Language flag / feature icons | `36dp` |
| Large state icons | `40dp` |
| Avatar / profile placeholder | `56dp` |
| Hero / splash logo area | `64dp–68dp` |
| Heritage card thumbnail | `80dp` |

---

## Current Packages (from pubspec.yaml)

### UI & Layout
| Package | Version | Purpose |
|---|---|---|
| `flutter` + `flutter_localizations` | SDK | Core UI + i18n |
| `hooks_riverpod` | `^2.5.0` | Reactive state management |
| `flutter_hooks` | `^0.20.5` | Hooks for StatefulWidget replacement |
| `go_router` | `^14.0.0` | Declarative navigation (Shazam camera-centered nav) |
| `shimmer` | `^3.0.0` | Skeleton loading placeholders |
| `flutter_markdown` | `^0.7.4` | Markdown rendering (heritage descriptions) |

### Camera & Media
| Package | Version | Purpose |
|---|---|---|
| `camera` | `^0.11.0` | Camera access for AI recognition |
| `image_picker` | `^1.0.7` | Gallery / file image pick |
| `just_audio` | `^0.9.40` | Audio guide playback |

### Maps & Location
| Package | Version | Purpose |
|---|---|---|
| `flutter_map` | `^7.0.0` | Map rendering |
| `latlong2` | `^0.9.1` | Geo coordinate types |
| `geolocator` | `^12.0.0` | Device location |

### Auth & Payments
| Package | Version | Purpose |
|---|---|---|
| `google_sign_in` | `^6.2.0` | Google OAuth |
| `local_auth` | `^2.3.0` | Biometric authentication |
| `flutter_stripe` | `^11.0.0` | Stripe payments (gated) |
| `flutter_secure_storage` | `^9.0.0` | Token / secret storage |

### Networking & Storage
| Package | Version | Purpose |
|---|---|---|
| `dio` | `^5.4.0` | HTTP client |
| `pretty_dio_logger` | `^1.4.0` | Request/response logging |
| `hive_flutter` | `^1.1.0` | Local offline database |
| `shared_preferences` | `^2.2.0` | Lightweight key-value store |
| `connectivity_plus` | `^6.0.0` | Network connectivity detection |

### Config & Monitoring
| Package | Version | Purpose |
|---|---|---|
| `flutter_dotenv` | `^5.1.0` | `.env` file config |
| `sentry_flutter` | `^8.0.0` | Error monitoring |
| `logger` | `^2.0.0` | Structured logging |
| `package_info_plus` | `^8.0.0` | App version / build info |
| `path_provider` | `^2.1.0` | File system paths |
| `intl` | `any` | i18n formatting |
| `uuid` | `^4.4.0` | UUID generation |
| `collection` | `^1.18.0` | Collection utilities |
| `meta` | `^1.12.0` | Dart meta annotations |
| `http_parser` | `^4.0.0` | HTTP content-type parsing |

### Dev / Test
| Package | Version | Purpose |
|---|---|---|
| `very_good_analysis` | `^6.0.0` | Strict linting rules |
| `mocktail` | `^1.0.0` | Mock testing |
| `flutter_native_splash` | `^2.4.0` | Splash screen generation |

---

## Notes
- All tokens above are **fallback / default values**; at runtime they are overridden dynamically via the admin panel's `/v1/branding` API endpoint (Project-Decisions §21).
- Theme variants: `light`, `dark`, `milliy` (national accents), `highContrast`, `system`.
- Font family is fully dynamic; Inter is declared but commented out pending admin-panel font-token shipping.
