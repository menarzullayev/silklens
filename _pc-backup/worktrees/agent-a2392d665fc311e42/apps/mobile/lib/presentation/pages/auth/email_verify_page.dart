import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/l10n/app_localizations.dart';
import 'package:silklens/presentation/providers/auth_provider.dart';

class EmailVerifyPage extends ConsumerStatefulWidget {
  const EmailVerifyPage({required this.email, super.key});
  final String email;

  @override
  ConsumerState<EmailVerifyPage> createState() => _EmailVerifyPageState();
}

class _EmailVerifyPageState extends ConsumerState<EmailVerifyPage> {
  final List<TextEditingController> _ctrls = List.generate(6, (_) => TextEditingController());
  final List<FocusNode> _nodes = List.generate(6, (_) => FocusNode());
  bool _loading = false;
  bool _resending = false;
  String? _errorMsg;

  int _countdown = 59;
  Timer? _timer;

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
    _startCountdown();
  }

  void _startCountdown() {
    _timer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (_countdown == 0) {
        t.cancel();
        return;
      }
      if (mounted) setState(() => _countdown--);
    });
  }

  @override
  void dispose() {
    _timer?.cancel();
    for (final c in _ctrls) {
      c.dispose();
    }
    for (final n in _nodes) {
      n.dispose();
    }
    super.dispose();
  }

  String get _code => _ctrls.map((c) => c.text).join();

  Future<void> _verify() async {
    if (_code.length < 6) return;
    setState(() {
      _loading = true;
      _errorMsg = null;
    });

    final l10n = AppLocalizations.of(context);
    final ok = await ref.read(authNotifierProvider.notifier).verifyEmail(
          email: widget.email,
          code: _code,
        );

    if (!mounted) return;
    setState(() => _loading = false);

    if (ok) {
      context.go('/home');
    } else {
      setState(() => _errorMsg = l10n.emailVerifyInvalidCode);
      for (final c in _ctrls) {
        c.clear();
      }
      _nodes[0].requestFocus();
    }
  }

  Future<void> _resend() async {
    setState(() {
      _resending = true;
      _errorMsg = null;
    });

    final l10n = AppLocalizations.of(context);
    final ok = await ref.read(authNotifierProvider.notifier).resendVerification(
          email: widget.email,
        );

    if (!mounted) return;
    setState(() {
      _resending = false;
      if (ok) {
        _countdown = 59;
        _startCountdown();
      } else {
        _errorMsg = l10n.emailVerifyResendError;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final screenH = MediaQuery.sizeOf(context).height;
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Stack(
        children: [
          Container(
            constraints: BoxConstraints(minHeight: screenH),
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color(0xFF0D2337),
                  Color(0xFF1A3A5C),
                  Color(0xFF0D2337),
                ],
                stops: [0.0, 0.5, 1.0],
              ),
            ),
          ),
          Container(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: const Alignment(-0.4, -0.4),
                radius: 1.3,
                colors: [
                  const Color(0xFF1F3A93).withValues(alpha: 0.6),
                  Colors.transparent,
                ],
              ),
            ),
          ),
          Container(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: const Alignment(0.7, 0.2),
                radius: 1,
                colors: [
                  const Color(0xFFC2501F).withValues(alpha: 0.4),
                  Colors.transparent,
                ],
              ),
            ),
          ),
          SafeArea(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 28),
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
                    onPressed: () => context.pop(),
                    padding: EdgeInsets.zero,
                  ),
                  const SizedBox(height: 32),
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
                            Icons.mark_email_read_outlined,
                            size: 36,
                            color: Colors.white,
                          ),
                        ),
                        const SizedBox(height: 20),
                        Text(
                          l10n.emailVerifyTitle,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 26,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          widget.email,
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.7),
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          l10n.emailVerifyCodeSentTo,
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.5),
                            fontSize: 14,
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 48),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: List.generate(
                      6,
                      (i) => _OtpBox(
                        controller: _ctrls[i],
                        focusNode: _nodes[i],
                        filled: _ctrls[i].text.isNotEmpty,
                        hasError: _errorMsg != null,
                        onChanged: (v) {
                          if (v.isNotEmpty && i < 5) {
                            _nodes[i + 1].requestFocus();
                          }
                          if (v.isEmpty && i > 0) {
                            _nodes[i - 1].requestFocus();
                          }
                          setState(() {});
                          if (_code.length == 6) _verify();
                        },
                      ),
                    ),
                  ),
                  if (_errorMsg != null) ...[
                    const SizedBox(height: 10),
                    Center(
                      child: Text(
                        _errorMsg!,
                        style: const TextStyle(
                          color: Color(0xFFFF6B6B),
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ],
                  const SizedBox(height: 40),
                  GestureDetector(
                    onTap: (_loading || _code.length < 6) ? null : _verify,
                    child: AnimatedOpacity(
                      opacity: (_loading || _code.length < 6) ? 0.5 : 1.0,
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
                              color: const Color(0xFFB78628).withValues(alpha: 0.35),
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
                                  l10n.emailVerifyConfirm,
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
                  Center(
                    child: GestureDetector(
                      onTap: _countdown == 0 && !_resending ? _resend : null,
                      child: Text(
                        _resending
                            ? l10n.emailVerifyResending
                            : _countdown > 0
                                ? l10n.emailVerifyResendCountdown(_countdown)
                                : l10n.emailVerifyResendNow,
                        style: TextStyle(
                          color: (_countdown > 0 || _resending)
                              ? Colors.white.withValues(alpha: 0.35)
                              : const Color(0xFFB78628),
                          fontSize: 14,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _OtpBox extends StatelessWidget {
  const _OtpBox({
    required this.controller,
    required this.focusNode,
    required this.onChanged,
    this.filled = false,
    this.hasError = false,
  });

  final TextEditingController controller;
  final FocusNode focusNode;
  final ValueChanged<String> onChanged;
  final bool filled;
  final bool hasError;

  @override
  Widget build(BuildContext context) {
    final borderColor = hasError
        ? const Color(0xFFFF6B6B)
        : filled
            ? const Color(0xFFB78628).withValues(alpha: 0.6)
            : Colors.white.withValues(alpha: 0.25);

    return SizedBox(
      width: 44,
      height: 54,
      child: TextField(
        controller: controller,
        focusNode: focusNode,
        maxLength: 1,
        keyboardType: TextInputType.number,
        textAlign: TextAlign.center,
        style: TextStyle(
          color: hasError
              ? const Color(0xFFFF6B6B)
              : filled
                  ? const Color(0xFFB78628)
                  : Colors.white,
          fontSize: 22,
          fontWeight: FontWeight.w700,
        ),
        inputFormatters: [FilteringTextInputFormatter.digitsOnly],
        decoration: InputDecoration(
          counterText: '',
          filled: true,
          fillColor: hasError
              ? const Color(0xFFFF6B6B).withValues(alpha: 0.1)
              : filled
                  ? const Color(0xFFB78628).withValues(alpha: 0.15)
                  : Colors.white.withValues(alpha: 0.1),
          enabledBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide(
              color: borderColor,
              width: filled || hasError ? 1.5 : 1,
            ),
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide(
              color: hasError ? const Color(0xFFFF6B6B) : const Color(0xFFB78628),
              width: 2,
            ),
          ),
        ),
        onChanged: onChanged,
      ),
    );
  }
}
