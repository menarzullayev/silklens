// Shared form pieces for the auth screens — keeps validation rules
// consistent across sign-in / sign-up / forgot-password flows.

import 'package:flutter/material.dart';
import 'package:silklens/l10n/app_localizations.dart';

class EmailField extends StatelessWidget {
  const EmailField({
    required this.controller,
    this.enabled = true,
    this.autofocus = false,
    super.key,
  });

  final TextEditingController controller;
  final bool enabled;
  final bool autofocus;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return TextFormField(
      key: const Key('auth.email_field'),
      controller: controller,
      enabled: enabled,
      autofocus: autofocus,
      keyboardType: TextInputType.emailAddress,
      autocorrect: false,
      textInputAction: TextInputAction.next,
      decoration: InputDecoration(
        labelText: l10n.authEmailLabel ?? 'Email',
        border: const OutlineInputBorder(),
        prefixIcon: const Icon(Icons.email_outlined),
      ),
      validator: (String? value) => validateEmail(value, l10n),
    );
  }
}

class PasswordField extends StatefulWidget {
  const PasswordField({
    required this.controller,
    this.label,
    this.enabled = true,
    this.requireStrength = true,
    this.textInputAction = TextInputAction.done,
    super.key,
  });

  final TextEditingController controller;
  final String? label;
  final bool enabled;
  final bool requireStrength;
  final TextInputAction textInputAction;

  @override
  State<PasswordField> createState() => _PasswordFieldState();
}

class _PasswordFieldState extends State<PasswordField> {
  bool _obscure = true;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return TextFormField(
      key: const Key('auth.password_field'),
      controller: widget.controller,
      enabled: widget.enabled,
      obscureText: _obscure,
      autocorrect: false,
      enableSuggestions: false,
      textInputAction: widget.textInputAction,
      decoration: InputDecoration(
        labelText: widget.label ?? (l10n.authPasswordLabel ?? 'Password'),
        border: const OutlineInputBorder(),
        prefixIcon: const Icon(Icons.lock_outline),
        suffixIcon: IconButton(
          key: const Key('auth.password_toggle'),
          icon: Icon(_obscure ? Icons.visibility_off : Icons.visibility),
          onPressed: () => setState(() => _obscure = !_obscure),
        ),
      ),
      validator: (String? value) => widget.requireStrength
          ? validateStrongPassword(value, l10n)
          : validateRequired(value, l10n),
    );
  }
}

String? validateEmail(String? value, AppLocalizations? l10n) {
  final trimmed = value?.trim() ?? '';
  if (trimmed.isEmpty) return l10n?.authErrorRequired ?? 'Required';
  // Simple RFC-5322-lite check — good enough for client-side. Server still
  // validates with email_validator.
  final re = RegExp(r'^[\w.\-+]+@[\w.\-]+\.[A-Za-z]{2,}$');
  if (!re.hasMatch(trimmed)) {
    return l10n?.authErrorInvalidEmail ?? 'Invalid email';
  }
  return null;
}

String? validateRequired(String? value, AppLocalizations? l10n) {
  if (value == null || value.isEmpty) {
    return l10n?.authErrorRequired ?? 'Required';
  }
  return null;
}

String? validateStrongPassword(String? value, AppLocalizations? l10n) {
  if (value == null || value.isEmpty) {
    return l10n?.authErrorRequired ?? 'Required';
  }
  if (value.length < 12) {
    return l10n?.authErrorPasswordTooShort ?? 'Password too short';
  }
  final hasUpper = RegExp('[A-Z]').hasMatch(value);
  final hasLower = RegExp('[a-z]').hasMatch(value);
  final hasDigit = RegExp('[0-9]').hasMatch(value);
  if (!hasUpper || !hasLower || !hasDigit) {
    return l10n?.authErrorPasswordWeak ?? 'Password too weak';
  }
  return null;
}
