import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

class AIUtilitiesPage extends ConsumerStatefulWidget {
  const AIUtilitiesPage({super.key});

  @override
  ConsumerState<AIUtilitiesPage> createState() => _AIUtilitiesPageState();
}

class _AIUtilitiesPageState extends ConsumerState<AIUtilitiesPage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabs;

  // Bargaining state
  final _itemCtrl = TextEditingController();
  final _marketCtrl = TextEditingController();
  Map<String, dynamic>? _priceResult;

  // Scam state
  final _venueCtrl = TextEditingController();
  final _serviceCtrl = TextEditingController();
  final _priceCtrl = TextEditingController();
  Map<String, dynamic>? _scamResult;

  // Lost & Found state
  String _lostItemType = 'passport';
  Map<String, dynamic>? _lostResult;

  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _tabs = TabController(length: 3, vsync: this);
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: Color(0xFF0D2337),
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );
  }

  @override
  void dispose() {
    _tabs.dispose();
    _itemCtrl.dispose();
    _marketCtrl.dispose();
    _venueCtrl.dispose();
    _serviceCtrl.dispose();
    _priceCtrl.dispose();
    super.dispose();
  }

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  Future<void> _checkFairPrice() async {
    if (_itemCtrl.text.trim().isEmpty || _marketCtrl.text.trim().isEmpty) {
      return;
    }
    setState(() {
      _isLoading = true;
      _priceResult = null;
    });
    try {
      final client = ref.read(silkLensApiClientProvider);
      final data = await client.checkFairPrice(
        item: _itemCtrl.text.trim(),
        market: _marketCtrl.text.trim(),
        language: LocaleService.instance.locale,
      );
      if (!mounted) return;
      setState(() {
        _priceResult = data;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _checkScam() async {
    setState(() {
      _isLoading = true;
      _scamResult = null;
    });
    try {
      final client = ref.read(silkLensApiClientProvider);
      final price = double.tryParse(_priceCtrl.text.trim()) ?? 10.0;
      final data = await client.checkScam(
        venueName: _venueCtrl.text.trim(),
        serviceDescription: _serviceCtrl.text.trim(),
        quotedPriceUsd: price,
        language: LocaleService.instance.locale,
      );
      if (!mounted) return;
      setState(() {
        _scamResult = data;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Future<void> _findLostHelp() async {
    setState(() {
      _isLoading = true;
      _lostResult = null;
    });
    try {
      final client = ref.read(silkLensApiClientProvider);
      final data = await client.getLostFoundHelp(
        itemType: _lostItemType,
        language: LocaleService.instance.locale,
      );
      if (!mounted) return;
      setState(() {
        _lostResult = data;
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Widget _buildInput({
    required TextEditingController ctrl,
    required String hint,
    required IconData icon,
  }) {
    return TextField(
      controller: ctrl,
      style: const TextStyle(color: Colors.white),
      decoration: InputDecoration(
        hintText: hint,
        hintStyle: const TextStyle(color: Colors.white38),
        prefixIcon: Icon(icon, color: const Color(0xFFB78628)),
        filled: true,
        fillColor: Colors.white.withValues(alpha: 0.08),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(
            color: Color(0xFFB78628),
          ),
        ),
      ),
    );
  }

  Widget _buildBargainingTab() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildInput(
          ctrl: _itemCtrl,
          hint: _s('aiutil_bargain_item_hint'),
          icon: Icons.shopping_bag,
        ),
        const SizedBox(height: 10),
        _buildInput(
          ctrl: _marketCtrl,
          hint: _s('aiutil_bargain_market_hint'),
          icon: Icons.store,
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          height: 48,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _checkFairPrice,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFB78628),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: _isLoading
                ? const CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2,
                  )
                : Text(_s('aiutil_bargain_check_btn')),
          ),
        ),
        if (_priceResult != null) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: const Color(0xFFB78628).withValues(alpha: 0.3),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (_priceResult!['typical_price_usd'] != null)
                  Text(
                    '\$${_priceResult!['typical_price_usd']} ${_s('aiutil_bargain_around')}',
                    style: const TextStyle(
                      color: Color(0xFFB78628),
                      fontSize: 20,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                if (_priceResult!['negotiation_tip'] != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    _priceResult!['negotiation_tip'] as String,
                    style: const TextStyle(color: Colors.white70),
                  ),
                ],
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildScamTab() {
    final verdict = _scamResult?['verdict'] as String? ?? '';
    final scamColor = switch (verdict) {
      'likely_scam' => const Color(0xFFE53935),
      'suspicious' => const Color(0xFFFFA726),
      _ => const Color(0xFF4CAF50),
    };

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        _buildInput(
          ctrl: _venueCtrl,
          hint: _s('aiutil_scam_venue_hint'),
          icon: Icons.place,
        ),
        const SizedBox(height: 10),
        _buildInput(
          ctrl: _serviceCtrl,
          hint: _s('aiutil_scam_service_hint'),
          icon: Icons.miscellaneous_services,
        ),
        const SizedBox(height: 10),
        _buildInput(
          ctrl: _priceCtrl,
          hint: _s('aiutil_scam_price_hint'),
          icon: Icons.attach_money,
        ),
        const SizedBox(height: 12),
        SizedBox(
          width: double.infinity,
          height: 48,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _checkScam,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFE53935),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: _isLoading
                ? const CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2,
                  )
                : Text(_s('aiutil_scam_check_btn')),
          ),
        ),
        if (_scamResult != null) ...[
          const SizedBox(height: 16),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: scamColor.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(
                color: scamColor.withValues(alpha: 0.4),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  switch (verdict) {
                    'safe' => _s('aiutil_scam_verdict_safe'),
                    'suspicious' => _s('aiutil_scam_verdict_suspicious'),
                    _ => _s('aiutil_scam_verdict_scam'),
                  },
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                    fontSize: 16,
                  ),
                ),
                if (_scamResult!['advice'] != null) ...[
                  const SizedBox(height: 8),
                  Text(
                    _scamResult!['advice'] as String,
                    style: const TextStyle(color: Colors.white70),
                  ),
                ],
              ],
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildLostTab() {
    final lostTypes = ['passport', 'phone', 'wallet', 'bag'];
    final lostLabels = [
      _s('aiutil_lost_passport'),
      _s('aiutil_lost_phone'),
      _s('aiutil_lost_wallet'),
      _s('aiutil_lost_bag'),
    ];

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Text(
          _s('aiutil_lost_select_label'),
          style: const TextStyle(color: Colors.white60),
        ),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: List.generate(lostTypes.length, (i) {
            final type = lostTypes[i];
            final isSelected = _lostItemType == type;
            return FilterChip(
              label: Text(lostLabels[i]),
              selected: isSelected,
              onSelected: (_) => setState(() => _lostItemType = type),
              selectedColor: const Color(0xFFB78628).withValues(alpha: 0.3),
              checkmarkColor: const Color(0xFFB78628),
              labelStyle: TextStyle(
                color: isSelected ? const Color(0xFFB78628) : Colors.white70,
              ),
              backgroundColor: Colors.white.withValues(alpha: 0.08),
              side: BorderSide(
                color: isSelected ? const Color(0xFFB78628) : Colors.white24,
              ),
            );
          }),
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          height: 48,
          child: ElevatedButton(
            onPressed: _isLoading ? null : _findLostHelp,
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFB78628),
              foregroundColor: Colors.white,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(12),
              ),
            ),
            child: _isLoading
                ? const CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2,
                  )
                : Text(_s('aiutil_lost_help_btn')),
          ),
        ),
        if (_lostResult != null) ...[
          const SizedBox(height: 16),
          ...((_lostResult!['steps'] as List?) ?? []).map((s) {
            return Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(
                    Icons.check_circle_outline,
                    color: Color(0xFFB78628),
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      s as String,
                      style: const TextStyle(color: Colors.white70),
                    ),
                  ),
                ],
              ),
            );
          }),
          const SizedBox(height: 8),
          ...((_lostResult!['nearest_help'] as List?) ?? []).take(3).map((h) {
            final m = h as Map<String, dynamic>;
            return ListTile(
              contentPadding: EdgeInsets.zero,
              leading: Container(
                padding: const EdgeInsets.all(6),
                decoration: BoxDecoration(
                  color: const Color(0xFFB78628).withValues(alpha: 0.15),
                  shape: BoxShape.circle,
                ),
                child: const Icon(
                  Icons.place,
                  color: Color(0xFFB78628),
                  size: 16,
                ),
              ),
              title: Text(
                m['name'] as String? ?? '',
                style: const TextStyle(color: Colors.white),
              ),
              subtitle: Text(
                m['phone'] as String? ?? '',
                style: const TextStyle(color: Color(0xFFB78628)),
              ),
            );
          }),
        ],
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          _s('aiutil_title'),
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w600,
          ),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => context.pop(),
        ),
        bottom: TabBar(
          controller: _tabs,
          indicatorColor: const Color(0xFFB78628),
          labelColor: const Color(0xFFB78628),
          unselectedLabelColor: Colors.white60,
          tabs: [
            Tab(text: _s('aiutil_tab_bargain')),
            Tab(text: _s('aiutil_tab_scam')),
            Tab(text: _s('aiutil_tab_lost')),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabs,
        children: [
          _buildBargainingTab(),
          _buildScamTab(),
          _buildLostTab(),
        ],
      ),
    );
  }
}
