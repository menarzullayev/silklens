import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/billing_repository_impl.dart";
import "package:silklens/domain/billing/entities/invoice.dart";
import "package:silklens/domain/billing/repositories/billing_repository.dart";
import "package:silklens/presentation/pages/billing/invoices_page.dart";

import "test_helpers.dart";

class _Repo extends Mock implements BillingRepository {}

void main() {
  testWidgets("InvoicesPage renders an invoice row",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.invoices(
          page: any(named: "page"),
          pageSize: any(named: "pageSize"),
        )).thenAnswer((_) async => Success<List<Invoice>>(<Invoice>[
          Invoice(
            id: "inv-1",
            status: InvoiceStatus.paid,
            amountMinor: 499,
            currency: "USD",
            issuedAt: DateTime.utc(2026, 5, 1),
          ),
        ]));

    await tester.pumpWidget(
      wrapForWidgetTest(
        const InvoicesPage(),
        overrides: <Override>[
          billingRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key("billing.invoices.list")), findsOneWidget);
    expect(find.textContaining("USD 4.99"), findsOneWidget);
  });

  testWidgets("InvoicesPage shows empty state",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.invoices(
          page: any(named: "page"),
          pageSize: any(named: "pageSize"),
        )).thenAnswer((_) async => const Success<List<Invoice>>(<Invoice>[]));

    await tester.pumpWidget(
      wrapForWidgetTest(
        const InvoicesPage(),
        overrides: <Override>[
          billingRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );
    await tester.pumpAndSettle();
    expect(find.byKey(const Key("billing.invoices.empty")), findsOneWidget);
  });
}
