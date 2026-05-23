import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/profile/follow_button.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('FollowButton shows Follow text when not following', (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(const FollowButton(pubId: 'test-user')),
    );
    expect(find.text('Follow'), findsOneWidget);
  });

  testWidgets('FollowButton shows Unfollow text when following', (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const FollowButton(pubId: 'test-user', isFollowing: true),
      ),
    );
    expect(find.text('Unfollow'), findsOneWidget);
  });
}
