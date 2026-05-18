// Forgot-password — UI stub. The backend reset-email endpoint ships in a
// follow-up agent (Sprint FAZA 2 OAuth+recovery), so for now we accept the
// email address and surface a localized "Coming soon" message.

import "package:flutter/material.dart";
import "package:flutter_hooks/flutter_hooks.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/widgets/auth_form_fields.dart";

class ForgotPasswordPage extends HookConsumerWidget {
  const ForgotPasswordPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final formKey = useMemoized<GlobalKey<FormState>>(
      () => GlobalKey<FormState>(),
    );
    final emailController = useTextEditingController();

    return Scaffold(
      appBar: AppBar(
        leading: const BackButton(key: Key("forgot_password.back")),
        title: Text(l10n?.authForgotPasswordTitle ?? ""),
      ),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Form(
            key: formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Text(
                  l10n?.authForgotPasswordBody ?? "",
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 24),
                EmailField(controller: emailController, autofocus: true),
                const SizedBox(height: 24),
                FilledButton(
                  key: const Key("forgot_password.submit"),
                  onPressed: () {
                    if (!(formKey.currentState?.validate() ?? false)) return;
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(l10n?.authComingSoon ?? "Coming soon"),
                      ),
                    );
                  },
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    child: Text(l10n?.authForgotPasswordCta ?? ""),
                  ),
                ),
                const SizedBox(height: 8),
                TextButton(
                  key: const Key("forgot_password.back_to_sign_in"),
                  onPressed: () => context.pop(),
                  child: Text(l10n?.commonClose ?? ""),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
