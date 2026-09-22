import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/settings/about_page.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('AboutPage renders without error', (tester) async {
    await tester.pumpWidget(wrapForWidgetTest(const AboutPage()));
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
