// Current subscription state from /v1/billing/me/subscription.

import "package:freezed_annotation/freezed_annotation.dart";

part "subscription.freezed.dart";

enum SubscriptionStatus {
  active,
  trialing,
  pastDue,
  canceled,
  paused,
  none,
}

@freezed
class Subscription with _$Subscription {
  const factory Subscription({
    required SubscriptionStatus status,
    required String planSlug,
    String? planName,
    DateTime? currentPeriodStart,
    DateTime? currentPeriodEnd,
    DateTime? cancelAt,
    @Default(false) bool cancelAtPeriodEnd,
  }) = _Subscription;

  const Subscription._();

  bool get isActive =>
      status == SubscriptionStatus.active ||
      status == SubscriptionStatus.trialing;
}
