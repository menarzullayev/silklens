// User-generated review of a heritage item. CRDT mode for `text` is
// `LWW + optimistic lock` per Master Architecture §8.

import 'package:silklens/domain/social/entities/review_dimensions.dart';

class Review {
  const Review({
    required this.id,
    required this.placeId,
    required this.authorId,
    required this.authorName,
    required this.rating,
    required this.createdAt,
    this.dimensions = const ReviewDimensions(),
    this.text,
    this.photoUrls = const [],
    this.authorAvatarUrl,
    this.isVerified = false,
    this.helpfulCount = 0,
  });

  factory Review.fromJson(Map<String, dynamic> j) => Review(
    id: j['id'] as String,
    placeId: j['place_id'] as String,
    authorId: j['author_id'] as String,
    authorName: j['author_name'] as String,
    rating: (j['rating'] as num).toDouble(),
    createdAt: DateTime.parse(j['created_at'] as String),
    text: j['text'] as String?,
    photoUrls: (j['photo_urls'] as List?)?.cast<String>() ?? [],
    authorAvatarUrl: j['author_avatar_url'] as String?,
    isVerified: j['is_verified'] as bool? ?? false,
    helpfulCount: j['helpful_count'] as int? ?? 0,
  );

  final String id;
  final String placeId;
  final String authorId;
  final String authorName;
  final double rating;
  final DateTime createdAt;
  final ReviewDimensions dimensions;
  final String? text;
  final List<String> photoUrls;
  final String? authorAvatarUrl;
  final bool isVerified;
  final int helpfulCount;
}
