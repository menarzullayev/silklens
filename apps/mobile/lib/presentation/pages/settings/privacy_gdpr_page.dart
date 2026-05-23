import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

class PrivacyGDPRPage extends ConsumerStatefulWidget {
  const PrivacyGDPRPage({super.key});

  @override
  ConsumerState<PrivacyGDPRPage> createState() => _PrivacyGDPRPageState();
}

class _PrivacyGDPRPageState extends ConsumerState<PrivacyGDPRPage> {
  bool _locationData = true;
  bool _analytics = false;
  bool _marketing = false;
  bool _exportLoading = false;

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
  }

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  Future<void> _requestDataExport() async {
    setState(() => _exportLoading = true);
    try {
      final client = ref.read(silkLensApiClientProvider);
      final result = await client.requestDataExport();
      if (!mounted) return;
      final requestId = result['request_id'] as String? ??
          result['id'] as String? ??
          '';
      _showExportDialog(requestId);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_s('privacy_export_error')),
          backgroundColor: const Color(0xFFFF3B30),
        ),
      );
    } finally {
      if (mounted) setState(() => _exportLoading = false);
    }
  }

  void _showExportDialog(String requestId) {
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF1A3A5C),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: Row(
          children: [
            const Icon(Icons.check_circle_outline,
                color: Color(0xFFB78628), size: 22),
            const SizedBox(width: 8),
            Text(
              _s('privacy_export_title'),
              style: const TextStyle(color: Colors.white, fontSize: 16),
            ),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _s('privacy_export_body'),
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.8),
                fontSize: 13,
                height: 1.5,
              ),
            ),
            if (requestId.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(
                '${_s('privacy_export_id')}: $requestId',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.5),
                  fontSize: 11,
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: Text(
              _s('privacy_export_btn_close'),
              style: const TextStyle(color: Color(0xFFB78628)),
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        leading: GestureDetector(
          onTap: () => context.pop(),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: const Text(
          'Maxfiylik',
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // GDPR rights info card
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: const Color(0xFF1F3A93).withValues(alpha: 0.25),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: const Color(0xFF1F3A93).withValues(alpha: 0.5),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Row(
                    children: [
                      Icon(
                        Icons.shield_outlined,
                        color: Color(0xFFB78628),
                        size: 20,
                      ),
                      SizedBox(width: 8),
                      Text(
                        'Huquqlaringiz himoyalangan',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'EU GDPR (2016/679) va O\'zbekiston "Shaxsiy ma\'lumotlar '
                    'to\'g\'risida"gi qonuni (2019) asosida sizning '
                    "ma'lumotlaringizni ko'rish, tahrirlash, yuklab olish "
                    "va o'chirish huquqingiz mavjud.",
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.7),
                      fontSize: 12,
                      height: 1.5,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // MA'LUMOTLAR section
            const _SectionLabel("MA'LUMOTLAR"),
            _ActionRow(
              icon: Icons.download_outlined,
              label: "Ma'lumotlarni yuklab olish",
              isGold: true,
              loading: _exportLoading,
              onTap: _exportLoading ? null : () => _requestDataExport(),
            ),
            _ActionRow(
              icon: Icons.edit_outlined,
              label: "Ma'lumotlarni tahrirlash",
              onTap: () {},
            ),
            const SizedBox(height: 16),

            // ULASHISH section
            const _SectionLabel('ULASHISH'),
            _ToggleRow(
              icon: Icons.location_on_outlined,
              label: "Joylashuv ma'lumotlari",
              subtitle: 'Xarita va yaqin joylar uchun',
              value: _locationData,
              onChanged: (v) => setState(() => _locationData = v),
            ),
            _ToggleRow(
              icon: Icons.bar_chart_outlined,
              label: 'Analitika',
              subtitle: 'Ilovani yaxshilashga yordam beradi',
              value: _analytics,
              onChanged: (v) => setState(() => _analytics = v),
            ),
            _ToggleRow(
              icon: Icons.campaign_outlined,
              label: 'Marketing',
              subtitle: 'Maqsadli reklamalar',
              value: _marketing,
              onChanged: (v) => setState(() => _marketing = v),
            ),
            const SizedBox(height: 16),

            // HUJJATLAR section
            const _SectionLabel('HUJJATLAR'),
            _LinkRow(
              icon: Icons.description_outlined,
              label: 'Foydalanish shartlari',
              onTap: () {},
            ),
            _LinkRow(
              icon: Icons.privacy_tip_outlined,
              label: 'Maxfiylik siyosati',
              onTap: () {},
            ),
            _LinkRow(
              icon: Icons.cookie_outlined,
              label: 'Cookie siyosati',
              onTap: () {},
            ),
            const SizedBox(height: 24),

            // Danger
            GestureDetector(
              onTap: () => context.go('/settings/delete-account'),
              child: Container(
                width: double.infinity,
                padding: const EdgeInsets.symmetric(vertical: 14),
                decoration: BoxDecoration(
                  color: const Color(0xFFFF3B30).withValues(alpha: 0.08),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(
                    color: const Color(0xFFFF3B30).withValues(alpha: 0.4),
                  ),
                ),
                child: const Center(
                  child: Text(
                    "Hisobni o'chirish",
                    style: TextStyle(
                      color: Color(0xFFFF6B6B),
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.title);
  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: Text(
        title,
        style: TextStyle(
          color: Colors.white.withValues(alpha: 0.4),
          fontSize: 11,
          letterSpacing: 1.5,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  const _ActionRow({
    required this.icon,
    required this.label,
    required this.onTap,
    this.isGold = false,
    this.loading = false,
  });

  final IconData icon;
  final String label;
  final VoidCallback? onTap;
  final bool isGold;
  final bool loading;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: isGold
              ? const Color(0xFFB78628).withValues(alpha: 0.12)
              : Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(
            color: isGold
                ? const Color(0xFFB78628).withValues(alpha: 0.4)
                : Colors.white.withValues(alpha: 0.08),
          ),
        ),
        child: Row(
          children: [
            Icon(
              icon,
              color: isGold
                  ? const Color(0xFFB78628)
                  : Colors.white.withValues(alpha: 0.7),
              size: 20,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  color: isGold ? const Color(0xFFB78628) : Colors.white,
                  fontSize: 14,
                  fontWeight: isGold ? FontWeight.w600 : FontWeight.w400,
                ),
              ),
            ),
            if (loading)
              const SizedBox(
                width: 16,
                height: 16,
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  valueColor: AlwaysStoppedAnimation<Color>(Color(0xFFB78628)),
                ),
              )
            else
              Icon(
                Icons.chevron_right,
                color: Colors.white.withValues(alpha: 0.3),
                size: 18,
              ),
          ],
        ),
      ),
    );
  }
}

class _ToggleRow extends StatelessWidget {
  const _ToggleRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.onChanged,
    this.subtitle,
  });

  final IconData icon;
  final String label;
  final String? subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        children: [
          Icon(
            icon,
            color: Colors.white.withValues(alpha: 0.6),
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: const TextStyle(color: Colors.white, fontSize: 14),
                ),
                if (subtitle != null)
                  Text(
                    subtitle!,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.4),
                      fontSize: 11,
                    ),
                  ),
              ],
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeThumbColor: const Color(0xFFB78628),
            activeTrackColor: const Color(0xFFB78628).withValues(alpha: 0.3),
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ],
      ),
    );
  }
}

class _LinkRow extends StatelessWidget {
  const _LinkRow({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        margin: const EdgeInsets.only(bottom: 8),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
        ),
        child: Row(
          children: [
            Icon(
              icon,
              color: Colors.white.withValues(alpha: 0.6),
              size: 20,
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                label,
                style: const TextStyle(color: Colors.white, fontSize: 14),
              ),
            ),
            Icon(
              Icons.open_in_new_rounded,
              color: Colors.white.withValues(alpha: 0.3),
              size: 16,
            ),
          ],
        ),
      ),
    );
  }
}
