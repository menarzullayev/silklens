import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/auth_provider.dart';

class SplashPage extends ConsumerStatefulWidget {
  const SplashPage({super.key});

  @override
  ConsumerState<SplashPage> createState() => _SplashPageState();
}

class _SplashPageState extends ConsumerState<SplashPage>
    with SingleTickerProviderStateMixin {
  late AnimationController _controller;
  late Animation<double> _fadeAnimation;
  late Animation<double> _scaleAnimation;
  late Animation<double> _taglineAnimation;

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

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    );

    _fadeAnimation = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0, 0.55, curve: Curves.easeIn),
    );

    _scaleAnimation = Tween<double>(begin: 0.72, end: 1).animate(
      CurvedAnimation(
        parent: _controller,
        curve: const Interval(0, 0.55, curve: Curves.easeOutBack),
      ),
    );

    _taglineAnimation = CurvedAnimation(
      parent: _controller,
      curve: const Interval(0.5, 1, curve: Curves.easeIn),
    );

    _controller.forward();
    _initAndNavigate();
  }

  Future<void> _initAndNavigate() async {
    final (hasLocale, _, authState) = await (
      _loadPrefs(),
      Future<void>.delayed(const Duration(milliseconds: 1800)),
      _waitForAuth(),
    ).wait;

    if (!mounted) return;

    if (authState is AuthAuthenticated) {
      context.go('/home');
    } else {
      context.go(hasLocale ? '/onboarding' : '/language');
    }
  }

  /// Waits until AuthNotifier._init() finishes (state leaves AuthInitial).
  /// Returns immediately if already resolved.
  Future<AuthState> _waitForAuth() async {
    final current = ref.read(authProvider);
    if (current is! AuthInitial) return current;

    final completer = Completer<AuthState>();
    final sub = ref.listenManual(
      authProvider,
      (_, next) {
        if (next is! AuthInitial && !completer.isCompleted) {
          completer.complete(next);
        }
      },
      fireImmediately: false,
    );
    final result = await completer.future;
    sub.close();
    return result;
  }

  Future<bool> _loadPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    await LocaleService.instance.loadFromPrefs();
    return prefs.containsKey('app_locale');
  }

  @override
  void dispose() {
    SystemChrome.setSystemUIOverlayStyle(SystemUiOverlayStyle.dark);
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Stack(
        children: [
          // Aurora background layer 1 — blue radial
          // (placeholder for AuroraBackground widget)
          Container(
            decoration: const BoxDecoration(
              gradient: RadialGradient(
                center: Alignment(-0.3, -0.3),
                radius: 1.5,
                colors: [Color(0xFF1F3A93), Color(0xFF0D2337)],
              ),
            ),
          ),
          // Aurora background layer 2 — warm amber accent
          Container(
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: const Alignment(0.6, 0.3),
                radius: 1.2,
                colors: [
                  const Color(0xFFC2501F).withValues(alpha: 0.5),
                  Colors.transparent,
                ],
              ),
            ),
          ),
          // Content (FadeTransition + ScaleTransition preserved)
          Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                FadeTransition(
                  opacity: _fadeAnimation,
                  child: ScaleTransition(
                    scale: _scaleAnimation,
                    child: Column(
                      children: [
                        // Logo with glow rings
                        Stack(
                          alignment: Alignment.center,
                          children: [
                            // Outer glow ring
                            Container(
                              width: 148,
                              height: 148,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: const Color(0x20B78628),
                                ),
                              ),
                            ),
                            // Middle ring
                            Container(
                              width: 132,
                              height: 132,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                border: Border.all(
                                  color: const Color(0x30B78628),
                                ),
                              ),
                            ),
                            // Main circle
                            Container(
                              width: 116,
                              height: 116,
                              decoration: BoxDecoration(
                                shape: BoxShape.circle,
                                color: Colors.white.withValues(alpha: 0.12),
                                border: Border.all(
                                  color: Colors.white.withValues(alpha: 0.35),
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(0xFFB78628)
                                        .withValues(alpha: 0.2),
                                    blurRadius: 24,
                                  ),
                                ],
                              ),
                              child: const Icon(
                                Icons.explore_rounded,
                                size: 58,
                                color: Colors.white,
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 36),
                        // App name — gold color
                        // (GoldShimmerText widget will replace later)
                        const Text(
                          'SilkLens',
                          style: TextStyle(
                            color: Color(0xFFE5C97A),
                            fontSize: 46,
                            fontWeight: FontWeight.w800,
                            letterSpacing: 4,
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                FadeTransition(
                  opacity: _taglineAnimation,
                  child: Text(
                    'Cultural Heritage Explorer',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.65),
                      fontSize: 15,
                      letterSpacing: 2,
                      fontWeight: FontWeight.w400,
                    ),
                  ),
                ),
                const SizedBox(height: 88),
                FadeTransition(
                  opacity: _taglineAnimation,
                  child: SizedBox(
                    width: 28,
                    height: 28,
                    child: CircularProgressIndicator(
                      strokeWidth: 1.8,
                      valueColor: AlwaysStoppedAnimation<Color>(
                        Colors.white.withValues(alpha: 0.5),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
