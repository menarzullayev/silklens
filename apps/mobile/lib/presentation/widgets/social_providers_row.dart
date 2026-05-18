// Three-button row for the OAuth providers (Google / Apple / Telegram).
// The backend OAuth flow ships in a follow-up agent, so for now every
// button surfaces a localized "Coming soon" snackbar.

import "package:flutter/material.dart";
import "package:silklens/l10n/app_localizations.dart";

class SocialProvidersRow extends StatelessWidget {
  const SocialProvidersRow({super.key});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Column(
      children: <Widget>[
        Row(
          children: <Widget>[
            const Expanded(child: Divider()),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Text(
                l10n?.authProvidersDivider ?? "",
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ),
            const Expanded(child: Divider()),
          ],
        ),
        const SizedBox(height: 12),
        _ProviderButton(
          providerKey: const Key("auth.provider_google"),
          icon: Icons.g_mobiledata,
          label: l10n?.authProviderGoogle ?? "Google",
        ),
        const SizedBox(height: 8),
        _ProviderButton(
          providerKey: const Key("auth.provider_apple"),
          icon: Icons.apple,
          label: l10n?.authProviderApple ?? "Apple",
        ),
        const SizedBox(height: 8),
        _ProviderButton(
          providerKey: const Key("auth.provider_telegram"),
          icon: Icons.send,
          label: l10n?.authProviderTelegram ?? "Telegram",
        ),
      ],
    );
  }
}

class _ProviderButton extends StatelessWidget {
  const _ProviderButton({
    required this.providerKey,
    required this.icon,
    required this.label,
  });

  final Key providerKey;
  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return SizedBox(
      width: double.infinity,
      child: OutlinedButton.icon(
        key: providerKey,
        icon: Icon(icon),
        label: Text(label),
        onPressed: () {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(l10n?.authComingSoon ?? "Coming soon")),
          );
        },
      ),
    );
  }
}
