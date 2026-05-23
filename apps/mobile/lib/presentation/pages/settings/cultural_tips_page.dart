import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class CulturalTipsPage extends HookConsumerWidget {
  const CulturalTipsPage({super.key});

  String _s(String key) =>
      AppStrings.get(LocaleService.instance.locale, key);

  static const _contextKeys = <String?>[
    null,
    'general',
    'mosque',
    'bazaar',
    'restaurant',
    'home_visit',
  ];

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    useEffect(() {
      SystemChrome.setSystemUIOverlayStyle(
        const SystemUiOverlayStyle(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.light,
          systemNavigationBarColor: Color(0xFF0D2337),
          systemNavigationBarIconBrightness: Brightness.light,
        ),
      );
      return null;
    }, const []);

    final locale = ref.watch(activeLocaleProvider);
    final selectedCtx = useState<String?>(null);
    final tips = useState<List<dynamic>>([]);
    final isLoading = useState(true);

    useEffect(() {
      isLoading.value = true;
      Future(() async {
        try {
          final client = ref.read(silkLensApiClientProvider);
          tips.value = await client.getCulturalTips(
            countryCode: 'UZ',
            language: locale.languageCode,
            tipContext: selectedCtx.value,
          );
        } catch (_) {}
        isLoading.value = false;
      });
      return null;
    }, [selectedCtx.value, locale.languageCode]);

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: GestureDetector(
          onTap: () => Navigator.of(context).pop(),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: Text(
          _s('ctips_title'),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: Column(
        children: [
          // Context filter strip
          SizedBox(
            height: 52,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              itemCount: _contextKeys.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) {
                final ctx = _contextKeys[i];
                final label = ctx == null
                    ? _s('ctips_filter_all')
                    : _s('ctips_filter_$ctx');
                final isSelected = selectedCtx.value == ctx;
                return ChoiceChip(
                  label: Text(label),
                  selected: isSelected,
                  onSelected: (_) => selectedCtx.value = ctx,
                  selectedColor: const Color(0xFFB78628),
                  backgroundColor: Colors.white.withValues(alpha: 0.1),
                  labelStyle: TextStyle(
                    color: isSelected ? Colors.black : Colors.white,
                    fontSize: 13,
                  ),
                  side: BorderSide(
                    color: isSelected
                        ? const Color(0xFFB78628)
                        : Colors.white24,
                  ),
                );
              },
            ),
          ),
          // Tips list
          Expanded(
            child: isLoading.value
                ? const Center(
                    child: CircularProgressIndicator(
                      color: Color(0xFFB78628),
                    ),
                  )
                : tips.value.isEmpty
                    ? Center(
                        child: Text(
                          _s('ctips_empty'),
                          style: const TextStyle(color: Colors.white54),
                        ),
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
                        itemCount: tips.value.length,
                        itemBuilder: (_, i) {
                          final tip =
                              tips.value[i] as Map<String, dynamic>;
                          return _TipCard(tip: tip);
                        },
                      ),
          ),
        ],
      ),
    );
  }
}

class _TipCard extends StatelessWidget {
  const _TipCard({required this.tip});
  final Map<String, dynamic> tip;

  static Color _colorForSeverity(String severity) => switch (severity) {
        'critical' => Colors.red,
        'warning' => Colors.orange,
        _ => Colors.blue,
      };

  @override
  Widget build(BuildContext context) {
    final severity = tip['severity'] as String? ?? 'info';
    final color = _colorForSeverity(severity);
    final title = tip['title'] as String? ?? '';
    final body = tip['body_md'] as String? ?? '';

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color.withValues(alpha: 0.3)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(
                severity == 'critical'
                    ? Icons.error_outline
                    : severity == 'warning'
                        ? Icons.warning_amber_outlined
                        : Icons.info_outline,
                color: color,
                size: 18,
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  title,
                  style: TextStyle(
                    color: color,
                    fontWeight: FontWeight.bold,
                    fontSize: 14,
                  ),
                ),
              ),
            ],
          ),
          if (body.isNotEmpty) ...[
            const SizedBox(height: 6),
            Text(
              body,
              style: const TextStyle(color: Colors.white70, fontSize: 13),
            ),
          ],
        ],
      ),
    );
  }
}
