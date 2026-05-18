import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/social_repository_impl.dart";
import "package:silklens/domain/social/entities/user_profile.dart";
import "package:silklens/domain/social/repositories/social_repository.dart";
import "package:silklens/presentation/pages/profile/follow_button.dart";

import "test_helpers.dart";

class _Repo extends Mock implements SocialRepository {}

void main() {
  testWidgets("FollowButton renders Follow when not following",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.getUser(any()))
        .thenAnswer((_) async => const Success<UserProfile>(
              UserProfile(
                pubId: "u-1",
                displayName: "Alice",
              ),
            ));

    await tester.pumpWidget(
      wrapForWidgetTest(
        const FollowButton(userPubId: "u-1"),
        overrides: <Override>[
          socialRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );
    await tester.pumpAndSettle();

    expect(find.byKey(const Key("follow_button.u-1")), findsOneWidget);
    expect(find.text("Follow"), findsOneWidget);
  });

  testWidgets("FollowButton renders Following when already following",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.getUser(any()))
        .thenAnswer((_) async => const Success<UserProfile>(
              UserProfile(
                pubId: "u-2",
                displayName: "Bob",
                isFollowing: true,
              ),
            ));

    await tester.pumpWidget(
      wrapForWidgetTest(
        const FollowButton(userPubId: "u-2"),
        overrides: <Override>[
          socialRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text("Following"), findsOneWidget);
  });
}
