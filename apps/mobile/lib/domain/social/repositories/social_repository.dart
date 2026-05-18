// Social graph + feed contract — wraps backend endpoints under /v1/social/*.
// The presentation layer talks exclusively to this interface (never to Dio).

import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/social/entities/feed_item.dart";
import "package:silklens/domain/social/entities/review_dimensions.dart";
import "package:silklens/domain/social/entities/user_profile.dart";

abstract interface class SocialRepository {
  Future<Result<List<FeedItem>>> feed({int page = 1, int pageSize = 20});

  Future<Result<UserProfile>> getUser(String pubId);

  Future<Result<List<UserProfile>>> following(String pubId);

  Future<Result<void>> follow(String pubId);

  Future<Result<void>> unfollow(String pubId);

  Future<Result<void>> inviteFriend({
    required String channel,
    required String contact,
  });

  Future<Result<void>> submitReview(ReviewDraft draft);
}
