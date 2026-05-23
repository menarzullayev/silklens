enum SubscriptionStatus { none, active, trialing, pastDue, canceled, expired, paused }

class Subscription {
  const Subscription({
    required this.id,
    required this.planId,
    required this.planSlug,
    required this.planName,
    required this.status,
    required this.currentPeriodEnd,
    this.trialEndsAt,
    this.cancelAtPeriodEnd = false,
    this.canceledAt,
  });

  factory Subscription.fromJson(Map<String, dynamic> j) => Subscription(
        id: j['id'] as String,
        planId: j['plan_id'] as String? ?? '',
        planSlug: j['plan_slug'] as String? ?? '',
        planName: j['plan_slug'] as String? ?? '',
        status: j['status'] as String,
        currentPeriodEnd: DateTime.parse(j['current_period_end'] as String),
        trialEndsAt:
            j['trial_ends_at'] != null ? DateTime.parse(j['trial_ends_at'] as String) : null,
        cancelAtPeriodEnd: j['cancel_at_period_end'] as bool? ?? false,
        canceledAt: j['canceled_at'] != null ? DateTime.parse(j['canceled_at'] as String) : null,
      );
  final String id;
  final String planId;
  final String planSlug;
  final String planName;
  final String status;
  final DateTime currentPeriodEnd;
  final DateTime? trialEndsAt;
  final bool cancelAtPeriodEnd;
  final DateTime? canceledAt;

  bool get isActive => status == 'active' || status == 'trial';
}
