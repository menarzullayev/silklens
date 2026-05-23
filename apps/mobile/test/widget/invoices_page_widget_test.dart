import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/billing/invoices_page.dart';
import 'package:silklens/presentation/providers/billing_provider.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('InvoicesPage renders without error when invoice list is empty',
      (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const InvoicesPage(),
        overrides: [
          invoicesProvider
              .overrideWith((ref) async => <Map<String, dynamic>>[]),
        ],
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
