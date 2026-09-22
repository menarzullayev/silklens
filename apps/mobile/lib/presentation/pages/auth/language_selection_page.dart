import 'dart:ui';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:silklens/core/l10n/locale_service.dart';

class LanguageSelectionPage extends StatefulWidget {
  const LanguageSelectionPage({super.key});

  @override
  State<LanguageSelectionPage> createState() => _LanguageSelectionPageState();
}

class _LanguageSelectionPageState extends State<LanguageSelectionPage>
    with SingleTickerProviderStateMixin {
  static const _prefKey = 'app_locale';

  static const _languages = [
    _Lang(
      code: 'uz',
      flag: '🇺🇿',
      name: "O'zbek",
      nativeName: "O'zbek tili",
      selectLabel: 'Tilni tanlang',
      confirmLabel: 'Davom etish',
    ),
    _Lang(
      code: 'en',
      flag: '🇬🇧',
      name: 'English',
      nativeName: 'English',
      selectLabel: 'Choose language',
      confirmLabel: 'Continue',
    ),
    _Lang(
      code: 'ru',
      flag: '🇷🇺',
      name: 'Русский',
      nativeName: 'Русский язык',
      selectLabel: 'Выберите язык',
      confirmLabel: 'Продолжить',
    ),
    _Lang(
      code: 'zh',
      flag: '🇨🇳',
      name: '中文',
      nativeName: '中文（简体）',
      selectLabel: '选择语言',
      confirmLabel: '继续',
    ),
    _Lang(
      code: 'de',
      flag: '🇩🇪',
      name: 'Deutsch',
      nativeName: 'Deutsch',
      selectLabel: 'Sprache auswählen',
      confirmLabel: 'Weiter',
    ),
    _Lang(
      code: 'ko',
      flag: '🇰🇷',
      name: '한국어',
      nativeName: '한국어',
      selectLabel: '언어 선택',
      confirmLabel: '계속',
    ),
  ];

  late String _selected;
  late AnimationController _controller;
  late Animation<double> _fadeAnim;

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

    // Pre-select based on device system locale
    final systemCode =
        PlatformDispatcher.instance.locale.languageCode.toLowerCase();
    _selected = _languages.any((l) => l.code == systemCode)
        ? systemCode
        : 'uz'; // fallback to Uzbek

    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 600),
    );
    _fadeAnim = CurvedAnimation(parent: _controller, curve: Curves.easeIn);
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _confirm() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_prefKey, _selected);
    LocaleService.instance.locale = _selected;
    if (mounted) context.go('/onboarding');
  }

  @override
  Widget build(BuildContext context) {
    final lang = _languages.firstWhere((l) => l.code == _selected);

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Container(
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
        child: Stack(
          children: [
            // Aurora glow — top-left (cool blue)
            Positioned(
              top: -80,
              left: -60,
              child: Container(
                width: 320,
                height: 320,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      Color(0x331A6BAA),
                      Color(0x001A6BAA),
                    ],
                  ),
                ),
              ),
            ),
            // Aurora glow — bottom-right (gold accent)
            Positioned(
              bottom: -60,
              right: -80,
              child: Container(
                width: 280,
                height: 280,
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: RadialGradient(
                    colors: [
                      Color(0x22B78628),
                      Color(0x00B78628),
                    ],
                  ),
                ),
              ),
            ),
            // Main content
            SafeArea(
              child: FadeTransition(
                opacity: _fadeAnim,
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 28),
                  child: Column(
                    children: [
                      const SizedBox(height: 16),

                      // Step indicator row
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const SizedBox(width: 40),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.08),
                              borderRadius: BorderRadius.circular(20),
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.15),
                              ),
                            ),
                            child: Text(
                              '1 / 3',
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.6),
                                fontSize: 11,
                              ),
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 24),

                      // Logo
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
                      const SizedBox(height: 24),

                      const Text(
                        'SilkLens',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 32,
                          fontWeight: FontWeight.w800,
                          letterSpacing: 2,
                        ),
                      ),
                      const SizedBox(height: 8),
                      AnimatedSwitcher(
                        duration: const Duration(milliseconds: 250),
                        child: Text(
                          lang.selectLabel,
                          key: ValueKey(_selected),
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.55),
                            fontSize: 14,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),

                      const SizedBox(height: 32),

                      // Language list — glass-style container
                      Container(
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: 0.06),
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(
                            color: Colors.white.withValues(alpha: 0.12),
                          ),
                        ),
                        padding: const EdgeInsets.all(8),
                        child: Column(
                          children: List.generate(_languages.length, (i) {
                            final l = _languages[i];
                            final isSelected = _selected == l.code;
                            final isLast = i == _languages.length - 1;
                            return Column(
                              children: [
                                _LangTile(
                                  lang: l,
                                  selected: isSelected,
                                  onTap: () =>
                                      setState(() => _selected = l.code),
                                ),
                                if (!isLast) const SizedBox(height: 4),
                              ],
                            );
                          }),
                        ),
                      ),

                      const SizedBox(height: 32),

                      // Confirm button — gold gradient
                      SizedBox(
                        width: double.infinity,
                        height: 54,
                        child: DecoratedBox(
                          decoration: BoxDecoration(
                            gradient: const LinearGradient(
                              colors: [Color(0xFFD4A017), Color(0xFFB78628)],
                            ),
                            borderRadius: BorderRadius.circular(14),
                            boxShadow: [
                              BoxShadow(
                                color: const Color(0xFFB78628)
                                    .withValues(alpha: 0.35),
                                blurRadius: 12,
                                offset: const Offset(0, 4),
                              ),
                            ],
                          ),
                          child: FilledButton(
                            onPressed: _confirm,
                            style: FilledButton.styleFrom(
                              backgroundColor: Colors.transparent,
                              shadowColor: Colors.transparent,
                              foregroundColor: Colors.white,
                              shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(14),
                              ),
                              textStyle: const TextStyle(
                                fontSize: 16,
                                fontWeight: FontWeight.w700,
                                letterSpacing: 0.5,
                              ),
                            ),
                            child: AnimatedSwitcher(
                              duration: const Duration(milliseconds: 200),
                              child: Text(
                                lang.confirmLabel,
                                key: ValueKey(_selected),
                              ),
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 32),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _LangTile extends StatelessWidget {
  const _LangTile({
    required this.lang,
    required this.selected,
    required this.onTap,
  });

  final _Lang lang;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        decoration: BoxDecoration(
          color: selected
              ? Colors.white.withValues(alpha: 0.18)
              : Colors.white.withValues(alpha: 0.07),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: selected
                ? Colors.white.withValues(alpha: 0.6)
                : Colors.white.withValues(alpha: 0.15),
            width: selected ? 1.5 : 1,
          ),
        ),
        child: Row(
          children: [
            // Flag
            Text(lang.flag, style: const TextStyle(fontSize: 28)),
            const SizedBox(width: 16),
            // Names
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    lang.name,
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
                    ),
                  ),
                  Text(
                    lang.nativeName,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.5),
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
            // Gold radio dot (selected indicator)
            AnimatedOpacity(
              opacity: selected ? 1.0 : 0.0,
              duration: const Duration(milliseconds: 200),
              child: Container(
                width: 20,
                height: 20,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: const Color(0xFFB78628),
                  boxShadow: [
                    BoxShadow(
                      color: const Color(0xFFB78628).withValues(alpha: 0.4),
                      blurRadius: 8,
                    ),
                  ],
                ),
                child: const Icon(
                  Icons.circle,
                  color: Colors.white,
                  size: 8,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _Lang {
  const _Lang({
    required this.code,
    required this.flag,
    required this.name,
    required this.nativeName,
    required this.selectLabel,
    required this.confirmLabel,
  });
  final String code;
  final String flag;
  final String name;
  final String nativeName;
  final String selectLabel;
  final String confirmLabel;
}
