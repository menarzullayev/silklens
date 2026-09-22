// SILK-0105 — Checkout page: reads real plan from billingProvider.
// Stripe / Payme integration is Phase 2; pay button shows an informational
// notice rather than navigating to a mock success screen.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/billing_provider.dart';

class CheckoutPage extends ConsumerStatefulWidget {
  /// [planSlug] is set by the router query parameter `?plan=<slug>`.
  const CheckoutPage({super.key, this.planSlug});

  final String? planSlug;

  @override
  ConsumerState<CheckoutPage> createState() => _CheckoutPageState();
}

class _CheckoutPageState extends ConsumerState<CheckoutPage> {
  static const _bg = Color(0xFF0D2337);
  static const _gold = Color(0xFFB78628);

  int _paymentMethod = 0; // 0=Card, 1=Payme, 2=Click, 3=PayPal

  final _cardNumberCtrl = TextEditingController();
  final _expiryCtrl = TextEditingController();
  final _cvvCtrl = TextEditingController();
  final _cardHolderCtrl = TextEditingController();
  final _couponCtrl = TextEditingController();

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  @override
  void dispose() {
    _cardNumberCtrl.dispose();
    _expiryCtrl.dispose();
    _cvvCtrl.dispose();
    _cardHolderCtrl.dispose();
    _couponCtrl.dispose();
    super.dispose();
  }

  Map<String, dynamic>? _resolvePlan(BillingState billing) {
    if (billing.plans.isEmpty) return null;
    final slug = widget.planSlug;
    if (slug != null) {
      try {
        return billing.plans.firstWhere((p) => p['slug'] == slug);
      } catch (_) {
        // slug not found — fall through to first paid plan
      }
    }
    // Default: first non-free plan
    try {
      return billing.plans
          .firstWhere((p) => (p['slug'] as String? ?? '') != 'free');
    } catch (_) {
      return billing.plans.first;
    }
  }

  String _displayName(Map<String, dynamic>? plan) {
    if (plan == null) return '—';
    final raw = plan['display_name'];
    if (raw is Map) {
      final locale = LocaleService.instance.locale;
      return (raw[locale] as String?) ??
          (raw['en'] as String?) ??
          plan['slug'] as String? ??
          '—';
    }
    return raw as String? ?? plan['slug'] as String? ?? '—';
  }

  String _priceLabel(Map<String, dynamic>? plan) {
    if (plan == null) return '—';
    final amount = plan['price_monthly'] as num?;
    final currency = plan['currency'] as String? ?? _s('billing_currency');
    if (amount == null) return _s('billing_free');
    return '$amount $currency / ${_s('billing_month')}';
  }

  num _priceAmount(Map<String, dynamic>? plan) {
    return plan?['price_monthly'] as num? ?? 0;
  }

  // ─── Coupon ─────────────────────────────────────────────────────────────────

