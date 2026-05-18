// Heritage detail page — opened from a list / search / saved card.
//
// Hero image + localized name + summary_md + period chip + action row:
//   [Save] [Share] [AI guide].
//
// The "Save" action toggles the local Isar pin (offline-first).
// The "AI guide" button is intentionally disabled with a localized
// "Coming in v2 build" tooltip — AR + voice-over land in FAZA 3.

import "package:flutter/material.dart";
import "package:flutter_markdown/flutter_markdown.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/heritage_detail_provider.dart";

class HeritageDetailPage extends ConsumerWidget {
  const HeritageDetailPage({required this.pubId, super.key});

  final String pubId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final async = ref.watch(heritageDetailProvider(pubId));

    return Scaffold(
      body: async.when(
        loading: () => const Center(
          key: Key("heritage_detail.loading"),
          child: CircularProgressIndicator(),
        ),
        error: (Object error, StackTrace _) => _ErrorView(
          message: error.toString(),
          onRetry: () =>
              ref.read(heritageDetailProvider(pubId).notifier).refresh(),
        ),
        data: (Heritage heritage) => _DetailBody(
          heritage: heritage,
          l10n: l10n,
        ),
      ),
    );
  }
}

class _DetailBody extends ConsumerWidget {
  const _DetailBody({required this.heritage, required this.l10n});

  final Heritage heritage;
  final AppLocalizations? l10n;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final locale = Localizations.localeOf(context).languageCode;
    final name = heritage.localizedName(locale);
    final summary = heritage.localizedSummary(locale);
    final description = heritage.localizedDescription(locale);

    return CustomScrollView(
      key: const Key("heritage_detail.scroll"),
      slivers: <Widget>[
        SliverAppBar(
          expandedHeight: 280,
          pinned: true,
          flexibleSpace: FlexibleSpaceBar(
            title: Text(
              name.isEmpty ? heritage.pubId : name,
              style: const TextStyle(
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
            background: heritage.heroMediaUrl != null &&
                    heritage.heroMediaUrl!.isNotEmpty
                ? Hero(
                    tag: "heritage-hero-${heritage.pubId}",
                    child: Image.network(
                      heritage.heroMediaUrl!,
                      fit: BoxFit.cover,
                      errorBuilder:
                          (BuildContext _, Object __, StackTrace? ___) =>
                              _HeroPlaceholder(theme: theme),
                    ),
                  )
                : _HeroPlaceholder(theme: theme),
          ),
        ),
        SliverPadding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 32),
          sliver: SliverList(
            delegate: SliverChildListDelegate(<Widget>[
              _ChipsRow(heritage: heritage, l10n: l10n),
              const SizedBox(height: 16),
              _ActionsRow(heritage: heritage),
              const SizedBox(height: 24),
              if (summary.isNotEmpty) ...<Widget>[
                Text(
                  l10n?.heritageDetailSummary ?? "",
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                MarkdownBody(
                  key: const Key("heritage_detail.summary"),
                  data: summary,
                ),
                const SizedBox(height: 24),
              ],
              if (description.isNotEmpty) ...<Widget>[
                Text(
                  l10n?.heritageDetailAbout ?? "",
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                MarkdownBody(
                  key: const Key("heritage_detail.description"),
                  data: description,
                ),
                const SizedBox(height: 24),
              ],
              if (heritage.hasGeolocation)
                _LocationBlock(heritage: heritage, l10n: l10n),
            ]),
          ),
        ),
      ],
    );
  }
}

class _ChipsRow extends StatelessWidget {
  const _ChipsRow({required this.heritage, required this.l10n});

  final Heritage heritage;
  final AppLocalizations? l10n;

  @override
  Widget build(BuildContext context) {
    final period = heritage.periodLabel;
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: <Widget>[
        if (period != null)
          Chip(
            avatar: const Icon(Icons.history, size: 18),
            label: Text("${l10n?.heritageDetailPeriod}: $period"),
          ),
        if (heritage.countryCode != null)
          Chip(
            avatar: const Icon(Icons.public, size: 18),
            label: Text(
              "${l10n?.heritageDetailCountry}: ${heritage.countryCode}",
            ),
          ),
        if (heritage.isUnescoListed)
          Chip(
            avatar: const Icon(Icons.star, size: 18),
            label: Text(
              "${l10n?.heritageDetailUnesco} "
              "(${heritage.unescoInscriptionYear})",
            ),
          ),
      ],
    );
  }
}

