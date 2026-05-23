# SilkLens UI Textures

Place background texture and pattern assets in this directory.

## Planned files

| Filename                | Purpose                                      | Format |
|-------------------------|----------------------------------------------|--------|
| islamic_geometry.png    | Islamic geometric pattern overlay (low-opacity) | PNG  |
| silk_pattern.svg        | Silk textile pattern for cards / headers     | SVG    |

## Design notes

- Textures are used at low opacity (5–15%) over the dark gradient backgrounds.
- SVG preferred for vector patterns (scales to any device DPI without bloat).
- PNG textures should be tiled (seamless repeat) and compressed < 200 KB.

## Current status (SILK-0143)

Art direction not yet started. All glass-card and background widgets in
`lib/presentation/widgets/glass/` currently render pure LinearGradient backgrounds
defined in `SilkDesignTokens`. Texture overlays are the next design-system
iteration planned for FAZA 7 visual polish.

## Declaring in pubspec.yaml

The `assets/textures/` directory is NOT yet declared in pubspec.yaml.
Add it before using any asset from this directory:

```yaml
flutter:
  assets:
    - assets/textures/
```
