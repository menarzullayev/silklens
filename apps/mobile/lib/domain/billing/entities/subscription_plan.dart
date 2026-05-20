class SubscriptionPlan {
  const SubscriptionPlan({
    required this.id,
    required this.slug,
    required this.name,
    required this.billingPeriod,
    required this.trialDays,
    required this.isDefault,
    this.price,
    this.currency = 'USD',
    this.features = const [],
    this.isHighlighted = false,
  });

  factory SubscriptionPlan.fromJson(Map<String, dynamic> j) => SubscriptionPlan(
        id: j['id'] as String,
        slug: j['slug'] as String,
        name: j['slug'] as String,
        billingPeriod: j['billing_period'] as String? ?? 'monthly',
        trialDays: j['trial_days'] as int? ?? 0,
        isDefault: j['is_default'] as bool? ?? false,
        price: (j['price'] as Map?)?['amount'] != null
            ? double.tryParse(j['price']['amount'].toString())
            : null,
        currency: (j['price'] as Map?)?['currency'] as String? ?? 'USD',
      );
  final String id;
  final String slug;
  final String name;
  final String billingPeriod;
  final int trialDays;
  final bool isDefault;
  final double? price;
  final String currency;
  final List<String> features;
  final bool isHighlighted;

  String get interval => billingPeriod;
  bool get isFree => price == null || (price ?? 0) == 0;

  String get amountMajor => price != null ? '${price!.toStringAsFixed(2)} $currency' : 'Free';
}
