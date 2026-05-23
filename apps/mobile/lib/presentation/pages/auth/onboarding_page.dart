import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:google_fonts/google_fonts.dart';

import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/core/theme/silk_animations.dart';
import 'package:silklens/presentation/widgets/glass/onboarding_icons.dart';

class OnboardingPage extends StatefulWidget {
  const OnboardingPage({super.key});

  @override
  State<OnboardingPage> createState() => _OnboardingPageState();
}

class _OnboardingPageState extends State<OnboardingPage> {
  final _pageController = PageController();
  int _currentPage = 0;

  // Per-page heritage gradient sets [dark, mid, accent]
  static const _backdrops = [
    // Page 1 — Registan, Samarqand: warm terracotta
    [Color(0xFF2D1810), Color(0xFF8B3A2A), Color(0xFFD2691E)],
    // Page 2 — Kalon, Bukhara: lapis blue
    [Color(0xFF0D1A3A), Color(0xFF1A3A5C), Color(0xFF2E6B9E)],
    // Page 3 — Ichan Qal'a, Khiva: golden amber
    [Color(0xFF1A150A), Color(0xFF5C3A10), Color(0xFFD4A853)],
  ];

  static const _locations = [
    '─── Registon · Samarqand',
    '─── Kalon · Buxoro',
    "─── Ichan Qal'a · Xiva",
  ];

