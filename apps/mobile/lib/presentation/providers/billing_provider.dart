// Billing state: plans / subscription / invoices.

import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/billing_repository_impl.dart";
import "package:silklens/domain/billing/entities/invoice.dart";
import "package:silklens/domain/billing/entities/subscription.dart";
import "package:silklens/domain/billing/entities/subscription_plan.dart";
import "package:silklens/domain/billing/repositories/billing_repository.dart";
import "package:uuid/uuid.dart";

class PlansController extends AsyncNotifier<List<SubscriptionPlan>> {
  @override
  Future<List<SubscriptionPlan>> build() async {
    final repo = ref.read(billingRepositoryProvider);
    final result = await repo.plans();
    return result.successOrNull ?? const <SubscriptionPlan>[];
  }
}

final AsyncNotifierProvider<PlansController, List<SubscriptionPlan>>
    plansProvider =
    AsyncNotifierProvider<PlansController, List<SubscriptionPlan>>(
  PlansController.new,
  name: "plansProvider",
);

class MySubscriptionController extends AsyncNotifier<Subscription?> {
  @override
  Future<Subscription?> build() async {
    final repo = ref.read(billingRepositoryProvider);
    final result = await repo.mySubscription();
    return result.successOrNull;
  }

  Future<Result<Subscription>> startCheckout({
    required String planSlug,
    required String paymentMethodToken,
  }) async {
    final repo = ref.read(billingRepositoryProvider);
    final idem = const Uuid().v4();
    final result = await repo.startSubscription(
      planSlug: planSlug,
      paymentMethodToken: paymentMethodToken,
      idempotencyKey: idem,
    );
    if (result.isSuccess) {
      state = AsyncValue<Subscription?>.data(result.successOrNull);
    } else {
      final Failure f = result.failureOrNull!;
      state = AsyncValue<Subscription?>.error(f, f.stackTrace ?? StackTrace.current);
    }
    return result;
  }

  Future<void> cancel() async {
    final repo = ref.read(billingRepositoryProvider);
    final result = await repo.cancelSubscription();
    if (result.isSuccess) {
      state = AsyncValue<Subscription?>.data(result.successOrNull);
    }
  }

  Future<void> resume() async {
    final repo = ref.read(billingRepositoryProvider);
    final result = await repo.resumeSubscription();
    if (result.isSuccess) {
      state = AsyncValue<Subscription?>.data(result.successOrNull);
    }
  }
}

final AsyncNotifierProvider<MySubscriptionController, Subscription?>
    mySubscriptionProvider =
    AsyncNotifierProvider<MySubscriptionController, Subscription?>(
  MySubscriptionController.new,
  name: "mySubscriptionProvider",
);

class InvoicesController extends AsyncNotifier<List<Invoice>> {
  @override
  Future<List<Invoice>> build() async {
    final repo = ref.read(billingRepositoryProvider);
    final result = await repo.invoices();
    return result.successOrNull ?? const <Invoice>[];
  }
}

final AsyncNotifierProvider<InvoicesController, List<Invoice>> invoicesProvider =
    AsyncNotifierProvider<InvoicesController, List<Invoice>>(
  InvoicesController.new,
  name: "invoicesProvider",
);
