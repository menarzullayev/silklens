import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/locale_provider.dart";
import "package:silklens/presentation/theme/theme_provider.dart";

class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final locale = ref.watch(activeLocaleProvider);
    final variant = ref.watch(themeControllerProvider);

    return ListView(
      key: const Key("profile.list"),
      padding: const EdgeInsets.all(16),
      children: <Widget>[
        const SizedBox(height: 16),
        Text(
          l10n?.profileTitle ?? "Profile",
          style: theme.textTheme.headlineSmall,
        ),
        const SizedBox(height: 24),
        ListTile(
          leading: const Icon(Icons.language),
          title: Text(l10n?.profileLanguage ?? "Language"),
          subtitle: Text(locale.languageCode.toUpperCase()),
          trailing: PopupMenuButton<String>(
            onSelected: (String code) =>
                ref.read(activeLocaleProvider.notifier).setLanguageCode(code),
            itemBuilder: (BuildContext context) => const <PopupMenuEntry<String>>[
              PopupMenuItem<String>(value: "uz", child: Text("O‘zbek")),
              PopupMenuItem<String>(value: "en", child: Text("English")),
              PopupMenuItem<String>(value: "ru", child: Text("Русский")),
              PopupMenuItem<String>(value: "zh", child: Text("中文")),
            ],
          ),
        ),
        ListTile(
          leading: const Icon(Icons.palette_outlined),
          title: Text(l10n?.profileTheme ?? "Theme"),
          subtitle: Text(variant.name),
          trailing: PopupMenuButton<ThemeVariant>(
            onSelected: (ThemeVariant v) =>
                ref.read(themeControllerProvider.notifier).setVariant(v),
            itemBuilder: (BuildContext context) => ThemeVariant.values
                .map(
                  (ThemeVariant v) =>
                      PopupMenuItem<ThemeVariant>(value: v, child: Text(v.name)),
                )
                .toList(),
          ),
        ),
      ],
    );
  }
}
