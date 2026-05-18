import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/presentation/pages/profile/profile_page.dart";

import "test_helpers.dart";

void main() {
  testWidgets("ProfilePage renders five tabs", (WidgetTester tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(const ProfilePage()),
    );
    // 5 tabs: Activity / Saved / Reviews / Friends / Settings.
    expect(find.byType(Tab), findsNWidgets(5));
  });

  testWidgets("Switching to Settings tab shows language tile",
      (WidgetTester tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(const ProfilePage()),
    );
    // Tap Settings tab (last one).
    await tester.tap(find.text("Settings"));
    await tester.pumpAndSettle();
    expect(find.byKey(const Key("profile.settings.list")), findsOneWidget);
  });
}
