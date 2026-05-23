import 'package:silklens/core/utils/result.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';
import 'package:silklens/domain/media/entities/media_capture.dart';

/// Camera → Vision pipeline (FAZA 2 deliverable). Placeholder signature only.
// Clean Arch domain interface — kept as abstract for future contract growth.
// ignore: one_member_abstracts
abstract interface class VisionRepository {
  /// Identify the heritage item in the given capture. Returns a ranked list,
  /// most-likely first.
  Future<Result<List<Heritage>>> identify(MediaCapture capture);
}
