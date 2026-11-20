import 'package:silklens/core/utils/result.dart';
import 'package:silklens/domain/heritage/entities/heritage.dart';
import 'package:silklens/domain/media/entities/media_capture.dart';

/// Camera → Vision pipeline (FAZA 2 deliverable). Placeholder signature only.
abstract interface class VisionRepository {
  /// Identify the heritage item in the given capture. Returns a ranked list,
  /// most-likely first.
  Future<Result<List<Heritage>>> identify(MediaCapture capture);
}
