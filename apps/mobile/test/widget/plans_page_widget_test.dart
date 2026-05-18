import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/billing_repository_impl.dart";
import "package:silklens/domain/billing/entities/invoice.dart";
import "package:silklens/domain/billing/entities/subscription.dart";
import "package:silklens/domain/billing/entities/subscription_plan.dart";
import "package:silklens/domain/billing/repositories/billing_repository.dart";
import "package:silklens/presentation/pages/billing/plans_page.dart";

import "test_helpers.dart";

class _Repo extends Mock implements BillingRepository {}

void main() {
  testWidgets("PlansPage renders Premium card with price",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.plans()).thenAnswer(
      (_) async => const Success<List<SubscriptionPlan>>(<SubscriptionPlan>[
        SubscriptionPlan(
          slug: "premium-monthly",
          name: "Premium Monthly",
          interval: PlanInterval.month,
          amountMinor: 499,
          currency: "USD",
          pricingZone: "GLOBAL",
          features: <String>["Audio guides", "Offline maps"],
        ),
      ]),
    );
    when(() => repo.mySubscription())
        .thenAnswer((_) async => const Success<Subscription>(
              Subscription(
                status: SubscriptionStatus.none,
                planSlug: "",
              ),
            ));
    when(() => repo.invoices(
          page: any(named: "page"),
          pageSize: any(named: "pageSize"),
        )).thenAnswer((_) async => const Success<List<Invoice>>(<Invoice>[]));

    await tester.pumpWidget(
      wrapForWidgetTest(
        const PlansPage(),
        overrides: <Override>[
          billingRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );

    await tester.pumpAndSettle();
    expect(find.text("Premium Monthly"), findsOneWidget);
    expect(find.textContaining("USD 4.99"), findsOneWidget);
    expect(find.text("Audio guides"), findsOneWidget);
  });
}
