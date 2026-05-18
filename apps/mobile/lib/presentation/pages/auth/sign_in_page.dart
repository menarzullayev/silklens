// Sign-in page — email + password against POST /v1/auth/login.
//
// On success the [AuthNotifier] flips to authenticated and the router's
// redirect rule lifts the user into /home/discover.

import "package:flutter/material.dart";
import "package:flutter_hooks/flutter_hooks.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/auth_provider.dart";
import "package:silklens/presentation/router/app_router.dart";
import "package:silklens/presentation/widgets/auth_error_mapper.dart";
import "package:silklens/presentation/widgets/auth_form_fields.dart";
import "package:silklens/presentation/widgets/social_providers_row.dart";

class SignInPage extends HookConsumerWidget {
  const SignInPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final formKey = useMemoized<GlobalKey<FormState>>(
      () => GlobalKey<FormState>(),
    );
    final emailController = useTextEditingController();
    final passwordController = useTextEditingController();
    final isSubmitting = useState<bool>(false);
    final errorMessage = useState<String?>(null);

    Future<void> submit() async {
      if (isSubmitting.value) return;
      if (!(formKey.currentState?.validate() ?? false)) return;
      isSubmitting.value = true;
      errorMessage.value = null;
      final failure = await ref.read(authNotifierProvider.notifier).signIn(
            email: emailController.text.trim(),
            password: passwordController.text,
          );
      if (!context.mounted) return;
      isSubmitting.value = false;
      if (failure != null) {
        errorMessage.value = mapFailure(failure, l10n);
        return;
      }
      context.go(AppRoutes.homeDiscover);
    }

    return Scaffold(
      appBar: AppBar(
        leading: BackButton(
          key: const Key("sign_in.back"),
          onPressed: () {
            if (context.canPop()) {
              context.pop();
            } else {
              context.go(AppRoutes.onboarding);
            }
          },
        ),
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Form(
            key: formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: <Widget>[
                Text(
                  l10n?.authSignInTitle ?? "Sign in",
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  l10n?.authSignInSubtitle ?? "",
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 32),
                EmailField(controller: emailController, autofocus: true),
                const SizedBox(height: 12),
                PasswordField(
                  controller: passwordController,
                  requireStrength: false,
                ),
                Align(
                  alignment: Alignment.centerRight,
                  child: TextButton(
                    key: const Key("sign_in.forgot_link"),
                    onPressed: () => context.go(AppRoutes.authForgotPassword),
                    child: Text(l10n?.authForgotLink ?? ""),
                  ),
                ),
                if (errorMessage.value != null)
                  _ErrorBanner(message: errorMessage.value!),
                const SizedBox(height: 12),
                FilledButton(
                  key: const Key("sign_in.submit"),
                  onPressed: isSubmitting.value ? null : submit,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    child: isSubmitting.value
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text(l10n?.authSignInCta ?? ""),
                  ),
                ),
                const SizedBox(height: 16),
                const SocialProvidersRow(),
                const SizedBox(height: 24),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    Text(l10n?.authNoAccountQ ?? ""),
                    TextButton(
                      key: const Key("sign_in.go_to_sign_up"),
                      onPressed: () => context.go(AppRoutes.authSignUp),
                      child: Text(l10n?.authSignUpCta ?? ""),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _ErrorBanner extends StatelessWidget {
  const _ErrorBanner({required this.message});

  final String message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      key: const Key("auth.error_banner"),
      margin: const EdgeInsets.only(top: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: theme.colorScheme.errorContainer,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: <Widget>[
          Icon(Icons.error_outline, color: theme.colorScheme.onErrorContainer),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              message,
              style: TextStyle(color: theme.colorScheme.onErrorContainer),
            ),
          ),
        ],
      ),
    );
  }
}

