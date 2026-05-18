// Camera page — FAZA 2 deliverable. Today it's a placeholder so the
// router and home shell can be exercised end-to-end.

import "package:flutter/material.dart";
import "package:silklens/l10n/app_localizations.dart";

class CameraPage extends StatelessWidget {
  const CameraPage({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      key: const Key("camera.placeholder"),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Icon(
              Icons.camera_alt,
              size: 96,
              color: Theme.of(context).colorScheme.primary,
            ),
            const SizedBox(height: 16),
            Text(
              l10n?.cameraPlaceholderTitle ?? "Camera",
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              l10n?.cameraPlaceholderBody ??
                  "Vision pipeline lands in FAZA 2 — Hafta 3.",
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}
