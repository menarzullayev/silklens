# SilkLens — Flutter Mobile

> The iOS + Android client for the SilkLens cultural-heritage platform.
> Skeleton ships at **FAZA 1 / Hafta 2**. Camera, vision, AR, maps and
> offline bundles land in FAZA 2+ per [`Roadmap.md`](../../Roadmap.md).

---

## Requirements

| Tool | Version |
|---|---|
| Flutter SDK | `>= 3.24.0` (stable channel) |
| Dart SDK    | `>= 3.5.0` (ships with Flutter) |
| Android SDK | API 34, build-tools 34.x, NDK per `flutter doctor` |
| Xcode       | 15+ with CocoaPods >= 1.13 |
| JDK         | 17 (Android Gradle Plugin 8.x requires JDK 17) |

Run `flutter doctor -v` and resolve every red item before continuing.

---

## First-time setup

```bash
cd apps/mobile

# 1. Pull dependencies.
flutter pub get

# 2. Copy the env template. The real .env is git-ignored.
cp assets/.env.example assets/.env

# 3. (Optional) If the native container drifts from your Flutter version,
#    regenerate it. WARNING: this rewrites android/ and ios/.
#    flutter create . --org com.silklens

# 4. Generate Freezed / json_serializable / Riverpod / Retrofit / Isar code.
dart run build_runner build --delete-conflicting-outputs

# 5. Generate localizations.
flutter gen-l10n
```

Step 4 produces:

- `*.freezed.dart` for every `@freezed` class
- `*.g.dart` for `@JsonSerializable` and `@RestApi` and Isar collections
- `*.g.dart` for `@riverpod` providers

Re-run it after any annotated-class change:

```bash
dart run build_runner watch --delete-conflicting-outputs   # continuous
# or
dart run build_runner build  --delete-conflicting-outputs  # one-shot
```

---

## Running

### Android emulator

```bash
flutter emulators                       # list available AVDs
flutter emulators --launch <avd_id>
flutter run -d emulator-5554
```

