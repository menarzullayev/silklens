import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/billing_repository_impl.dart";
import "package:silklens/domain/billing/entities/subscription.dart";
import "package:silklens/domain/billing/repositories/billing_repository.dart";
import "package:silklens/presentation/pages/billing/checkout_page.dart";

import "test_helpers.dart";

class _Repo extends Mock implements BillingRepository {}

void main() {
  testWidgets("Mock token button populates the token field",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.mySubscription()).thenAnswer(
      (_) async => const Success<Subscription>(
        Subscription(status: SubscriptionStatus.none, planSlug: ""),
      ),
    );

    await tester.pumpWidget(
      wrapForWidgetTest(
        const CheckoutPage(planSlug: "premium-monthly"),
        overrides: <Override>[
          billingRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const Key("billing.checkout.mock")));
    await tester.pumpAndSettle();

    final field = tester.widget<TextField>(
      find.byKey(const Key("billing.checkout.token")),
    );
    expect(field.controller!.text, startsWith("mock_tok_"));
  });
}