class _ActionsRow extends ConsumerWidget {
  const _ActionsRow({required this.heritage});

  final Heritage heritage;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final savedAsync = ref.watch(heritageSavedProvider(heritage.pubId));
    final isSaved = savedAsync.maybeWhen(
      data: (bool v) => v,
      orElse: () => false,
    );

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceEvenly,
      children: <Widget>[
        _ActionButton(
          buttonKey: const Key("heritage_detail.save"),
          icon: isSaved ? Icons.bookmark : Icons.bookmark_outline,
          label: isSaved
              ? (l10n?.heritageDetailUnsave ?? "")
              : (l10n?.heritageDetailSave ?? ""),
          onPressed: () => ref
              .read(heritageSavedProvider(heritage.pubId).notifier)
              .toggle(heritage),
        ),
        _ActionButton(
          buttonKey: const Key("heritage_detail.share"),
          icon: Icons.ios_share,
          label: l10n?.heritageDetailShare ?? "",
          onPressed: () {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(content: Text(l10n?.authComingSoon ?? "Coming soon")),
            );
          },
        ),
        Tooltip(
          message: l10n?.heritageDetailAiGuideTooltip ?? "",
          child: _ActionButton(
            buttonKey: const Key("heritage_detail.ai_guide"),
            icon: Icons.auto_awesome,
            label: l10n?.heritageDetailAiGuide ?? "",
            onPressed: null,
          ),
        ),
      ],
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.buttonKey,
    required this.icon,
    required this.label,
    required this.onPressed,
  });

  final Key buttonKey;
  final IconData icon;
  final String label;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final disabledColor = theme.colorScheme.onSurface.withValues(alpha: 0.38);
    final color = onPressed == null ? disabledColor : theme.colorScheme.primary;
    return InkWell(
      key: buttonKey,
      onTap: onPressed,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(icon, color: color),
            const SizedBox(height: 4),
            Text(label, style: theme.textTheme.bodySmall?.copyWith(color: color)),
          ],
        ),
      ),
    );
  }
}

class _LocationBlock extends StatelessWidget {
  const _LocationBlock({required this.heritage, required this.l10n});

  final Heritage heritage;
  final AppLocalizations? l10n;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      key: const Key("heritage_detail.location"),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.place, color: theme.colorScheme.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: <Widget>[
                Text(
                  l10n?.heritageDetailLocation ?? "Location",
                  style: theme.textTheme.titleSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                Text(
                  "${heritage.latitude?.toStringAsFixed(4)}, "
                  "${heritage.longitude?.toStringAsFixed(4)}",
                  style: theme.textTheme.bodyMedium,
                ),
              ],
            ),
          ),
          TextButton.icon(
            key: const Key("heritage_detail.open_in_map"),
            icon: const Icon(Icons.map),
            label: Text(l10n?.heritageDetailOpenInMap ?? ""),
            onPressed: () {
              context.go("/home/map?lat=${heritage.latitude}&lng=${heritage.longitude}");
            },
          ),
        ],
      ),
    );
  }
}

class _HeroPlaceholder extends StatelessWidget {
  const _HeroPlaceholder({required this.theme});

  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    return ColoredBox(
      color: theme.colorScheme.surfaceContainerHighest,
      child: Center(
        child: Icon(
          Icons.account_balance,
          size: 96,
          color: theme.colorScheme.onSurfaceVariant,
        ),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  const _ErrorView({required this.message, required this.onRetry});

  final String message;
  final Future<void> Function() onRetry;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Center(
      key: const Key("heritage_detail.error"),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            const Icon(Icons.error_outline, size: 64),
            const SizedBox(height: 12),
            Text(message, textAlign: TextAlign.center),
            const SizedBox(height: 12),
            FilledButton.tonal(
              key: const Key("heritage_detail.retry"),
              onPressed: onRetry,
              child: Text(l10n?.commonRetry ?? "Retry"),
            ),
          ],
        ),
      ),
    );
  }
}