The default API base URL on Android emulator is **`http://10.0.2.2:8000`**
(host machine's localhost from inside the emulator). Override with
`API_BASE_URL_OVERRIDE` in `assets/.env`.

### iOS simulator

```bash
open -a Simulator                       # boot the simulator
flutter run -d "iPhone 15"
```

Default API base URL on iOS simulator: **`http://localhost:8000`**.

### Physical device

Override the base URL to your LAN IP (find it with `ipconfig` / `ifconfig`):

```env
# assets/.env
API_BASE_URL_OVERRIDE=http://192.168.1.42:8000
```

### Pointing at the local backend

The FastAPI service in `services/api/` listens on `:8000`:

```bash
# In repo root
make dev       # starts Postgres / Redis / MinIO / Elasticsearch / Redpanda
cd services/api && source .venv/bin/activate && make api-run
```

Verify with:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/version
```

---

## Project structure

```
apps/mobile/
├── lib/
│   ├── main.dart                       Boot orchestration (Sentry, env, Isar).
│   ├── app/                            Composition root (MaterialApp.router).
│   ├── core/                           Cross-cutting: env, error, logging, utils.
│   │   ├── env/                          AppEnvironment (.env parser)
│   │   ├── error/                        Failure / Exception hierarchies
│   │   ├── logging/                      AppLogger
│   │   ├── network/                      ApiEndpoints catalogue
│   │   ├── storage/                      SecureTokenStorage
│   │   └── utils/                        Result<S,F>, HybridLogicalClock
│   ├── domain/                         Pure-Dart business layer.
│   │   ├── heritage/                     entities / repositories (interfaces) / usecases
│   │   ├── identity/
│   │   ├── media/
│   │   └── social/
│   ├── data/                           Adapter layer.
│   │   ├── api/                          Dio + Retrofit client + DTOs + interceptors
│   │   ├── local/                        Isar schemas + DB wrapper
│   │   └── repositories/                 Domain interface implementations
│   ├── presentation/                   Flutter UI (replaceable per ADR-0003).
│   │   ├── pages/                        Splash · Onboarding · HomeShell · Camera · Map · Profile
│   │   ├── widgets/                      BrandedAppName · SilkLensLogo
│   │   ├── theme/                        Dynamic ThemeData + design tokens
│   │   ├── router/                       GoRouter map
│   │   └── providers/                    LocaleProvider (and more later)
│   └── l10n/                           4 ARB files + generated AppLocalizations
├── test/                               Unit + widget tests
├── integration_test/                   App-boot smoke test
├── android/                            Min Android container
├── ios/                                Min iOS container
└── assets/                             .env template + branding/ + onboarding/
```

The folder layout deliberately mirrors `services/api/src/` (per
[ADR-0003](../../docs/adr/0003-clean-architecture-layers.md)). Inner
layers never import outer ones:

- `domain/` imports nothing but `dart:core` + freezed annotations.
- `data/` imports `domain/` + adapter SDKs (Dio, Isar, secure_storage).
- `presentation/` imports `domain/` + Riverpod + Flutter.
- The composition root (`main.dart` + `app/app.dart`) imports everything.

---

## Testing

```bash
flutter test                            # unit + widget tests
flutter test integration_test           # integration smoke (requires a device/emulator)
flutter analyze                         # very_good_analysis + strict
```

Coverage:

```bash
flutter test --coverage
genhtml coverage/lcov.info -o coverage/html
```

---

## Architecture cheatsheet

- **State:** Riverpod (`hooks_riverpod` + `riverpod_annotation`). UI uses
  `ConsumerWidget` / `HookConsumerWidget`. Providers live next to their
  layer — never directly in widgets.
- **Navigation:** `go_router` 14, single `GoRouter` provider. ShellRoute
  hosts Map / Camera / Profile tabs (Project-Decisions §23, Shazam-style
  camera-centered navigation).
- **HTTP:** Dio + Retrofit. Three interceptors (auth, telemetry, error).
  Errors are normalized to `ApiException` / `NetworkException` at the
  adapter boundary, then translated to `Failure` values by repositories.
- **Offline:** Isar for L1 (always-cached metadata) and L2 (offline
  bundles) per [Master Architecture §8](../../docs/architecture/00-MASTER-ARCHITECTURE.md).
  Conflict resolution per CRDT type table in §8 is honoured by the HLC
  utility in `core/utils/hlc.dart`.
- **Branding:** Per [Project-Decisions §1](../../Project-Decisions.md)
  the user-visible app name is dynamic. Source of truth, in order:
  1. `/v1/tenant/branding` from admin panel (FAZA 1 Hafta 2).
  2. `AppLocalizations.appName` from the active ARB.
  3. The `APP_NAME` fallback in `.env`.
  Code MUST NOT hard-code the literal `"SilkLens"` in user-visible
  strings; always read from `AppLocalizations` or the branding store.
- **Theme:** Per [Project-Decisions §21](../../Project-Decisions.md)
  themes are dynamic. `ThemeTokens` (colors / typography) come from the
  admin panel; today they're hardcoded placeholders in
  `presentation/theme/theme_tokens.dart`.
- **Localization:** Four ARBs (uz / en / ru / zh). Adding a new language
  is a one-file change. NLLB-200 auto-translates the missing keys.

---

## Known follow-ups (FAZA 2+)

- Apple Sign-In needs an entitlement file (`Runner.entitlements`) and a
  capability in Xcode signing.
- Android Maps key required for FAZA 2 (Mapbox is the current first-pick;
  Google Maps as fallback). Plumbed through `.env`.
- Camera + AR plugins (`camera`, `arcore_flutter_plugin`, `arkit_plugin`)
  intentionally not added at FAZA 1 — they pin the iOS deployment target
  high. Add together with the Vision pipeline.
- Sentry release & dist tagging — wire to CI once GitHub Actions ships.
- Crashlytics is intentionally NOT used (Sentry covers it; one
  observability vendor is enough).
- `dart run build_runner` outputs are gitignored. First-clone-then-build
  ergonomics depend on contributors running step 4 above.

---

## Troubleshooting

- **`Generated.xcconfig must exist`** — run `flutter pub get` once first.
- **`isarDatabaseProvider must be overridden`** — you mounted
  `SilkLensApp` in a test without supplying the override. Use the pattern
  from `integration_test/app_boot_test.dart`.
- **Android build fails with `Unsupported class file major version`** —
  set JDK 17 as `JAVA_HOME`.
- **Emulator can't reach the API** — Android emulator uses `10.0.2.2`
  as the host loopback alias, not `localhost`. Don't override unless you
  also know the route.
