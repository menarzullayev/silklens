import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class SettingsHomePage extends StatelessWidget {
  const SettingsHomePage({super.key});

  static const _gold = Color(0xFFB78628);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        leading: GestureDetector(
          onTap: () => context.pop(),
          child: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 20),
        ),
        title: const Text(
          'Sozlamalar',
          style: TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Profile header
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 52,
                    height: 52,
                    decoration: const BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: LinearGradient(
                        colors: [Color(0xFFB78628), Color(0xFF1F3A93)],
                      ),
                    ),
                    child: const Center(
                      child: Text(
                        'A',
                        style: TextStyle(
                            color: Colors.white, fontSize: 22, fontWeight: FontWeight.w700,),
                      ),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Aziz Karimov',
                          style: TextStyle(
                              color: Colors.white, fontSize: 16, fontWeight: FontWeight.w600,),
                        ),
                        Text(
                          'aziz@email.com',
                          style:
                              TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 12),
                        ),
                      ],
                    ),
                  ),
                  const Icon(Icons.chevron_right, color: Colors.white38),
                ],
              ),
            ),
            const SizedBox(height: 24),

            const _SectionHeader('HISOB'),
            _SettingsRow(
              icon: Icons.language_rounded,
              label: 'Til',
              subtitle: "O'zbek",
              onTap: () => context.go('/settings/language'),
            ),
            _SettingsRow(
              icon: Icons.notifications_outlined,
              label: 'Bildirishnomalar',
              onTap: () => context.go('/settings/notifications'),
            ),
            _SettingsRow(
              icon: Icons.lock_outline_rounded,
              label: 'Maxfiylik',
              onTap: () => context.go('/settings/privacy'),
            ),
            const SizedBox(height: 16),

            const _SectionHeader('OBUNA'),
            _SettingsRow(
              icon: Icons.workspace_premium_rounded,
              label: 'Mening rejam',
              subtitle: 'Explorer ⭐',
              iconColor: _gold,
              onTap: () => context.go('/billing'),
            ),
            _SettingsRow(
              icon: Icons.receipt_long_outlined,
              label: "To'lov tarixi",
              onTap: () => context.go('/billing/invoices'),
            ),
            _SettingsRow(
              icon: Icons.confirmation_number_outlined,
              label: 'Mening chiptalarim',
              onTap: () => context.go('/billing/tickets'),
            ),
            const SizedBox(height: 16),

            const _SectionHeader('SAYOHAT'),
            _SettingsRow(
              icon: Icons.route_outlined,
              label: 'Sayohat Rejalash',
              onTap: () => context.go('/trips'),
            ),
            _SettingsRow(
              icon: Icons.restaurant_outlined,
              label: 'Ovqat Gidi',
              onTap: () => context.go('/food-guide'),
            ),
            _SettingsRow(
              icon: Icons.account_balance_wallet_outlined,
              label: 'Xarajatlar',
              onTap: () => context.go('/expenses'),
            ),
            _SettingsRow(
              icon: Icons.eco_outlined,
              label: 'Karbon Izi',
              onTap: () => context.go('/carbon'),
            ),
            _SettingsRow(
              icon: Icons.mood_outlined,
              label: 'Kayfiyat Sayohati',
              onTap: () => context.go('/mood'),
            ),
            _SettingsRow(
              icon: Icons.wb_sunny_outlined,
              label: 'Ob-havo Gidi',
              onTap: () => context.go('/weather'),
            ),
            _SettingsRow(
              icon: Icons.auto_stories_outlined,
              label: 'Sayohat Kundaligi',
              onTap: () => context.go('/memory-book'),
            ),
            _SettingsRow(
              icon: Icons.lightbulb_outline,
              label: 'Madaniy Maslahatlar',
              onTap: () => context.go('/cultural-tips'),
            ),
            _SettingsRow(
              icon: Icons.psychology_outlined,
              label: 'AI Vositalar',
              iconColor: _gold,
              onTap: () => context.go('/ai-utilities'),
            ),
            _SettingsRow(
              icon: Icons.account_balance_outlined,
              label: "Hukumat Ma'lumotlari",
              onTap: () => context.go('/government'),
            ),
            _SettingsRow(
              icon: Icons.emergency_outlined,
              label: 'Favqulodda yordam',
              iconColor: const Color(0xFFE53935),
              onTap: () => context.go('/emergency'),
            ),
            const SizedBox(height: 16),

            const _SectionHeader('YORDAM'),
            _SettingsRow(
              icon: Icons.info_outline_rounded,
              label: 'Ilova haqida',
              onTap: () => context.go('/settings/about'),
            ),
            const SizedBox(height: 16),

            // Danger zone
            _SettingsRow(
              icon: Icons.delete_outline_rounded,
              label: "Hisobni o'chirish",
              iconColor: const Color(0xFFFF6B6B),
              labelColor: const Color(0xFFFF6B6B),
              onTap: () => context.go('/settings/delete-account'),
            ),
            const SizedBox(height: 32),
            Center(
              child: Text(
                'SilkLens v0.3.0-beta',
                style: TextStyle(color: Colors.white.withValues(alpha: 0.3), fontSize: 12),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  const _SectionHeader(this.title);
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

class _SettingsRow extends StatelessWidget {
  const _SettingsRow({
    required this.icon,
    required this.label,
    this.subtitle,
    this.onTap,
    this.iconColor,
    this.labelColor,
  });

  final IconData icon;
  final String label;
  final String? subtitle;
  final VoidCallback? onTap;
  final Color? iconColor;
  final Color? labelColor;

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
            Icon(icon, color: iconColor ?? Colors.white.withValues(alpha: 0.7), size: 20),
            const SizedBox(width: 12),
            Expanded(
              child: Text(label, style: TextStyle(color: labelColor ?? Colors.white, fontSize: 14)),
            ),
            if (subtitle != null)
              Text(subtitle!, style: const TextStyle(color: Color(0xFFB78628), fontSize: 12)),
            const SizedBox(width: 4),
            Icon(Icons.chevron_right, color: Colors.white.withValues(alpha: 0.3), size: 18),
          ],
        ),
      ),
    );
  }
}
