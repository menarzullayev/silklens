import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/billing/checkout_page.dart';
import 'package:silklens/presentation/providers/billing_provider.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('CheckoutPage renders without error', (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const CheckoutPage(),
        overrides: [
          billingProvider.overrideWith(_StubBillingNotifier.new),
        ],
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}

class _StubBillingNotifier extends BillingNotifier {
  @override
  BillingState build() => const BillingState(isLoading: false);
}
