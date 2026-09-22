import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/chat/chat_page.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('ChatPage renders without error', (tester) async {
    await tester.pumpWidget(wrapForWidgetTest(const ChatPage()));
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}
