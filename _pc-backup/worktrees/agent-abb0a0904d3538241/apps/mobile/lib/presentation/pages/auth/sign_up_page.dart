import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/auth_provider.dart';

class SignUpPage extends ConsumerStatefulWidget {
  const SignUpPage({super.key});

  @override
  ConsumerState<SignUpPage> createState() => _SignUpPageState();
}

class _SignUpPageState extends ConsumerState<SignUpPage> {
  final _formKey = GlobalKey<FormState>();
  final _emailCtrl = TextEditingController();
  final _passCtrl = TextEditingController();
  final _confirmPassCtrl = TextEditingController();
  bool _loading = false;
  bool _obscurePass = true;
  bool _obscureConfirm = true;
  bool _tosAccepted = false;
  double _passwordStrength = 0;

  @override
  void initState() {
    super.initState();
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: Color(0xFF0D2337),
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );
    LocaleService.instance.loadFromPrefs().then((_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _emailCtrl.dispose();
    _passCtrl.dispose();
    _confirmPassCtrl.dispose();
    super.dispose();
  }

  double _calcStrength(String pwd) {
    if (pwd.isEmpty) return 0;
    if (pwd.length < 6) return 0.25;
    if (pwd.length < 10) return 0.5;
    final hasUpper = pwd.contains(RegExp('[A-Z]'));
    final hasDigit = pwd.contains(RegExp('[0-9]'));
    final hasSpecial = pwd.contains(RegExp(r'[!@#$%^&*]'));
    if (hasUpper && hasDigit && hasSpecial) return 1;
    if (hasUpper || hasDigit) return 0.75;
    return 0.5;
  }

  Future<void> _submit() async {
    if (!_tosAccepted) return;
    if (!(_formKey.currentState?.validate() ?? false)) return;
    setState(() => _loading = true);

    final success = await ref
        .read(authNotifierProvider.notifier)
        .register(_emailCtrl.text.trim(), _passCtrl.text);

    if (!mounted) return;
    setState(() => _loading = false);

    if (success) {
      final email = Uri.encodeComponent(_emailCtrl.text.trim());
      context.go('/auth/email-verify?email=$email');
    } else {
      final authState = ref.read(authNotifierProvider);
      if (authState is AuthError) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(authState.message),
            backgroundColor: const Color(0xFFE53935),
          ),
        );
      }
    }
  }

  String _s(String key) =>
      AppStrings.get(LocaleService.instance.locale, key);

  @override
  Widget build(BuildContext context) {
    final screenH = MediaQuery.sizeOf(context).height;

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Container(
        constraints: BoxConstraints(minHeight: screenH),
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0D2337), Color(0xFF1A3A5C), Color(0xFF0D2337)],
            stops: [0.0, 0.5, 1.0],
          ),
        ),
        child: SafeArea(
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 28),
            child: ConstrainedBox(
              constraints: BoxConstraints(minHeight: screenH * 0.9),
              child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const SizedBox(height: 16),
                    IconButton(
                      icon: const Icon(
                        Icons.arrow_back_ios_new,
                        color: Colors.white,
                        size: 20,
                      ),
                      onPressed: () => context.go('/onboarding'),
                      padding: EdgeInsets.zero,
                    ),
                    const SizedBox(height: 32),

                    // Header
                    Center(
                      child: Column(
                        children: [
                          Container(
                            width: 72,
                            height: 72,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: Colors.white.withValues(alpha: 0.18),
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.45),
                              ),
                            ),
                            child: const Icon(
                              Icons.explore_rounded,
                              size: 36,
                              color: Colors.white,
                            ),
                          ),
                          const SizedBox(height: 20),
                          Text(
                            _s('auth_signup_title'),
                            style: const TextStyle(
                              color: Colors.white,
                              fontSize: 28,
                              fontWeight: FontWeight.w800,
                            ),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            _s('auth_signup_sub'),
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.6),
                              fontSize: 15,
                            ),
                          ),
                        ],
                      ),
                    ),

                    const SizedBox(height: 48),

                    // Email
                    TextFormField(
                      controller: _emailCtrl,
                      keyboardType: TextInputType.emailAddress,
                      textInputAction: TextInputAction.next,
                      style: const TextStyle(color: Colors.white),
                      decoration: _inputDecoration(
                        _s('auth_email'),
                        Icons.email_outlined,
                      ),
                      validator: (v) {
                        if (v == null || v.isEmpty) {
                          return _s('err_email_required');
                        }
                        if (!v.contains('@')) {
                          return _s('err_email_invalid');
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Password
                    TextFormField(
                      controller: _passCtrl,
                      obscureText: _obscurePass,
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _submit(),
                      onChanged: (v) =>
                          setState(() => _passwordStrength = _calcStrength(v)),
                      style: const TextStyle(color: Colors.white),
                      decoration: _inputDecoration(
                        _s('auth_password_8'),
                        Icons.lock_outline,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscurePass
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                            color: Colors.white.withValues(alpha: 0.5),
                            size: 20,
                          ),
                          onPressed: () =>
                              setState(() => _obscurePass = !_obscurePass),
                        ),
                      ),
                      validator: (v) {
                        if (v == null || v.length < 8) {
                          return _s('err_password_8');
                        }
                        return null;
                      },
                    ),

                    const SizedBox(height: 8),

                    // Password strength bar
                    AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      height: 4,
                      child: Row(
                        children: List.generate(4, (i) {
                          final filled = _passwordStrength > i * 0.25;
                          final color = _passwordStrength < 0.5
                              ? const Color(0xFFFF6B6B)
                              : _passwordStrength < 0.75
                                  ? const Color(0xFFF5B041)
                                  : const Color(0xFFB78628);
                          return Expanded(
                            child: Container(
                              margin: EdgeInsets.only(right: i < 3 ? 3 : 0),
                              decoration: BoxDecoration(
                                color: filled
                                    ? color
                                    : Colors.white.withValues(alpha: 0.12),
                                borderRadius: BorderRadius.circular(2),
                              ),
                            ),
                          );
                        }),
                      ),
                    ),

                    const SizedBox(height: 4),

                    if (_passwordStrength > 0)
                      Text(
                        _passwordStrength < 0.5
                            ? _s('pwd_weak')
                            : _passwordStrength < 0.75
                                ? _s('pwd_medium')
                                : _s('pwd_strong'),
                        style: TextStyle(
                          color: _passwordStrength < 0.5
                              ? const Color(0xFFFF6B6B)
                              : const Color(0xFFB78628),
                          fontSize: 11,
                        ),
                      ),

                    const SizedBox(height: 16),

                    // Confirm password
                    TextFormField(
                      controller: _confirmPassCtrl,
                      obscureText: _obscureConfirm,
                      textInputAction: TextInputAction.done,
                      onFieldSubmitted: (_) => _submit(),
                      style: const TextStyle(color: Colors.white),
                      decoration: _inputDecoration(
                        _s('auth_confirm_password'),
                        Icons.lock_outline,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscureConfirm
                                ? Icons.visibility_outlined
                                : Icons.visibility_off_outlined,
                            color: Colors.white.withValues(alpha: 0.5),
                            size: 20,
                          ),
                          onPressed: () => setState(
                            () => _obscureConfirm = !_obscureConfirm,
                          ),
                        ),
                      ),
                      validator: (v) {
                        if (v == null || v.isEmpty) {
                          return _s('err_confirm_password_required');
                        }
                        if (v != _passCtrl.text) {
                          return _s('err_passwords_mismatch');
                        }
                        return null;
                      },
                    ),

                    const SizedBox(height: 32),

                    // ToS checkbox
                    Row(
                      children: [
                        Checkbox(
                          value: _tosAccepted,
                          onChanged: (v) =>
                              setState(() => _tosAccepted = v ?? false),
                          checkColor: const Color(0xFF1A3A5C),
                          fillColor: WidgetStateProperty.resolveWith(
                            (states) => states.contains(WidgetState.selected)
                                ? Colors.white
                                : Colors.white.withValues(alpha: 0.15),
                          ),
                          side: BorderSide(
                            color: Colors.white.withValues(alpha: 0.4),
                          ),
                        ),
                        Expanded(
                          child: Text(
                            _s('auth_tos_text'),
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.7),
                              fontSize: 13,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),

                    // Create Account button — gold gradient
                    GestureDetector(
                      onTap: _loading || !_tosAccepted ? null : _submit,
                      child: AnimatedOpacity(
                        opacity: (_loading || !_tosAccepted) ? 0.6 : 1.0,
                        duration: const Duration(milliseconds: 200),
                        child: Container(
                          width: double.infinity,
                          height: 54,
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                            ),
                            borderRadius: BorderRadius.circular(14),
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFFB78628)
                                    .withValues(alpha: 0.35),
                                blurRadius: 16,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: Center(
                            child: _loading
                                ? const SizedBox(
                                    width: 22,
                                    height: 22,
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                      valueColor: AlwaysStoppedAnimation(
                                        Color(0xFF1A1200),
                                      ),
                                    ),
                                  )
                                : Text(
                                    _s('auth_signup_btn'),
                                    style: const TextStyle(
                                      color: Color(0xFF1A1200),
                                      fontSize: 16,
                                      fontWeight: FontWeight.w700,
                                    ),
                                  ),
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 20),

                    // Sign In link
                    Center(
                      child: GestureDetector(
                        onTap: () => context.go('/auth/sign-in'),
                        child: RichText(
                          text: TextSpan(
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.65),
                              fontSize: 14,
                            ),
                            children: [
                              TextSpan(text: _s('auth_have_account')),
                              TextSpan(
                                text: _s('auth_signin_link'),
                                style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ),
                    ),

                    const SizedBox(height: 40),
                  ],
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }

  InputDecoration _inputDecoration(
    String hint,
    IconData icon, {
    Widget? suffixIcon,
  }) {
    return InputDecoration(
      hintText: hint,
      hintStyle: TextStyle(color: Colors.white.withValues(alpha: 0.4)),
      prefixIcon: Icon(
        icon,
        color: Colors.white.withValues(alpha: 0.5),
        size: 20,
      ),
      suffixIcon: suffixIcon,
      filled: true,
      fillColor: Colors.white.withValues(alpha: 0.1),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: Colors.white.withValues(alpha: 0.2)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Colors.white, width: 1.5),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFFF6B6B)),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: const BorderSide(color: Color(0xFFFF6B6B), width: 1.5),
      ),
      errorStyle: const TextStyle(color: Color(0xFFFF6B6B)),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
    );
  }
}
