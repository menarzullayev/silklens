// HTTP-backed implementation of [RecognitionRepository].
//
// /v1/media/uploads is multipart; /v1/ai/recognize is plain JSON. We keep the
// transport details here so the presentation layer never sees FormData /
// MultipartFile. Errors are translated to typed [Failure] subclasses.

import "package:dio/dio.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/api/dio_client.dart";
import "package:silklens/domain/media/entities/media_capture.dart";
import "package:silklens/domain/media/entities/media_upload.dart";
import "package:silklens/domain/media/entities/recognition_result.dart";
import "package:silklens/domain/media/repositories/recognition_repository.dart";

class RecognitionRepositoryImpl implements RecognitionRepository {
  RecognitionRepositoryImpl({required Dio dio}) : _dio = dio;

  final Dio _dio;

  @override
  Future<Result<MediaUpload>> uploadMedia(MediaCapture capture) async {
    try {
      final formData = FormData.fromMap(<String, Object>{
        "kind": capture.kind == MediaCaptureKind.photo ? "photo" : "video",
        "file": await MultipartFile.fromFile(capture.localPath),
        if (capture.latitude != null) "latitude": capture.latitude!,
        if (capture.longitude != null) "longitude": capture.longitude!,
      });

      final response = await _dio.post<Map<String, dynamic>>(
        "/v1/media/uploads",
        data: formData,
        options: Options(
          headers: <String, String>{
            // Override Dio default JSON content-type so the multipart
            // boundary header survives.
            Headers.contentTypeHeader: "multipart/form-data",
          },
        ),
      );

      final body = response.data ?? const <String, dynamic>{};
      final upload = MediaUpload(
        mediaAssetId: body["media_asset_id"] as String? ?? "",
        signedUrl: body["signed_url"] as String?,
        sizeBytes: body["size_bytes"] as int?,
        mimeType: body["mime_type"] as String?,
      );
      if (upload.mediaAssetId.isEmpty) {
        return const FailureResult<MediaUpload>(
          ServerFailure("Upload response missing media_asset_id"),
        );
      }
      return Success<MediaUpload>(upload);
    } on DioException catch (e, st) {
      return FailureResult<MediaUpload>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<RecognitionResult>> recognize({
    required String mediaAssetId,
    required String language,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/v1/ai/recognize",
        data: <String, dynamic>{
          "media_asset_id": mediaAssetId,
          "language": language,
        },
      );
      final body = response.data ?? const <String, dynamic>{};
      final top = _parseCandidate(body["top"] as Map<String, dynamic>?);
      if (top == null) {
        return const FailureResult<RecognitionResult>(
          ServerFailure("Recognition response missing top candidate"),
        );
      }
      final altList = (body["alternatives"] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .map(_parseCandidate)
          .whereType<RecognitionCandidate>()
          .toList(growable: false);

      return Success<RecognitionResult>(
        RecognitionResult(
          requestId: body["request_id"] as String? ?? "",
          topCandidate: top,
          alternatives: altList,
          language: body["language"] as String?,
        ),
      );
    } on DioException catch (e, st) {
      return FailureResult<RecognitionResult>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  RecognitionCandidate? _parseCandidate(Map<String, dynamic>? json) {
    if (json == null) return null;
    final pubId = json["heritage_pub_id"] as String? ?? json["pub_id"] as String?;
    final name = json["name"] as String?;
    final confRaw = json["confidence"];
    final confidence = confRaw is num ? confRaw.toDouble() : 0.0;
    if (pubId == null || pubId.isEmpty || name == null) return null;
    return RecognitionCandidate(
      heritagePubId: pubId,
      name: name,
      confidence: confidence,
      thumbnailUrl: json["thumbnail_url"] as String?,
      country: json["country"] as String?,
      regionLabel: json["region_label"] as String?,
    );
  }
}

final Provider<RecognitionRepository> recognitionRepositoryProvider =
    Provider<RecognitionRepository>(
  (Ref ref) => RecognitionRepositoryImpl(dio: ref.watch(dioProvider)),
  name: "recognitionRepositoryProvider",
);
