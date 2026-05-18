// Plan returned by /v1/billing/plans. `pricingZone` is resolved server-side
// from the device country; we just render whatever the API returns.

import "package:freezed_annotation/freezed_annotation.dart";

part "subscription_plan.freezed.dart";

enum PlanInterval { month, year, lifetime }

@freezed
class SubscriptionPlan with _$SubscriptionPlan {
  const factory SubscriptionPlan({
    required String slug,
    required String name,
    required PlanInterval interval,
    required int amountMinor,
    required String currency,
    required String pricingZone,
    @Default(<String>[]) List<String> features,
    @Default(false) bool isFree,
    @Default(false) bool isHighlighted,
  }) = _SubscriptionPlan;

  const SubscriptionPlan._();

  /// Returns the price as a major-unit double — e.g. minor = 4900 + ccy = USD
  /// produces 49.00.
  double get amountMajor => amountMinor / 100.0;
}
