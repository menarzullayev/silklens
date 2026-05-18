// Sign-up page — email + password + (optional) display name against
// POST /v1/auth/register. The backend auto-logs-in via the 201 response,
// so on success we land straight in /home/discover.

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

class SignUpPage extends HookConsumerWidget {
  const SignUpPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final theme = Theme.of(context);
    final formKey = useMemoized<GlobalKey<FormState>>(
      () => GlobalKey<FormState>(),
    );
    final displayNameController = useTextEditingController();
    final emailController = useTextEditingController();
    final passwordController = useTextEditingController();
    final confirmController = useTextEditingController();
    final isSubmitting = useState<bool>(false);
    final errorMessage = useState<String?>(null);

    String? confirmValidator(String? value) {
      if (value == null || value.isEmpty) {
        return l10n?.authErrorRequired;
      }
      if (value != passwordController.text) {
        return l10n?.authErrorPasswordsDontMatch;
      }
      return null;
    }

    Future<void> submit() async {
      if (isSubmitting.value) return;
      if (!(formKey.currentState?.validate() ?? false)) return;
      isSubmitting.value = true;
      errorMessage.value = null;
      final locale = Localizations.localeOf(context).languageCode;
      final failure = await ref.read(authNotifierProvider.notifier).signUp(
            email: emailController.text.trim(),
            password: passwordController.text,
            displayName: displayNameController.text.trim().isEmpty
                ? null
                : displayNameController.text.trim(),
            preferredLocale: locale,
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
          key: const Key("sign_up.back"),
          onPressed: () {
            if (context.canPop()) {
              context.pop();
            } else {
              context.go(AppRoutes.authSignIn);
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
                  l10n?.authSignUpTitle ?? "",
                  style: theme.textTheme.headlineMedium?.copyWith(
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  l10n?.authSignUpSubtitle ?? "",
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 32),
                TextFormField(
                  key: const Key("sign_up.display_name"),
                  controller: displayNameController,
                  textInputAction: TextInputAction.next,
                  decoration: InputDecoration(
                    labelText: l10n?.authDisplayNameLabel ?? "Display name",
                    border: const OutlineInputBorder(),
                    prefixIcon: const Icon(Icons.person_outline),
                  ),
                ),
                const SizedBox(height: 12),
                EmailField(controller: emailController),
                const SizedBox(height: 12),
                PasswordField(controller: passwordController),
                const SizedBox(height: 12),
                TextFormField(
                  key: const Key("sign_up.password_confirm"),
                  controller: confirmController,
                  obscureText: true,
                  autocorrect: false,
                  enableSuggestions: false,
                  decoration: InputDecoration(
                    labelText: l10n?.authPasswordConfirmLabel ?? "Confirm",
                    border: const OutlineInputBorder(),
                    prefixIcon: const Icon(Icons.lock_outline),
                  ),
                  validator: confirmValidator,
                ),
                if (errorMessage.value != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 12),
                    child: Container(
                      key: const Key("auth.error_banner"),
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: theme.colorScheme.errorContainer,
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: Row(
                        children: <Widget>[
                          Icon(Icons.error_outline,
                              color: theme.colorScheme.onErrorContainer),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              errorMessage.value!,
                              style: TextStyle(
                                color: theme.colorScheme.onErrorContainer,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 24),
                FilledButton(
                  key: const Key("sign_up.submit"),
                  onPressed: isSubmitting.value ? null : submit,
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    child: isSubmitting.value
                        ? const SizedBox(
                            width: 20,
                            height: 20,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : Text(l10n?.authSignUpCta ?? ""),
                  ),
                ),
                const SizedBox(height: 16),
                const SocialProvidersRow(),
                const SizedBox(height: 24),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: <Widget>[
                    Text(l10n?.authHaveAccountQ ?? ""),
                    TextButton(
                      key: const Key("sign_up.go_to_sign_in"),
                      onPressed: () => context.go(AppRoutes.authSignIn),
                      child: Text(l10n?.authSignInCta ?? ""),
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
