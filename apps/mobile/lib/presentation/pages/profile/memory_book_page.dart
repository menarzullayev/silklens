import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

class MemoryBookPage extends ConsumerStatefulWidget {
  const MemoryBookPage({super.key});

  @override
  ConsumerState<MemoryBookPage> createState() => _MemoryBookPageState();
}

class _MemoryBookPageState extends ConsumerState<MemoryBookPage> {
  Map<String, dynamic>? _preview;
  Map<String, dynamic>? _book;
  bool _isLoadingPreview = true;
  bool _isGenerating = false;
  String _selectedFormat = 'json';

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
    _loadPreview();
  }

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  Future<void> _loadPreview() async {
    try {
      final client = ref.read(silkLensApiClientProvider);
      final data = await client.getMemoryBookPreview();
      if (!mounted) return;
      setState(() {
        _preview = data;
        _isLoadingPreview = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _isLoadingPreview = false);
    }
  }

  Future<void> _generateBook() async {
    setState(() => _isGenerating = true);
    try {
      final client = ref.read(silkLensApiClientProvider);
      final data = await client.generateMemoryBook(
        language: LocaleService.instance.locale,
        format: _selectedFormat,
        title: _s('membook_default_title'),
      );
      if (!mounted) return;
      setState(() {
        _book = data;
        _isGenerating = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() => _isGenerating = false);
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_s('membook_generate_error')),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final totalVisits = _preview?['total_visits'] as int? ?? 0;
    final recentVisits = (_preview?['recent_check_ins'] as List?) ?? [];
    final days = _book?['total_days'] as int? ?? 0;
    final sites = _book?['total_sites'] as int? ?? 0;
    final narrative = _book?['narrative'] as String?;

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: Text(
          _s('membook_title'),
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
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (_isLoadingPreview)
            const Center(
              child: CircularProgressIndicator(color: Color(0xFFB78628)),
            )
          else ...[
            // Hero stat banner
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [Color(0xFF1F3A93), Color(0xFF0D2337)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.auto_stories,
                    color: Color(0xFFB78628),
                    size: 48,
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '$totalVisits ${_s('membook_visits_label')}',
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          _s('membook_cta_sub'),
                          style: const TextStyle(color: Colors.white70),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Format selector
            Text(
              _s('membook_format_label'),
              style: const TextStyle(
                color: Colors.white60,
                fontSize: 13,
                letterSpacing: 1.2,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                Expanded(
                  child: _FormatCard(
                    icon: Icons.article,
                    label: _s('membook_format_text'),
                    selected: _selectedFormat == 'json',
                    onTap: () => setState(() => _selectedFormat = 'json'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: _FormatCard(
                    icon: Icons.picture_as_pdf,
                    label: 'PDF',
                    selected: _selectedFormat == 'pdf',
                    onTap: () => setState(() => _selectedFormat = 'pdf'),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 16),

            // Generate button
            SizedBox(
              width: double.infinity,
              height: 52,
              child: ElevatedButton.icon(
                onPressed:
                    totalVisits == 0 || _isGenerating ? null : _generateBook,
                icon: _isGenerating
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Icon(Icons.auto_awesome),
                label: Text(
                  _isGenerating
                      ? _s('membook_generating')
                      : _s('membook_generate_btn'),
                ),
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFB78628),
                  foregroundColor: Colors.white,
                  disabledBackgroundColor:
                      const Color(0xFFB78628).withValues(alpha: 0.4),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                ),
              ),
            ),
          ],

          // Generated book result
          if (_book != null) ...[
            const SizedBox(height: 20),
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
                  Text(
                    _book!['title'] as String? ?? _s('membook_title'),
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '$sites ${_s('membook_sites_unit')} • $days ${_s('membook_days_unit')}',
                    style: const TextStyle(color: Colors.white60),
                  ),
                  if (narrative != null) ...[
                    const SizedBox(height: 12),
                    const Divider(color: Colors.white12),
                    const SizedBox(height: 12),
                    Text(
                      narrative,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 14,
                        height: 1.6,
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],

          // Recent visits preview (only before generation)
          if (recentVisits.isNotEmpty && _book == null) ...[
            const SizedBox(height: 16),
            Text(
              _s('membook_recent_label'),
              style: const TextStyle(
                color: Colors.white60,
                fontSize: 13,
                letterSpacing: 1.2,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 8),
            ...recentVisits.take(5).map((v) {
              final visit = v as Map<String, dynamic>;
              final dateRaw = visit['checked_in_at'] as String?;
              final dateStr = dateRaw != null && dateRaw.length >= 10
                  ? dateRaw.substring(0, 10)
                  : '';
              return ListTile(
                contentPadding: EdgeInsets.zero,
                leading: Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFFB78628).withValues(alpha: 0.15),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.place,
                    color: Color(0xFFB78628),
                    size: 18,
                  ),
                ),
                title: Text(
                  visit['site_name'] as String? ?? '',
                  style: const TextStyle(color: Colors.white),
                ),
                subtitle: Text(
                  dateStr,
                  style: const TextStyle(color: Colors.white38, fontSize: 12),
                ),
              );
            }),
          ],
        ],
      ),
    );
  }
}

class _FormatCard extends StatelessWidget {
  const _FormatCard({
    required this.icon,
    required this.label,
    required this.selected,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: selected
              ? const Color(0xFFB78628).withValues(alpha: 0.2)
              : Colors.white.withValues(alpha: 0.05),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: selected ? const Color(0xFFB78628) : Colors.white24,
          ),
        ),
        child: Column(
          children: [
            Icon(icon, color: const Color(0xFFB78628)),
            const SizedBox(height: 4),
            Text(
              label,
              style: const TextStyle(color: Colors.white, fontSize: 12),
            ),
          ],
        ),
      ),
    );
  }
}
