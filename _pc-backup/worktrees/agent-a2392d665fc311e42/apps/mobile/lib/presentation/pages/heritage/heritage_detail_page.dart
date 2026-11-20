// SILK-0098 — HeritageDetailPage extended with Kids Story + Cultural Tips tabs.
// Tab count: About / Facts / Reviews / Kids / Culture (5 total).
// Kids story loaded lazily on first tab visit via getKidsStory.
// Cultural tips loaded lazily on first tab visit via getHeritageCulturalTips.

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';
import 'package:silklens/presentation/providers/heritage_detail_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class HeritageDetailPage extends ConsumerStatefulWidget {
  const HeritageDetailPage({required this.pubId, super.key});
  final String pubId;

  @override
  ConsumerState<HeritageDetailPage> createState() => _HeritageDetailPageState();
}

class _HeritageDetailPageState extends ConsumerState<HeritageDetailPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabCtrl;
  int _activeTab = 0;

  // Lazy-loaded Kids & Culture tab state.
  String? _kidsStory;
  bool _kidsLoading = false;
  bool _kidsLoaded = false;

  List<Map<String, dynamic>> _culturalTips = [];
  bool _cultureLoading = false;
  bool _cultureLoaded = false;

  static const _gold = Color(0xFFB78628);
  static const _bg = Color(0xFF0D2337);

  // Tab indices.
  static const _tabAbout = 0;
  static const _tabFacts = 1;
  static const _tabReviews = 2;
  static const _tabKids = 3;
  static const _tabCulture = 4;

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 5, vsync: this);
    _tabCtrl.addListener(() {
      if (!mounted) return;
      setState(() => _activeTab = _tabCtrl.index);
      // Lazy-load when tab is first visited.
      if (_tabCtrl.index == _tabKids && !_kidsLoaded) _loadKidsStory();
      if (_tabCtrl.index == _tabCulture && !_cultureLoaded) _loadCultureTips();
    });
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    super.dispose();
  }

  String _s(String key) {
    final lang = ref.read(activeLocaleProvider).languageCode;
    return AppStrings.get(lang, key);
  }

  Future<void> _loadKidsStory() async {
    if (_kidsLoaded || _kidsLoading) return;
    setState(() => _kidsLoading = true);
    final lang = ref.read(activeLocaleProvider).languageCode;
    final client = ref.read(silkLensApiClientProvider);
    final story = await client.getKidsStory(
      pubId: widget.pubId,
      language: lang,
    );
    if (!mounted) return;
    setState(() {
      _kidsStory = story;
      _kidsLoading = false;
      _kidsLoaded = true;
    });
  }

  Future<void> _loadCultureTips() async {
    if (_cultureLoaded || _cultureLoading) return;
    setState(() => _cultureLoading = true);
    final lang = ref.read(activeLocaleProvider).languageCode;
    final client = ref.read(silkLensApiClientProvider);
    final tips = await client.getHeritageCulturalTips(
      pubId: widget.pubId,
      language: lang,
    );
    if (!mounted) return;
    setState(() {
      _culturalTips = tips.map((e) => Map<String, dynamic>.from(e as Map)).toList();
      _cultureLoading = false;
      _cultureLoaded = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    final heritage = ref.watch(heritageDetailProvider(widget.pubId));
    final isSaved = ref.watch(heritageSavedProvider(widget.pubId));
    final lang = ref.watch(activeLocaleProvider).languageCode;

    return Scaffold(
      backgroundColor: _bg,
      body: heritage.when(
        loading: () => const Center(
          child: CircularProgressIndicator(color: _gold),
        ),
        error: (e, _) => Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.wifi_off_rounded,
                color: Colors.white.withValues(alpha: 0.4),
                size: 48,
              ),
              const SizedBox(height: 12),
              Text(
                e.toString(),
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.6),
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 16),
              GestureDetector(
                onTap: () => ref.invalidate(heritageDetailProvider(widget.pubId)),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: _gold,
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    _s('heritage_retry'),
                    style: const TextStyle(
                      color: Color(0xFF1A1200),
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
        data: (item) => _buildContent(context, item, isSaved, lang),
      ),
    );
  }

  Widget _buildContent(
    BuildContext context,
    Heritage item,
    bool isSaved,
    String lang,
  ) {
    final title = item.localizedName(lang);
    final summary = item.localizedSummary(lang);
    final description = item.localizedDescription(lang);
    final location = item.countryCode ?? '';
    final period = item.periodLabel;

    final tabs = [
      _s('heritage_tab_about'),
      _s('heritage_tab_facts'),
      _s('heritage_tab_reviews'),
      _s('heritage_tab_kids'),
      _s('heritage_tab_culture'),
    ];

    return CustomScrollView(
      slivers: [
        // ── Hero image sliver ────────────────────────────────────────────
        SliverAppBar(
          expandedHeight: MediaQuery.sizeOf(context).height * 0.48,
          pinned: true,
          backgroundColor: _bg,
          leading: GestureDetector(
            onTap: () => context.pop(),
            child: Container(
              margin: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.black.withValues(alpha: 0.35),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.2),
                ),
              ),
              child: const Icon(
                Icons.arrow_back_ios_new,
                color: Colors.white,
                size: 18,
              ),
            ),
          ),
          actions: [
            GestureDetector(
              onTap: () => ref.read(heritageSavedProvider(widget.pubId).notifier).toggle(),
              child: Container(
                margin: const EdgeInsets.all(8),
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.black.withValues(alpha: 0.35),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.2),
                  ),
                ),
                child: Icon(
                  isSaved ? Icons.bookmark_rounded : Icons.bookmark_outline_rounded,
                  color: isSaved ? _gold : Colors.white,
                  size: 20,
                ),
              ),
            ),
            Container(
              margin: const EdgeInsets.only(right: 8, top: 8, bottom: 8),
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: Colors.black.withValues(alpha: 0.35),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.2),
                ),
              ),
              child: const Icon(
                Icons.share_outlined,
                color: Colors.white,
                size: 20,
              ),
            ),
          ],
          flexibleSpace: FlexibleSpaceBar(
            background: Stack(
              fit: StackFit.expand,
              children: [
                // Heritage tone gradient placeholder until media service lands
                Container(
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [
                        Color(0xFF8B3A2A),
                        Color(0xFFD2691E),
                        Color(0xFF8B6914),
                      ],
                    ),
                  ),
                ),
                // Photo caption
                Positioned(
                  bottom: 16,
                  left: 16,
                  child: Text(
                    '${item.kindSlug.toUpperCase()} · ${location.toUpperCase()}',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.65),
                      fontSize: 9,
                      fontFamily: 'monospace',
                      letterSpacing: 2,
                    ),
                  ),
                ),
                // UNESCO badge
                if (item.isUnescoListed)
                  Positioned(
                    top: 16,
                    right: 16,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: _gold,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Text(
                        'UNESCO',
                        style: TextStyle(
                          color: Color(0xFF1A1200),
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ),
                // Bottom gradient overlay
                Positioned(
                  bottom: 0,
                  left: 0,
                  right: 0,
                  child: Container(
                    height: 80,
                    decoration: BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topCenter,
                        end: Alignment.bottomCenter,
                        colors: [
                          Colors.transparent,
                          _bg.withValues(alpha: 0.9),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),

        // ── Glass info card ───────────────────────────────────────────────
        SliverToBoxAdapter(
          child: Container(
            margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.07),
              borderRadius: BorderRadius.circular(24),
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.12),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 28,
                    fontWeight: FontWeight.w800,
                  ),
                ),
                const SizedBox(height: 6),
                if (location.isNotEmpty)
                  Row(
                    children: [
                      const Icon(
                        Icons.location_on,
                        color: _gold,
                        size: 14,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        location,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.7),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                const SizedBox(height: 12),
                // Info chips
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: [
                    if (period.isNotEmpty) _InfoChip(period, Icons.history_edu_rounded),
                    _InfoChip(item.kindSlug, Icons.account_balance_rounded),
                    if (item.isUnescoListed)
                      _InfoChip(
                        'UNESCO ${item.unescoInscriptionYear ?? ''}',
                        Icons.workspace_premium_rounded,
                      ),
                  ],
                ),
                const SizedBox(height: 20),

                // ── Tab bar (5 tabs) ────────────────────────────────────
                Container(
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.06),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: TabBar(
                    controller: _tabCtrl,
                    isScrollable: true,
                    tabAlignment: TabAlignment.start,
                    indicatorSize: TabBarIndicatorSize.tab,
                    indicator: BoxDecoration(
                      color: _gold,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    labelColor: const Color(0xFF1A1200),
                    unselectedLabelColor: Colors.white.withValues(alpha: 0.6),
                    labelStyle: const TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                    ),
                    tabs: tabs.map((t) => Tab(text: t)).toList(),
                  ),
                ),
                const SizedBox(height: 16),

                // ── Tab content ─────────────────────────────────────────
                if (_activeTab == _tabAbout)
                  Text(
                    description.isNotEmpty
                        ? description
                        : summary.isNotEmpty
                            ? summary
                            : AppStrings.get(lang, 'heritage_no_description'),
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.85),
                      fontSize: 14,
                      height: 1.6,
                    ),
                  )
                else if (_activeTab == _tabFacts)
                  Column(
                    children: [
                      if (period.isNotEmpty)
                        _FactRow(
                          AppStrings.get(lang, 'heritage_period'),
                          period,
                        ),
                      if (location.isNotEmpty)
                        _FactRow(
                          AppStrings.get(lang, 'heritage_country'),
                          location,
                        ),
                      _FactRow(
                        AppStrings.get(lang, 'heritage_kind'),
                        item.kindSlug,
                      ),
                      ...item.tags.map(
                        (t) => _FactRow('#', t),
                      ),
                    ],
                  )
                else if (_activeTab == _tabReviews)
                  Text(
                    AppStrings.get(lang, 'heritage_reviews_loading'),
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.5),
                      fontSize: 14,
                    ),
                  )
                else if (_activeTab == _tabKids)
                  _KidsTabContent(
                    isLoading: _kidsLoading,
                    story: _kidsStory,
                    loadingLabel: AppStrings.get(lang, 'heritage_kids_loading'),
                    emptyLabel: AppStrings.get(lang, 'heritage_kids_empty'),
                  )
                else if (_activeTab == _tabCulture)
                  _CultureTabContent(
                    isLoading: _cultureLoading,
                    tips: _culturalTips,
                    loadingLabel: AppStrings.get(lang, 'heritage_culture_loading'),
                    emptyLabel: AppStrings.get(lang, 'heritage_culture_empty'),
                    severityLabel: AppStrings.get(lang, 'heritage_culture_severity'),
                  ),
              ],
            ),
          ),
        ),

        // ── Action buttons ────────────────────────────────────────────────
        SliverToBoxAdapter(
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                _ActionBtn(
                  Icons.volume_up_rounded,
                  AppStrings.get(lang, 'heritage_action_audio'),
                  () {},
                ),
                _ActionBtn(
                  Icons.view_in_ar_rounded,
                  AppStrings.get(lang, 'heritage_action_ar'),
                  () {},
                  isGold: true,
                ),
                _ActionBtn(
                  Icons.map_rounded,
                  AppStrings.get(lang, 'heritage_action_directions'),
                  () {},
                ),
                _ActionBtn(
                  Icons.photo_library_outlined,
                  AppStrings.get(lang, 'heritage_action_photos'),
                  () {},
                ),
                // SILK-0100 — AI Photo Guide
                _ActionBtn(
                  Icons.camera_enhance_outlined,
                  AppStrings.get(lang, 'heritage_action_photo_guide'),
                  () => context.push(
                    '/photo-guide/${item.pubId}'
                    '?name=${Uri.encodeComponent(item.localizedName(lang))}',
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}

// ─── Kids tab ─────────────────────────────────────────────────────────────────

class _KidsTabContent extends StatelessWidget {
  const _KidsTabContent({
    required this.isLoading,
    required this.story,
    required this.loadingLabel,
    required this.emptyLabel,
  });

  final bool isLoading;
  final String? story;
  final String loadingLabel;
  final String emptyLabel;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          children: [
            const CircularProgressIndicator(
              color: Color(0xFFB78628),
              strokeWidth: 2,
            ),
            const SizedBox(height: 12),
            Text(
              loadingLabel,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.5),
                fontSize: 13,
              ),
            ),
          ],
        ),
      );
    }
    if (story == null || story!.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Row(
          children: [
            const Text('🧒', style: TextStyle(fontSize: 28)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                emptyLabel,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.55),
                  fontSize: 14,
                  height: 1.5,
                ),
              ),
            ),
          ],
        ),
      );
    }
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: const Color(0xFF1A3A5C).withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFFB78628).withValues(alpha: 0.3),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Text('🧒', style: TextStyle(fontSize: 20)),
              SizedBox(width: 8),
              Text(
                '✨',
                style: TextStyle(fontSize: 16),
              ),
            ],
          ),
          const SizedBox(height: 10),
          Text(
            story!,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 14,
              height: 1.7,
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Culture tab ──────────────────────────────────────────────────────────────

class _CultureTabContent extends StatelessWidget {
  const _CultureTabContent({
    required this.isLoading,
    required this.tips,
    required this.loadingLabel,
    required this.emptyLabel,
    required this.severityLabel,
  });

  final bool isLoading;
  final List<Map<String, dynamic>> tips;
  final String loadingLabel;
  final String emptyLabel;
  final String severityLabel;

  @override
  Widget build(BuildContext context) {
    if (isLoading) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 24),
        child: Column(
          children: [
            const CircularProgressIndicator(
              color: Color(0xFFB78628),
              strokeWidth: 2,
            ),
            const SizedBox(height: 12),
            Text(
              loadingLabel,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.5),
                fontSize: 13,
              ),
            ),
          ],
        ),
      );
    }
    if (tips.isEmpty) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Row(
          children: [
            const Text('🏛️', style: TextStyle(fontSize: 28)),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                emptyLabel,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.55),
                  fontSize: 14,
                  height: 1.5,
                ),
              ),
            ),
          ],
        ),
      );
    }
    return Column(
      children: tips.map((tip) => _CulturalTipCard(tip: tip)).toList(),
    );
  }
}

