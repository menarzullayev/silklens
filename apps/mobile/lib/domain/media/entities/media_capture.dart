import "package:freezed_annotation/freezed_annotation.dart";

part "media_capture.freezed.dart";

/// A photo or video the user just captured but hasn't uploaded yet.
@freezed
class MediaCapture with _$MediaCapture {
  const factory MediaCapture({
    required String localPath,
    required MediaCaptureKind kind,
    int? widthPx,
    int? heightPx,
    int? durationMs,
    double? latitude,
    double? longitude,
    DateTime? capturedAt,
  }) = _MediaCapture;
}

enum MediaCaptureKind { photo, video }
