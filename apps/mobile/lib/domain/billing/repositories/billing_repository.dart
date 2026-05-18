// Billing contract — plans, subscriptions, invoices. Talks to /v1/billing/*.

import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/billing/entities/invoice.dart";
import "package:silklens/domain/billing/entities/subscription.dart";
import "package:silklens/domain/billing/entities/subscription_plan.dart";

abstract interface class BillingRepository {
  Future<Result<List<SubscriptionPlan>>> plans();

  Future<Result<Subscription>> mySubscription();

  Future<Result<List<String>>> myEntitlements();

  Future<Result<Subscription>> startSubscription({
    required String planSlug,
    required String paymentMethodToken,
    required String idempotencyKey,
  });

  Future<Result<Subscription>> cancelSubscription();

  Future<Result<Subscription>> resumeSubscription();

  Future<Result<List<Invoice>>> invoices({int page = 1, int pageSize = 20});
}
