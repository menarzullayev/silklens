import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

class GovernmentPage extends ConsumerStatefulWidget {
  const GovernmentPage({super.key});

  @override
  ConsumerState<GovernmentPage> createState() => _GovernmentPageState();
}

class _GovernmentPageState extends ConsumerState<GovernmentPage> {
  List<Map<String, dynamic>> _items = [];
  bool _isLoading = true;
  String? _selectedKind;

  static const _kinds = [
    'holiday',
    'law',
    'visa_info',
    'emergency',
    'announcement',
  ];

  static const _kindIcons = [
    Icons.celebration,
    Icons.gavel,
    Icons.airplane_ticket,
    Icons.warning,
    Icons.campaign,
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
    _loadInfo();
  }

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  List<String> get _kindNames => [
        _s('gov_kind_holiday'),
        _s('gov_kind_law'),
        _s('gov_kind_visa'),
        _s('gov_kind_emergency'),
        _s('gov_kind_announcement'),
      ];

  Future<void> _loadInfo() async {
    setState(() => _isLoading = true);
    try {
      final client = ref.read(silkLensApiClientProvider);
      final items = await client.getGovernmentInfo(
        language: LocaleService.instance.locale,
        kind: _selectedKind,
      );
      if (!mounted) return;
      setState(() {
        _items = items.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        _isLoading = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoading = false);
    }
  }

  Widget _chip(
    String label,
    String? kind,
    IconData? icon,
    bool selected,
  ) {
    return FilterChip(
      label: icon != null
          ? Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  icon,
                  size: 14,
                  color: selected ? const Color(0xFFB78628) : Colors.white60,
                ),
                const SizedBox(width: 4),
                Text(label),
              ],
            )
          : Text(label),
      selected: selected,
      onSelected: (_) {
        setState(() => _selectedKind = kind);
        _loadInfo();
      },
      selectedColor: const Color(0xFFB78628).withValues(alpha: 0.3),
      checkmarkColor: const Color(0xFFB78628),
      labelStyle: TextStyle(
        color: selected ? const Color(0xFFB78628) : Colors.white70,
      ),
      backgroundColor: Colors.white.withValues(alpha: 0.08),
      side: BorderSide(
        color: selected ? const Color(0xFFB78628) : Colors.white24,
      ),
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
          _s('gov_title'),
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w600,
          ),
        ),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back, color: Colors.white),
          onPressed: () => context.pop(),
        ),
      ),
      body: Column(
        children: [
          SizedBox(
            height: 56,
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              scrollDirection: Axis.horizontal,
              itemCount: _kinds.length + 1,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) {
                if (i == 0) {
                  return _chip(
                    _s('gov_filter_all'),
                    null,
                    null,
                    _selectedKind == null,
                  );
                }
                final idx = i - 1;
                return _chip(
                  _kindNames[idx],
                  _kinds[idx],
                  _kindIcons[idx],
                  _selectedKind == _kinds[idx],
                );
              },
            ),
          ),
          Expanded(
            child: _isLoading
                ? const Center(
                    child: CircularProgressIndicator(
                      color: Color(0xFFB78628),
                    ),
                  )
                : _items.isEmpty
                    ? Center(
                        child: Text(
                          _s('gov_empty'),
                          style: const TextStyle(color: Colors.white60),
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _items.length,
                        itemBuilder: (_, i) {
                          final item = _items[i];
                          final kindStr = item['kind'] as String? ?? '';
                          final kindIdx = _kinds.indexOf(kindStr);
                          return Container(
                            margin: const EdgeInsets.only(bottom: 12),
                            padding: const EdgeInsets.all(16),
                            decoration: BoxDecoration(
                              color: Colors.white.withValues(alpha: 0.08),
                              borderRadius: BorderRadius.circular(16),
                              border: Border.all(
                                color: Colors.white.withValues(alpha: 0.08),
                              ),
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  children: [
                                    if (kindIdx >= 0) ...[
                                      Icon(
                                        _kindIcons[kindIdx],
                                        color: const Color(0xFFB78628),
                                        size: 16,
                                      ),
                                      const SizedBox(width: 6),
                                    ],
                                    Text(
                                      kindIdx >= 0
                                          ? _kindNames[kindIdx]
                                          : kindStr,
                                      style: const TextStyle(
                                        color: Color(0xFFB78628),
                                        fontSize: 12,
                                      ),
                                    ),
                                    if (item['effective_date'] != null) ...[
                                      const Spacer(),
                                      Text(
                                        item['effective_date'] as String,
                                        style: const TextStyle(
                                          color: Colors.white38,
                                          fontSize: 11,
                                        ),
                                      ),
                                    ],
                                  ],
                                ),
                                const SizedBox(height: 8),
                                Text(
                                  item['title'] as String? ?? '',
                                  style: const TextStyle(
                                    color: Colors.white,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                                if (item['body_md'] != null) ...[
                                  const SizedBox(height: 4),
                                  Text(
                                    item['body_md'] as String,
                                    style: const TextStyle(
                                      color: Colors.white70,
                                      fontSize: 13,
                                    ),
                                  ),
                                ],
                              ],
                            ),
                          );
                        },
                      ),
          ),
        ],
      ),
    );
  }
}
