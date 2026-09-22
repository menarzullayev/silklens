import 'package:silklens/core/utils/result.dart';
import 'package:silklens/domain/social/entities/review.dart';

abstract interface class ReviewRepository {
  Future<Result<List<Review>>> listForHeritage(String heritageId);
  Future<Result<Review>> submit({
    required String heritageId,
    required int rating,
    String? text,
  });
}
