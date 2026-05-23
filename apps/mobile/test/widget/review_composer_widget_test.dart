import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/profile/review_composer_sheet.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('ReviewComposerSheet renders without error', (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const ReviewComposerSheet(heritagePubId: 'test-pub-id'),
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
