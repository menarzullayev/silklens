import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/billing_repository_impl.dart";
import "package:silklens/domain/billing/entities/subscription.dart";
import "package:silklens/domain/billing/repositories/billing_repository.dart";
import "package:silklens/presentation/pages/billing/manage_subscription_page.dart";

import "test_helpers.dart";

class _Repo extends Mock implements BillingRepository {}

void main() {
  testWidgets("ManageSubscriptionPage shows empty state when no sub",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.mySubscription()).thenAnswer(
      (_) async => const Success<Subscription>(
        Subscription(
          status: SubscriptionStatus.none,
          planSlug: "",
        ),
      ),
    );
    await tester.pumpWidget(
      wrapForWidgetTest(
        const ManageSubscriptionPage(),
        overrides: <Override>[
          billingRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key("billing.manage.empty")), findsOneWidget);
  });

  testWidgets("ManageSubscriptionPage shows cancel button when active",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.mySubscription()).thenAnswer(
      (_) async => Success<Subscription>(
        Subscription(
          status: SubscriptionStatus.active,
          planSlug: "premium-monthly",
          planName: "Premium Monthly",
          currentPeriodEnd: DateTime.utc(2026, 12, 31),
        ),
      ),
    );
    await tester.pumpWidget(
      wrapForWidgetTest(
        const ManageSubscriptionPage(),
        overrides: <Override>[
          billingRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key("billing.manage.cancel")), findsOneWidget);
    expect(find.text("Premium Monthly"), findsOneWidget);
  });
}
