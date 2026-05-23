import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';

class SocialRepositoryImpl {
  const SocialRepositoryImpl(this._client);

  final SilkLensApiClient _client;

  Future<Map<String, dynamic>> getFeed({
    int limit = 20,
    String? before,
  }) =>
      _client.getSocialFeed(limit: limit, before: before);

  Future<Map<String, dynamic>> getFollowing(
    String pubId, {
    int limit = 30,
  }) =>
      _client.getFollowing(pubId, limit: limit);

  Future<Map<String, dynamic>> getFollowers(
    String pubId, {
    int limit = 30,
  }) =>
      _client.getFollowers(pubId, limit: limit);

  Future<void> follow(String pubId) => _client.followUser(pubId);

  Future<void> unfollow(String pubId) => _client.unfollowUser(pubId);

  Future<Map<String, dynamic>> createInvite({String? message}) =>
      _client.createFriendInvite(message: message);

  Future<Map<String, dynamic>> getNotifications({
    int limit = 30,
    bool unreadOnly = false,
  }) =>
      _client.getNotifications(limit: limit, unreadOnly: unreadOnly);

  Future<void> markRead(String id) => _client.markNotificationRead(id);

  Future<void> markAllRead() => _client.markAllNotificationsRead();
}

final socialRepositoryProvider = Provider<SocialRepositoryImpl>((ref) {
  return SocialRepositoryImpl(ref.watch(silkLensApiClientProvider));
});
