// Card widget used by the discover list and the search results page.
// Hero photo + localized name + period chip + country code.

import 'package:flutter/material.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';
import 'package:silklens/l10n/app_localizations.dart';

class HeritageCard extends StatelessWidget {
  const HeritageCard({
    required this.heritage,
    required this.onTap,
    super.key,
  });

  final Heritage heritage;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final locale = Localizations.localeOf(context).languageCode;
    final l10n = AppLocalizations.of(context);
    final name = heritage.localizedName(locale);
    final periodLabel = heritage.periodLabel;
    final hero = heritage.heroMediaUrl;

    return Card(
      key: Key('heritage_card.${heritage.pubId}'),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            AspectRatio(
              aspectRatio: 16 / 9,
              child: hero != null && hero.isNotEmpty
                  ? Hero(
                      tag: 'heritage-hero-${heritage.pubId}',
                      child: Image.network(
                        hero,
                        fit: BoxFit.cover,
                        errorBuilder: (BuildContext _, Object __,
                                StackTrace? ___,) =>
                            _PlaceholderImage(theme: theme),
                      ),
                    )
                  : _PlaceholderImage(theme: theme),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(12, 12, 12, 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: <Widget>[
                  Text(
                    name.isEmpty ? heritage.pubId : name,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                    maxLines: 2,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: <Widget>[
                      Chip(
                        visualDensity: VisualDensity.compact,
                        padding: EdgeInsets.zero,
                        label: Text(periodLabel),
                        avatar: const Icon(Icons.history, size: 16),
                      ),
                      if (heritage.countryCode != null)
                        Chip(
                          visualDensity: VisualDensity.compact,
                          padding: EdgeInsets.zero,
                          label: Text(heritage.countryCode!),
                          avatar: const Icon(Icons.public, size: 16),
                        ),
                      if (heritage.isUnescoListed)
                        Chip(
                          visualDensity: VisualDensity.compact,
                          padding: EdgeInsets.zero,
                          label: Text(
                            l10n.heritageDetailUnesco ?? 'UNESCO',
                          ),
                          avatar: const Icon(Icons.star, size: 16),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PlaceholderImage extends StatelessWidget {
  const _PlaceholderImage({required this.theme});

  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: theme.colorScheme.surfaceContainerHighest,
      child: Center(
        child: Icon(
          Icons.account_balance,
          size: 56,
          color: theme.colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }
}
