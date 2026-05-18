// Result of a /v1/media/uploads call — server returns the media_asset_id we
// then pass into AI recognition. We also surface the storage URL so a caller
// can render the preview straight from the CDN if needed.

import "package:freezed_annotation/freezed_annotation.dart";

part "media_upload.freezed.dart";

@freezed
class MediaUpload with _$MediaUpload {
  const factory MediaUpload({
    required String mediaAssetId,
    String? signedUrl,
    int? sizeBytes,
    String? mimeType,
  }) = _MediaUpload;
}
