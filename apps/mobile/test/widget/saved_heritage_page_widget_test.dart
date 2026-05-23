import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/heritage/saved_heritage_page.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('SavedHeritagePage renders without error', (tester) async {
    await tester.pumpWidget(wrapForWidgetTest(const SavedHeritagePage()));
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
