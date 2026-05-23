// SILK-0106 — Manage subscription page wired to billingProvider (real API).

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/billing_provider.dart';

class ManageSubscriptionPage extends ConsumerWidget {
  const ManageSubscriptionPage({super.key});

  static const _bg = Color(0xFF0D2337);
  static const _gold = Color(0xFFB78628);

  String _s(String locale, String key) => AppStrings.get(locale, key);

  String _planDisplayName(Map<String, dynamic>? sub, String locale) {
    if (sub == null) return AppStrings.get(locale, 'billing_plan_free');
    final raw = sub['plan_display_name'] ?? sub['plan_slug'] ?? '';
    if (raw is Map) {
      return (raw[locale] as String?) ??
          (raw['en'] as String?) ??
          sub['plan_slug'] as String? ??
          '';
    }
    return raw as String;
  }

  // Map entitlement slugs to icon + label key + unit key.
  static const _entitlementMeta = <String, (IconData, String, String)>{
    'ai_recognition_daily': (
      Icons.psychology_rounded,
      'billing_stat_ai',
      'billing_unit_times',
    ),
    'tts_monthly': (
      Icons.headphones_rounded,
      'billing_stat_audio',
      'billing_unit_items',
    ),
    'ar_sessions_monthly': (
      Icons.view_in_ar_rounded,
      'billing_stat_ar',
      'billing_unit_times',
    ),
    'storage_mb': (
      Icons.cloud_rounded,
      'billing_stat_storage',
      'billing_unit_mb',
    ),
  };

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locale = LocaleService.instance.locale;
    final billing = ref.watch(billingProvider);

    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: Text(
          _s(locale, 'billing_manage_title'),
          style: const TextStyle(color: Colors.white),
        ),
      ),
      body: billing.isLoading
          ? const Center(child: CircularProgressIndicator(color: _gold))
          : SingleChildScrollView(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _heroPlanCard(billing, locale),
                  const SizedBox(height: 20),
                  Text(
                    _s(locale, 'billing_usage_title'),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 15,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 12),
                  _usageGrid(billing, locale),
                  const SizedBox(height: 20),
                  _paymentMethodRow(context, locale),
                  const SizedBox(height: 20),
                  _actionButtons(context, ref, billing, locale),
                  if (billing.error != null) ...[
                    const SizedBox(height: 12),
                    Text(
                      billing.error!,
                      style: const TextStyle(
                        color: Color(0xFFEF5350),
                        fontSize: 12,
                      ),
                    ),
                  ],
                  const SizedBox(height: 24),
                ],
              ),
            ),
    );
  }

  Widget _heroPlanCard(BillingState billing, String locale) {
    final sub = billing.currentSubscription;
    final planName = _planDisplayName(sub, locale);
    final isActive = billing.hasActiveSubscription;
    final nextPayment = sub?['current_period_end'] as String? ?? '—';
    final startedAt = sub?['current_period_start'] as String? ?? '—';
    final priceAmt = sub?['price_amount'];
    final currency = sub?['currency'] as String? ?? '';
    final priceLabel = priceAmt != null
        ? '$priceAmt $currency / ${_s(locale, 'billing_month')}'
        : _s(locale, 'billing_free');

    return Container(
      padding: const EdgeInsets.all(22),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: _gold.withValues(alpha: 0.55), width: 1.5),
        boxShadow: [
          BoxShadow(color: _gold.withValues(alpha: 0.15), blurRadius: 24),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      planName,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 22,
                        fontWeight: FontWeight.w800,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      '${_s(locale, 'billing_next_payment')}: $nextPayment',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.5),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  gradient: isActive
                      ? const LinearGradient(
                          colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                        )
                      : null,
                  color: isActive ? null : Colors.white.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(10),
                ),
                child: Text(
                  isActive
                      ? _s(locale, 'billing_status_active')
                      : _s(locale, 'billing_status_inactive'),
                  style: TextStyle(
                    color: isActive ? const Color(0xFF1A1200) : Colors.white.withValues(alpha: 0.5),
                    fontSize: 11,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Row(
            children: [
              _planDetail(
                Icons.calendar_today_rounded,
                startedAt,
                _s(locale, 'billing_started'),
              ),
              const SizedBox(width: 20),
              _planDetail(
                Icons.attach_money_rounded,
                priceLabel,
                _s(locale, 'billing_price'),
              ),
              const SizedBox(width: 20),
              _planDetail(
                Icons.loop_rounded,
                _s(locale, 'billing_auto_renew'),
                _s(locale, 'billing_renewal'),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _planDetail(IconData icon, String value, String label) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Icon(icon, size: 13, color: _gold),
            const SizedBox(width: 4),
            Text(
              label,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.45),
                fontSize: 10,
              ),
            ),
          ],
        ),
        const SizedBox(height: 2),
        Text(
          value,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ],
    );
  }

  Widget _usageGrid(BillingState billing, String locale) {
    // Build stats from entitlements when available; fall back to sensible
    // defaults so the grid is never empty.
    final entMap = <String, Map<String, dynamic>>{
      for (final e in billing.entitlements)
        if (e['slug'] is String) e['slug'] as String: e,
    };

    final slugOrder = [
      'ai_recognition_daily',
      'tts_monthly',
      'ar_sessions_monthly',
      'storage_mb',
    ];

    final stats = slugOrder.map((slug) {
      final meta = _entitlementMeta[slug];
      final ent = entMap[slug];
      final icon = meta?.$1 ?? Icons.star_rounded;
      final labelKey = meta?.$2 ?? 'billing_stat_ai';
      final unitKey = meta?.$3 ?? 'billing_unit_times';

      final used = (ent?['used'] as num?)?.toInt() ?? 0;
      final limit = (ent?['limit'] as num?)?.toInt() ?? 0;
      // -1 means unlimited.
      final isUnlimited = limit < 0;

      return (icon, labelKey, unitKey, used, limit, isUnlimited);
    }).toList();

    return GridView.builder(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: stats.length,
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        mainAxisSpacing: 10,
        crossAxisSpacing: 10,
        childAspectRatio: 1.55,
      ),
      itemBuilder: (_, i) {
        final (icon, labelKey, unitKey, used, limit, isUnlimited) = stats[i];
        final pct = (isUnlimited || limit == 0) ? 0.0 : (used / limit).clamp(0.0, 1.0);
        final limitLabel = isUnlimited ? _s(locale, 'billing_unlimited') : limit.toString();
        final unit = _s(locale, unitKey);

        return Container(
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.05),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.white.withValues(alpha: 0.09)),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(icon, color: _gold, size: 16),
                  const SizedBox(width: 6),
                  Text(
                    _s(locale, labelKey),
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.55),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
              const Spacer(),
              Text(
                isUnlimited ? '$used / $limitLabel' : '$used / $limit $unit',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 6),
              ClipRRect(
                borderRadius: BorderRadius.circular(4),
                child: LinearProgressIndicator(
                  value: isUnlimited ? 0.0 : pct,
                  backgroundColor: Colors.white.withValues(alpha: 0.1),
                  valueColor: AlwaysStoppedAnimation<Color>(
                    pct > 0.8 ? const Color(0xFFEF5350) : _gold,
                  ),
                  minHeight: 5,
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  Widget _paymentMethodRow(BuildContext context, String locale) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.09)),
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(8),
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.07),
              borderRadius: BorderRadius.circular(10),
            ),
            child: const Icon(Icons.credit_card, color: _gold, size: 20),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Payment method details come from backend in Phase 2;
                // show a placeholder label until then.
                Text(
                  _s(locale, 'billing_payment_placeholder'),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  _s(locale, 'billing_payment_coming_soon'),
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.4),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          GestureDetector(
            onTap: () => context.go('/billing/checkout'),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 7),
              decoration: BoxDecoration(
                border: Border.all(color: _gold.withValues(alpha: 0.5)),
                borderRadius: BorderRadius.circular(9),
              ),
              child: Text(
                _s(locale, 'billing_change'),
                style: const TextStyle(
                  color: _gold,
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _actionButtons(
    BuildContext context,
    WidgetRef ref,
    BillingState billing,
    String locale,
  ) {
    final pendingCancel = billing.cancelAtPeriodEnd;

    return Column(
      children: [
        GestureDetector(
          onTap: () => context.go('/billing'),
          child: Container(
            height: 52,
            width: double.infinity,
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
              ),
              borderRadius: BorderRadius.circular(14),
              boxShadow: [
                BoxShadow(
                  color: _gold.withValues(alpha: 0.25),
                  blurRadius: 12,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: Center(
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.rocket_launch_rounded,
                    color: Color(0xFF1A1200),
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    _s(locale, 'billing_upgrade_btn'),
                    style: const TextStyle(
                      color: Color(0xFF1A1200),
                      fontSize: 15,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 10),
        // Show resume button when pending cancellation, cancel button otherwise.
        if (pendingCancel)
          GestureDetector(
            onTap: billing.isCancelling
                ? null
                : () async {
                    final ok = await ref.read(billingProvider.notifier).resumeSubscription();
                    if (!ok && context.mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(_s(locale, 'billing_resume_error')),
                          backgroundColor: const Color(0xFFEF5350),
                        ),
                      );
                    }
                  },
            child: Container(
              height: 52,
              width: double.infinity,
              decoration: BoxDecoration(
                color: const Color(0xFF1B4332),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: const Color(0xFF4CAF50).withValues(alpha: 0.5),
                ),
              ),
              child: billing.isCancelling
                  ? const Center(
                      child: SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Color(0xFF4CAF50),
                        ),
                      ),
                    )
                  : Center(
                      child: Text(
                        _s(locale, 'billing_resume_btn'),
                        style: const TextStyle(
                          color: Color(0xFF4CAF50),
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
            ),
          )
        else
          GestureDetector(
            onTap: billing.hasActiveSubscription
                ? () => _showCancelDialog(context, ref, locale)
                : null,
            child: Container(
              height: 52,
              width: double.infinity,
              decoration: BoxDecoration(
                color: const Color(0xFFEF5350).withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: const Color(0xFFEF5350).withValues(
                    alpha: billing.hasActiveSubscription ? 0.35 : 0.15,
                  ),
                ),
              ),
              child: billing.isCancelling
                  ? const Center(
                      child: SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Color(0xFFEF5350),
                        ),
                      ),
                    )
                  : Center(
                      child: Text(
                        _s(locale, 'billing_cancel_btn'),
                        style: TextStyle(
                          color: const Color(0xFFEF5350).withValues(
                            alpha: billing.hasActiveSubscription ? 0.85 : 0.4,
                          ),
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
            ),
          ),
      ],
    );
  }

  void _showCancelDialog(
    BuildContext context,
    WidgetRef ref,
    String locale,
  ) {
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: const Color(0xFF0F2A3D),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Text(
          _s(locale, 'billing_cancel_title'),
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.w700,
          ),
        ),
        content: Text(
          _s(locale, 'billing_cancel_body'),
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.6),
            fontSize: 13,
            height: 1.5,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: Text(
              _s(locale, 'billing_cancel_go_back'),
              style: const TextStyle(
                color: _gold,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          TextButton(
            onPressed: () async {
              Navigator.pop(ctx);
              final ok = await ref.read(billingProvider.notifier).cancelSubscription();
              if (!ok && context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(
                  SnackBar(
                    content: Text(_s(locale, 'billing_cancel_error')),
                    backgroundColor: const Color(0xFFEF5350),
                  ),
                );
              }
            },
            child: Text(
              _s(locale, 'billing_cancel_confirm'),
              style: const TextStyle(
                color: Color(0xFFEF5350),
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
