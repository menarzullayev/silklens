import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/social_repository_impl.dart";
import "package:silklens/domain/social/entities/feed_item.dart";
import "package:silklens/domain/social/entities/review_dimensions.dart";
import "package:silklens/domain/social/entities/user_profile.dart";
import "package:silklens/domain/social/repositories/social_repository.dart";
import "package:silklens/presentation/pages/profile/review_composer_sheet.dart";

import "test_helpers.dart";

class _Repo extends Mock implements SocialRepository {}

class _FakeDraft extends Fake implements ReviewDraft {}

void main() {
  setUpAll(() => registerFallbackValue(_FakeDraft()));

  testWidgets("Tapping stars and submit fires SocialRepository.submitReview",
      (WidgetTester tester) async {
    final repo = _Repo();
    when(() => repo.submitReview(any())).thenAnswer(
      (_) async => const Success<void>(null),
    );
    when(() => repo.feed(
          page: any(named: "page"),
          pageSize: any(named: "pageSize"),
        )).thenAnswer((_) async => const Success<List<FeedItem>>(<FeedItem>[]));
    when(() => repo.getUser(any()))
        .thenAnswer((_) async => const Success<UserProfile>(
              UserProfile(pubId: "me", displayName: "Me"),
            ));

    await tester.pumpWidget(
      wrapForWidgetTest(
        const ReviewComposerSheet(heritagePubId: "h-1"),
        overrides: <Override>[
          socialRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );

    await tester.tap(find.byKey(const Key("review_composer.history.4")));
    await tester.tap(find.byKey(const Key("review_composer.photos.5")));
    await tester.enterText(
      find.byKey(const Key("review_composer.body")),
      "Stunning",
    );
    await tester.tap(find.byKey(const Key("review_composer.submit")));
    await tester.pumpAndSettle();

    verify(() => repo.submitReview(any())).called(1);
  });
}
