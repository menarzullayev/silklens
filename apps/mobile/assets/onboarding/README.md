# SilkLens Onboarding Assets

Place onboarding slide images in this directory.

## Required files

| Filename      | Subject                          | Recommended size |
|---------------|----------------------------------|------------------|
| slide_1.png   | Registon, Samarkand              | 1080 x 1920 px   |
| slide_2.png   | Poi Kalyan, Bukhara              | 1080 x 1920 px   |
| slide_3.png   | Itchan Kala, Khiva               | 1080 x 1920 px   |

## Format guidelines

- PNG with transparency preferred (so the dark-glass overlay blends correctly).
- Compress to < 500 KB per image using `pngquant` or similar.
- Avoid text in the image — all copy comes from `AppStrings` / `AppLocalizations`.

## Current status (SILK-0143)

Design not yet commissioned. `OnboardingPage` renders gradient-colour placeholder
containers until these assets are placed here. No code change is required once
the images are dropped in — Flutter's `AssetImage('assets/onboarding/slide_N.png')`
calls are already present in the implementation.

## Declaring in pubspec.yaml

The `assets/onboarding/` directory is already declared:

```yaml
flutter:
  assets:
    - assets/onboarding/
```

Individual files do not need separate entries when the whole directory is listed.
