// SILK-0105 — Plans page wired to billingProvider (real API).

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/billing_provider.dart';

class PlansPage extends ConsumerStatefulWidget {
  const PlansPage({super.key});

  @override
  ConsumerState<PlansPage> createState() => _PlansPageState();
}

class _PlansPageState extends ConsumerState<PlansPage> {
  bool _annual = false;
  int _selected = 1; // default to first paid plan
  static const _gold = Color(0xFFB78628);

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  String _planDisplayName(Map<String, dynamic> plan) {
    final raw = plan['display_name'];
    if (raw is Map) {
      return (raw[LocaleService.instance.locale] as String?) ??
          (raw['en'] as String?) ??
          plan['slug'] as String? ??
          '';
    }
    return raw as String? ?? plan['slug'] as String? ?? '';
  }

  String _planDescription(Map<String, dynamic> plan) {
    final raw = plan['description'];
    if (raw is Map) {
      return (raw[LocaleService.instance.locale] as String?) ??
          (raw['en'] as String?) ??
          '';
    }
    return raw as String? ?? '';
  }

  String _planPrice(Map<String, dynamic> plan, bool annual) {
    final slug = plan['slug'] as String? ?? '';
    if (slug == 'free') return _s('billing_free');

    // Prefer structured pricing fields when present.
    final monthlyPrice = plan['price_monthly'] as num?;
    final yearlyPrice = plan['price_yearly'] as num?;
    final currency = plan['currency'] as String? ?? _s('billing_currency');

    if (annual && yearlyPrice != null) {
      return '$yearlyPrice $currency / ${_s('billing_year')}';
    }
    if (monthlyPrice != null) {
      return '$monthlyPrice $currency / ${_s('billing_month')}';
    }
    return _s('billing_free');
  }

  bool get _selectedIsFree {
    final billing = ref.read(billingProvider);
    if (billing.plans.isEmpty) return true;
    final idx = _selected.clamp(0, billing.plans.length - 1);
    return (billing.plans[idx]['slug'] as String? ?? '') == 'free';
  }

  String _selectedSlug(List<Map<String, dynamic>> plans) {
    if (plans.isEmpty) return 'free';
    final idx = _selected.clamp(0, plans.length - 1);
    return plans[idx]['slug'] as String? ?? 'free';
  }

  @override
  Widget build(BuildContext context) {
    final billing = ref.watch(billingProvider);

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: Text(
          _s('billing_plans_title'),
          style: const TextStyle(color: Colors.white),
        ),
      ),
      body: billing.isLoading
          ? const Center(
              child: CircularProgressIndicator(color: _gold),
            )
          : billing.error != null && billing.plans.isEmpty
              ? _errorState(billing.error!)
              : Column(
                  children: [
                    _billingToggle(),
                    Expanded(child: _planList(billing)),
                    _ctaButton(billing),
                  ],
                ),
    );
  }

  Widget _errorState(String error) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            _s('billing_load_error'),
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.6),
              fontSize: 14,
            ),
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 16),
          GestureDetector(
            onTap: () => ref.read(billingProvider.notifier).refresh(),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
              decoration: BoxDecoration(
                color: _gold.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: _gold.withValues(alpha: 0.4)),
              ),
              child: Text(
                _s('billing_retry'),
                style: const TextStyle(
                  color: _gold,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _billingToggle() {
    return Padding(
      padding: const EdgeInsets.all(16),
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.08),
          borderRadius: BorderRadius.circular(24),
          border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
        ),
        child: Row(
          children: [
            Expanded(
              child: GestureDetector(
                onTap: () => setState(() => _annual = false),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  decoration: BoxDecoration(
                    color: !_annual ? _gold : Colors.transparent,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: Center(
                    child: Text(
                      _s('billing_monthly'),
                      style: TextStyle(
                        color:
                            !_annual ? const Color(0xFF1A1200) : Colors.white,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
              ),
            ),
            Expanded(
              child: GestureDetector(
                onTap: () => setState(() => _annual = true),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.symmetric(vertical: 10),
                  decoration: BoxDecoration(
                    color: _annual ? _gold : Colors.transparent,
                    borderRadius: BorderRadius.circular(22),
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        _s('billing_yearly'),
                        style: TextStyle(
                          color:
                              _annual ? const Color(0xFF1A1200) : Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const SizedBox(width: 6),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFF4CAF50),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: const Text(
                          '-40%',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                      ),
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

  Widget _planList(BillingState billing) {
    final plans = billing.plans;
    if (plans.isEmpty) {
      return Center(
        child: Text(
          _s('billing_no_plans'),
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.4),
            fontSize: 14,
          ),
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      itemCount: plans.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (_, i) {
        final plan = plans[i];
        final slug = plan['slug'] as String? ?? '';
        final selected = _selected == i;
        final isCurrent = slug == billing.currentPlanSlug;
        // Mark the second plan as recommended if API doesn't specify.
        final recommended = (plan['recommended'] as bool? ?? false) ||
            (i == 1 && plans.length >= 3);

        return GestureDetector(
          onTap: () => setState(() => _selected = i),
          child: AnimatedContainer(
            duration: const Duration(milliseconds: 200),
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: selected
                  ? Colors.white.withValues(alpha: 0.10)
                  : Colors.white.withValues(alpha: 0.05),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: selected ? _gold : Colors.white.withValues(alpha: 0.12),
                width: selected ? 2 : 1,
              ),
              boxShadow: selected
                  ? [
                      BoxShadow(
                        color: _gold.withValues(alpha: 0.2),
                        blurRadius: 16,
                      ),
                    ]
                  : null,
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Text(
                      _planDisplayName(plan),
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 18,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                    const Spacer(),
                    if (isCurrent)
                      Container(
                        margin: const EdgeInsets.only(right: 8),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          color: const Color(0xFF1B4332),
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          _s('billing_current_plan'),
                          style: const TextStyle(
                            color: Color(0xFF4CAF50),
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                    if (recommended)
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 3,
                        ),
                        decoration: BoxDecoration(
                          color: _gold,
                          borderRadius: BorderRadius.circular(8),
                        ),
                        child: Text(
                          _s('billing_recommended'),
                          style: const TextStyle(
                            color: Color(0xFF1A1200),
                            fontSize: 10,
                            fontWeight: FontWeight.w800,
                          ),
                        ),
                      ),
                  ],
                ),
                const SizedBox(height: 4),
                Text(
                  _planPrice(plan, _annual),
                  style: TextStyle(
                    color: slug == 'free'
                        ? Colors.white.withValues(alpha: 0.5)
                        : _gold,
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  _planDescription(plan),
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.65),
                    fontSize: 12,
                    height: 1.6,
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _ctaButton(BillingState billing) {
    final isFree = _selectedIsFree;
    final slug = _selectedSlug(billing.plans);

    return Padding(
      padding: const EdgeInsets.all(16),
      child: GestureDetector(
        onTap: isFree ? null : () => context.go('/billing/checkout?plan=$slug'),
        child: Container(
          height: 54,
          width: double.infinity,
          decoration: BoxDecoration(
            gradient: isFree
                ? null
                : const LinearGradient(
                    colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                  ),
            color: isFree ? Colors.white.withValues(alpha: 0.2) : null,
            borderRadius: BorderRadius.circular(14),
          ),
          child: Center(
            child: Text(
              isFree ? _s('billing_current_plan') : _s('billing_trial_cta'),
              style: TextStyle(
                color: isFree
                    ? Colors.white.withValues(alpha: 0.5)
                    : const Color(0xFF1A1200),
                fontSize: 16,
                fontWeight: FontWeight.w700,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
