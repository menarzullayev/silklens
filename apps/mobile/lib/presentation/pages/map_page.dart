import "package:flutter/material.dart";
import "package:silklens/l10n/app_localizations.dart";

class MapPage extends StatelessWidget {
  const MapPage({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      key: const Key("map.placeholder"),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: <Widget>[
            Icon(Icons.map, size: 96, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 16),
            Text(
              l10n?.mapPlaceholderTitle ?? "Map",
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Text(
              l10n?.mapPlaceholderBody ??
                  "Mapbox / OSM integration lands in FAZA 2 — Hafta 3.",
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.bodyMedium,
            ),
          ],
        ),
      ),
    );
  }
}
