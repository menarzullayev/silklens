import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/billing/manage_subscription_page.dart';
import 'package:silklens/presentation/providers/billing_provider.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('ManageSubscriptionPage renders without error', (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const ManageSubscriptionPage(),
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