  static const _iconWidgets = [
    CompassRoseIcon(size: 80),
    AICameraIcon(size: 80),
    CommunityIcon(size: 80),
  ];

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
    _pageController.dispose();
    super.dispose();
  }

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  void _next() {
    if (_currentPage < 2) {
      _pageController.nextPage(
        duration: SilkDurations.pageSlide,
        curve: SilkCurves.springSlide,
      );
    } else {
      context.go('/auth/choice');
    }
  }

  void _back() {
    _pageController.previousPage(
      duration: SilkDurations.pageSlide,
      curve: SilkCurves.springSlide,
    );
  }

  @override
  Widget build(BuildContext context) {
    final backdrop = _backdrops[_currentPage];

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Stack(
        fit: StackFit.expand,
        children: [
          // Radial glow 1 — upper-left mid tone
          AnimatedContainer(
            duration: const Duration(milliseconds: 400),
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: const Alignment(-0.3, -0.3),
                radius: 1.5,
                colors: [
                  Color.fromRGBO(
                    backdrop[1].r.toInt(),
                    backdrop[1].g.toInt(),
                    backdrop[1].b.toInt(),
                    0.70,
                  ),
                  Colors.transparent,
                ],
              ),
            ),
          ),
          // Radial glow 2 — lower-right accent tone
          AnimatedContainer(
            duration: const Duration(milliseconds: 400),
            decoration: BoxDecoration(
              gradient: RadialGradient(
                center: const Alignment(0.5, 0.4),
                radius: 1.2,
                colors: [
                  Color.fromRGBO(
                    backdrop[2].r.toInt(),
                    backdrop[2].g.toInt(),
                    backdrop[2].b.toInt(),
                    0.40,
                  ),
                  Colors.transparent,
                ],
              ),
            ),
          ),
          // Dark vertical overlay
          AnimatedContainer(
            duration: const Duration(milliseconds: 400),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  Color.fromRGBO(
                    backdrop[0].r.toInt(),
                    backdrop[0].g.toInt(),
                    backdrop[0].b.toInt(),
                    0.60,
                  ),
                  const Color(0xFF0D2337),
                ],
              ),
            ),
          ),

          // Content
          SafeArea(
            child: Column(
              children: [
                // Skip button top-right
                Align(
                  alignment: Alignment.topRight,
                  child: Padding(
                    padding: const EdgeInsets.only(top: 8, right: 16),
                    child: TextButton(
                      onPressed: () => context.go('/auth/choice'),
                      child: Text(
                        _s('onb_skip'),
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.65),
                          fontSize: 15,
                        ),
                      ),
                    ),
                  ),
                ),

                // PageView
                Expanded(
                  child: PageView.builder(
                    controller: _pageController,
                    onPageChanged: (i) => setState(() => _currentPage = i),
                    itemCount: 3,
                    itemBuilder: (_, i) => _PageContent(
                      pageIndex: i,
                      iconWidget: _iconWidgets[i],
                      titleKey: 'onb_p${i + 1}_title',
                      subtitleKey: 'onb_p${i + 1}_sub',
                      location: _locations[i],
                      s: _s,
                    ),
                  ),
                ),

                // Gold dot indicator in glass pill
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.15),
                    ),
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    children: List.generate(3, (i) {
                      final active = _currentPage == i;
                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 250),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        width: active ? 24 : 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: active
                              ? const Color(0xFFE5C97A)
                              : Colors.white.withValues(alpha: 0.35),
                          borderRadius: BorderRadius.circular(4),
                          boxShadow: active
                              ? const [
                                  BoxShadow(
                                    color: Color(0x66E5C97A),
                                    blurRadius: 6,
                                  ),
                                ]
                              : null,
                        ),
                      );
                    }),
                  ),
                ),

                const SizedBox(height: 24),

                // Navigation buttons
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24),
                  child: Column(
                    children: [
                      Row(
                        children: [
                          if (_currentPage > 0) ...[
                            Expanded(
                              child: _GlassBackButton(
                                onTap: _back,
                                label: _s('onb_back'),
                              ),
                            ),
                            const SizedBox(width: 12),
                          ],
                          Expanded(
                            flex: _currentPage > 0 ? 2 : 1,
                            child: _GoldNextButton(
                              label: _currentPage == 2 ? _s('onb_get_started') : _s('onb_next'),
                              onTap: _next,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      GestureDetector(
                        onTap: () => context.go('/auth/sign-in'),
                        child: Text(
                          _s('onb_have_account'),
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.55),
                            fontSize: 14,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 32),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Page content
// ---------------------------------------------------------------------------

class _PageContent extends StatelessWidget {
  const _PageContent({
    required this.pageIndex,
    required this.iconWidget,
    required this.titleKey,
    required this.subtitleKey,
    required this.location,
    required this.s,
  });

  final int pageIndex;
  final Widget iconWidget;
  final String titleKey;
  final String subtitleKey;
  final String location;
  final String Function(String) s;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 32),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          // Glass icon container
          Container(
            width: 120,
            height: 120,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(32),
              color: Colors.white.withValues(alpha: 0.12),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.25),
              ),
              boxShadow: const [
                BoxShadow(
                  color: Color(0x40B78628),
                  blurRadius: 24,
                  offset: Offset(0, 8),
                ),
              ],
            ),
            child: iconWidget,
          ),

          const SizedBox(height: 32),

          // Location caption
          Text(
            location,
            style: const TextStyle(
              color: Color(0xFFB78628),
              fontSize: 10,
              letterSpacing: 2,
              fontFamily: 'monospace',
            ),
          ),

          const SizedBox(height: 8),

          // Title — Playfair Display
          Text(
            s(titleKey),
            textAlign: TextAlign.center,
            style: GoogleFonts.playfairDisplay(
              color: Colors.white,
              fontSize: 28,
              fontWeight: FontWeight.w700,
              height: 1.2,
            ),
          ),

          const SizedBox(height: 16),

          // Subtitle
          Text(
            s(subtitleKey),
            textAlign: TextAlign.center,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.72),
              fontSize: 15,
              height: 1.6,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Gold Next / Get Started button
// ---------------------------------------------------------------------------

class _GoldNextButton extends StatelessWidget {
  const _GoldNextButton({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 54,
        decoration: BoxDecoration(
          gradient: const LinearGradient(
            colors: [Color(0xFFE5C97A), Color(0xFFB78628)],
          ),
          borderRadius: BorderRadius.circular(14),
          boxShadow: const [
            BoxShadow(
              color: Color(0x4DB78628),
              blurRadius: 16,
              offset: Offset(0, 4),
            ),
          ],
        ),
        child: Center(
          child: Text(
            label,
            style: const TextStyle(
              color: Color(0xFF2A1810),
              fontSize: 16,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Glass Back button
// ---------------------------------------------------------------------------

class _GlassBackButton extends StatelessWidget {
  const _GlassBackButton({required this.onTap, required this.label});

  final VoidCallback onTap;
  final String label;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        height: 54,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.25),
          ),
        ),
        child: Center(
          child: Text(
            '← $label',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.85),
              fontSize: 15,
            ),
          ),
        ),
      ),
    );
  }
}
