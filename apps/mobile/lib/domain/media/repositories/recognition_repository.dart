// Recognition + media upload contract. The data layer talks to
// /v1/media/uploads + /v1/ai/recognize behind this interface so the
// presentation layer never imports Dio or http_parser.

import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/media/entities/media_capture.dart";
import "package:silklens/domain/media/entities/media_upload.dart";
import "package:silklens/domain/media/entities/recognition_result.dart";

abstract interface class RecognitionRepository {
  /// Uploads the captured media to the backend storage tier.
  Future<Result<MediaUpload>> uploadMedia(MediaCapture capture);

  /// Calls /v1/ai/recognize with the previously-uploaded asset id.
  Future<Result<RecognitionResult>> recognize({
    required String mediaAssetId,
    required String language,
  });
}