class _CulturalTipCard extends StatelessWidget {
  const _CulturalTipCard({required this.tip});

  final Map<String, dynamic> tip;

  static const _severityColors = {
    'high': Color(0xFFE53935),
    'medium': Color(0xFFFF8F00),
    'low': Color(0xFF43A047),
  };

  @override
  Widget build(BuildContext context) {
    final body = tip['body'] as String? ?? tip['text'] as String? ?? tip['tip'] as String? ?? '';
    final severity = (tip['severity'] as String? ?? 'low').toLowerCase();
    final badgeColor = _severityColors[severity] ?? const Color(0xFF43A047);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(
          color: badgeColor.withValues(alpha: 0.4),
        ),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 6,
            height: 6,
            margin: const EdgeInsets.only(top: 5, right: 10),
            decoration: BoxDecoration(
              color: badgeColor,
              shape: BoxShape.circle,
            ),
          ),
          Expanded(
            child: Text(
              body,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13,
                height: 1.5,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
            decoration: BoxDecoration(
              color: badgeColor.withValues(alpha: 0.2),
              borderRadius: BorderRadius.circular(6),
              border: Border.all(color: badgeColor.withValues(alpha: 0.5)),
            ),
            child: Text(
              severity.toUpperCase(),
              style: TextStyle(
                color: badgeColor,
                fontSize: 9,
                fontWeight: FontWeight.w700,
                letterSpacing: 0.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ─── Shared sub-widgets (same as before) ─────────────────────────────────────

class _InfoChip extends StatelessWidget {
  const _InfoChip(this.label, this.icon);
  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: const Color(0xFFB78628)),
          const SizedBox(width: 4),
          Text(
            label,
            style: const TextStyle(color: Colors.white, fontSize: 11),
          ),
        ],
      ),
    );
  }
}

class _FactRow extends StatelessWidget {
  const _FactRow(this.label, this.value);
  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.55),
              fontSize: 13,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionBtn extends StatelessWidget {
  const _ActionBtn(this.icon, this.label, this.onTap, {this.isGold = false});
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool isGold;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          height: 54,
          decoration: BoxDecoration(
            color: isGold ? const Color(0xFFB78628) : Colors.white.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(14),
            border: isGold
                ? null
                : Border.all(
                    color: Colors.white.withValues(alpha: 0.15),
                  ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                color: isGold ? const Color(0xFF1A1200) : Colors.white,
                size: 20,
              ),
              const SizedBox(height: 2),
              Text(
                label,
                style: TextStyle(
                  color: isGold ? const Color(0xFF1A1200) : Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