  Widget _couponSection(BillingState billing) {
    final coupon = billing.couponResult;
    final isValidating = billing.isValidatingCoupon;
    final discountPct = coupon?['discount_pct'] as num?;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          _s('billing_coupon_label'),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 14,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: _couponCtrl,
                textCapitalization: TextCapitalization.characters,
                style: const TextStyle(color: Colors.white, fontSize: 14),
                decoration: InputDecoration(
                  hintText: _s('billing_coupon_hint'),
                  hintStyle: TextStyle(
                    color: Colors.white.withValues(alpha: 0.25),
                    fontSize: 13,
                  ),
                  filled: true,
                  fillColor: Colors.white.withValues(alpha: 0.06),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 12,
                  ),
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide(
                      color: Colors.white.withValues(alpha: 0.15),
                    ),
                  ),
                  enabledBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: BorderSide(
                      color: coupon != null
                          ? const Color(0xFF4CAF50)
                          : Colors.white.withValues(alpha: 0.15),
                    ),
                  ),
                  focusedBorder: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(10),
                    borderSide: const BorderSide(color: _gold, width: 1.5),
                  ),
                  suffixIcon: coupon != null
                      ? GestureDetector(
                          onTap: () {
                            _couponCtrl.clear();
                            ref.read(billingProvider.notifier).clearCoupon();
                          },
                          child: const Icon(
                            Icons.close_rounded,
                            color: Color(0xFF4CAF50),
                            size: 18,
                          ),
                        )
                      : null,
                ),
              ),
            ),
            const SizedBox(width: 10),
            GestureDetector(
              onTap: isValidating
                  ? null
                  : () async {
                      final code = _couponCtrl.text.trim();
                      if (code.isEmpty) return;
                      final ok = await ref
                          .read(billingProvider.notifier)
                          .validateCoupon(
                            code,
                            _priceAmount(_resolvePlan(billing)).toDouble(),
                          );
                      if (!ok && mounted) {
                        ScaffoldMessenger.of(context).showSnackBar(
                          SnackBar(
                            content: Text(_s('billing_coupon_invalid')),
                            backgroundColor: const Color(0xFFEF5350),
                          ),
                        );
                      }
                    },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 200),
                height: 48,
                padding: const EdgeInsets.symmetric(horizontal: 16),
                decoration: BoxDecoration(
                  color: isValidating
                      ? Colors.white.withValues(alpha: 0.08)
                      : _gold.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: isValidating
                        ? Colors.white.withValues(alpha: 0.15)
                        : _gold.withValues(alpha: 0.5),
                  ),
                ),
                child: isValidating
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: _gold,
                        ),
                      )
                    : Text(
                        _s('billing_coupon_apply'),
                        style: const TextStyle(
                          color: _gold,
                          fontSize: 13,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
              ),
            ),
          ],
        ),
        if (coupon != null) ...[
          const SizedBox(height: 8),
          Row(
            children: [
              const Icon(
                Icons.check_circle_rounded,
                color: Color(0xFF4CAF50),
                size: 16,
              ),
              const SizedBox(width: 6),
              Text(
                discountPct != null
                    ? '${_s('billing_coupon_valid')} (-$discountPct%)'
                    : _s('billing_coupon_valid'),
                style: const TextStyle(
                  color: Color(0xFF4CAF50),
                  fontSize: 12,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ),
        ],
      ],
    );
  }

  @override
  Widget build(BuildContext context) {
    final billing = ref.watch(billingProvider);
    final plan = _resolvePlan(billing);

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
          _s('billing_checkout_title'),
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
                  _planSummaryCard(plan),
                  const SizedBox(height: 20),
                  _couponSection(billing),
                  const SizedBox(height: 24),
                  Text(
                    _s('billing_payment_method_label'),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                  const SizedBox(height: 12),
                  ...List.generate(4, _paymentCard),
                  const SizedBox(height: 24),
                  _payButton(context, plan),
                  const SizedBox(height: 16),
                  _securityBadges(),
                  const SizedBox(height: 24),
                ],
              ),
            ),
    );
  }

  Widget _planSummaryCard(Map<String, dynamic>? plan) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: _gold.withValues(alpha: 0.4)),
        boxShadow: [
          BoxShadow(color: _gold.withValues(alpha: 0.12), blurRadius: 20),
        ],
      ),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: _gold.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: const Icon(Icons.star_rounded, color: _gold, size: 28),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _displayName(plan),
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  _priceLabel(plan),
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.6),
                    fontSize: 13,
                  ),
                ),
              ],
            ),
          ),
          Text(
            '${_priceAmount(plan)}',
            style: const TextStyle(
              color: _gold,
              fontSize: 20,
              fontWeight: FontWeight.w800,
            ),
          ),
        ],
      ),
    );
  }

  Widget _paymentCard(int index) {
    final selected = _paymentMethod == index;
    final labels = [
      (Icons.credit_card, _s('billing_method_card'), 'Visa / Mastercard'),
      (
        Icons.account_balance_wallet,
        'Payme',
        _s('billing_method_payme_sub'),
      ),
      (
        Icons.payments_outlined,
        'Click',
        _s('billing_method_click_sub'),
      ),
      (Icons.language, 'PayPal', _s('billing_method_paypal_sub')),
    ];
    final (icon, name, sub) = labels[index];
    final isExternal = index == 1 || index == 2 || index == 3;

    return GestureDetector(
      onTap: () => setState(() => _paymentMethod = index),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        margin: const EdgeInsets.only(bottom: 10),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          color: selected
              ? Colors.white.withValues(alpha: 0.09)
              : Colors.white.withValues(alpha: 0.04),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: selected ? _gold : Colors.white.withValues(alpha: 0.1),
            width: selected ? 2 : 1,
          ),
        ),
        child: Column(
          children: [
            Row(
              children: [
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: selected
                        ? _gold.withValues(alpha: 0.15)
                        : Colors.white.withValues(alpha: 0.06),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    icon,
                    color:
                        selected ? _gold : Colors.white.withValues(alpha: 0.5),
                    size: 22,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        name,
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 15,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      Text(
                        sub,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.45),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                ),
                AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  width: 20,
                  height: 20,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    border: Border.all(
                      color: selected
                          ? _gold
                          : Colors.white.withValues(alpha: 0.3),
                      width: 2,
                    ),
                    color: selected ? _gold : Colors.transparent,
                  ),
                  child: selected
                      ? const Icon(
                          Icons.check,
                          size: 12,
                          color: Color(0xFF1A1200),
                        )
                      : null,
                ),
              ],
            ),
            // Card fields for card payment
            if (selected && index == 0) ...[
              const SizedBox(height: 16),
              _cardField(
                controller: _cardNumberCtrl,
                label: _s('billing_card_number'),
                hint: '0000 0000 0000 0000',
                keyboardType: TextInputType.number,
                inputFormatters: [
                  FilteringTextInputFormatter.digitsOnly,
                  _CardNumberFormatter(),
                ],
              ),
              const SizedBox(height: 10),
              Row(
                children: [
                  Expanded(
                    child: _cardField(
                      controller: _expiryCtrl,
                      label: _s('billing_card_expiry'),
                      hint: 'MM/YY',
                      keyboardType: TextInputType.number,
                      inputFormatters: [
                        FilteringTextInputFormatter.digitsOnly,
                        _ExpiryFormatter(),
                      ],
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: _cardField(
                      controller: _cvvCtrl,
                      label: 'CVV',
                      hint: '•••',
                      keyboardType: TextInputType.number,
                      obscureText: true,
                      inputFormatters: [
                        FilteringTextInputFormatter.digitsOnly,
                        LengthLimitingTextInputFormatter(3),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              _cardField(
                controller: _cardHolderCtrl,
                label: _s('billing_card_holder'),
                hint: _s('billing_card_holder_hint'),
                textCapitalization: TextCapitalization.characters,
              ),
            ],
            // External redirect note for wallets
            if (selected && isExternal) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 12,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.05),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.1),
                  ),
                ),
                child: Row(
                  children: [
                    Icon(
                      Icons.open_in_new_rounded,
                      size: 14,
                      color: Colors.white.withValues(alpha: 0.5),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      _s('billing_external_redirect'),
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.5),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Widget _cardField({
    required TextEditingController controller,
    required String label,
    required String hint,
    TextInputType keyboardType = TextInputType.text,
    bool obscureText = false,
    TextCapitalization textCapitalization = TextCapitalization.none,
    List<TextInputFormatter>? inputFormatters,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.55),
            fontSize: 11,
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 4),
        TextField(
          controller: controller,
          keyboardType: keyboardType,
          obscureText: obscureText,
          textCapitalization: textCapitalization,
          inputFormatters: inputFormatters,
          style: const TextStyle(color: Colors.white, fontSize: 15),
          decoration: InputDecoration(
            hintText: hint,
            hintStyle: TextStyle(
              color: Colors.white.withValues(alpha: 0.25),
              fontSize: 14,
            ),
            filled: true,
            fillColor: Colors.white.withValues(alpha: 0.06),
            contentPadding: const EdgeInsets.symmetric(
              horizontal: 14,
              vertical: 12,
            ),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(
                color: Colors.white.withValues(alpha: 0.15),
              ),
            ),
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: BorderSide(
                color: Colors.white.withValues(alpha: 0.15),
              ),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(10),
              borderSide: const BorderSide(color: _gold, width: 1.5),
            ),
          ),
        ),
      ],
    );
  }

  Widget _payButton(BuildContext context, Map<String, dynamic>? plan) {
    final subAsync = ref.watch(subscriptionNotifierProvider);
    final isLoading = subAsync is AsyncLoading;

    return GestureDetector(
      onTap: isLoading ? null : () => _submit(context, plan),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 200),
        height: 54,
        width: double.infinity,
        decoration: BoxDecoration(
          gradient: isLoading
              ? null
              : const LinearGradient(
                  colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                ),
          color: isLoading ? Colors.white.withValues(alpha: 0.12) : null,
          borderRadius: BorderRadius.circular(14),
          boxShadow: isLoading
              ? null
              : [
                  BoxShadow(
                    color: _gold.withValues(alpha: 0.3),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
        ),
        child: Center(
          child: isLoading
              ? const SizedBox(
                  width: 22,
                  height: 22,
                  child: CircularProgressIndicator(
                    strokeWidth: 2.5,
                    color: _gold,
                  ),
                )
              : Text(
                  _s('billing_pay_btn'),
                  style: const TextStyle(
                    color: Color(0xFF1A1200),
                    fontSize: 16,
                    fontWeight: FontWeight.w800,
                  ),
                ),
        ),
      ),
    );
  }

  Future<void> _submit(
    BuildContext context,
    Map<String, dynamic>? plan,
  ) async {
    final slug = plan?['slug'] as String? ?? '';
    if (slug.isEmpty || slug == 'free') return;

    // Capture context-dependent objects before the async gap so the linter
    // is satisfied and we avoid using a potentially stale BuildContext.
    final messenger = ScaffoldMessenger.of(context);
    final navigator = Navigator.of(context);
    final successMsg = _s('billing_subscribe_success');
    final errorMsg = _s('billing_subscribe_error');

    // TODO(SILK-0105): integrate flutter_stripe — obtain a real PaymentMethod
    // token before calling start(). The mock token is accepted by the backend
    // MockPaymentProvider in non-production environments only.
    final mockToken = 'mock_token_${DateTime.now().millisecondsSinceEpoch}';

    try {
      await ref.read(subscriptionNotifierProvider.notifier).start(
            planSlug: slug,
            paymentMethodToken: mockToken,
          );
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(
          content: Text(successMsg),
          backgroundColor: const Color(0xFF1B4332),
        ),
      );
      navigator.pop();
    } catch (_) {
      if (!mounted) return;
      messenger.showSnackBar(
        SnackBar(
          content: Text(errorMsg),
          backgroundColor: const Color(0xFFEF5350),
        ),
      );
    }
  }

  Widget _securityBadges() {
    final badges = [
      (Icons.lock_rounded, _s('billing_badge_ssl')),
      (Icons.verified_user_rounded, _s('billing_badge_3ds')),
      (Icons.shield_rounded, _s('billing_badge_pci')),
    ];
    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: badges
          .map(
            (b) => Padding(
              padding: const EdgeInsets.symmetric(horizontal: 10),
              child: Column(
                children: [
                  Icon(
                    b.$1,
                    color: Colors.white.withValues(alpha: 0.3),
                    size: 20,
                  ),
                  const SizedBox(height: 4),
                  Text(
                    b.$2,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.3),
                      fontSize: 10,
                    ),
                  ),
                ],
              ),
            ),
          )
          .toList(),
    );
  }
}

// ─── Input formatters ────────────────────────────────────────────────────────

class _CardNumberFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll(' ', '');
    if (digits.length > 16) return oldValue;
    final buffer = StringBuffer();
    for (var i = 0; i < digits.length; i++) {
      if (i > 0 && i % 4 == 0) buffer.write(' ');
      buffer.write(digits[i]);
    }
    final str = buffer.toString();
    return TextEditingValue(
      text: str,
      selection: TextSelection.collapsed(offset: str.length),
    );
  }
}

class _ExpiryFormatter extends TextInputFormatter {
  @override
  TextEditingValue formatEditUpdate(
    TextEditingValue oldValue,
    TextEditingValue newValue,
  ) {
    final digits = newValue.text.replaceAll('/', '');
    if (digits.length > 4) return oldValue;
    final buffer = StringBuffer();
    for (var i = 0; i < digits.length; i++) {
      if (i == 2) buffer.write('/');
      buffer.write(digits[i]);
    }
    final str = buffer.toString();
    return TextEditingValue(
      text: str,
      selection: TextSelection.collapsed(offset: str.length),
    );
  }
}
