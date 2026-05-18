// Result of a /v1/ai/recognize call.
//
// `topCandidate` is the highest-confidence match; `alternatives` ranks the
// next best guesses. The presentation layer uses `topCandidate.confidence` to
// decide whether to deep-link directly into the heritage detail page or to
// invite the user to disambiguate.

import "package:freezed_annotation/freezed_annotation.dart";

part "recognition_result.freezed.dart";

@freezed
class RecognitionCandidate with _$RecognitionCandidate {
  const factory RecognitionCandidate({
    required String heritagePubId,
    required String name,
    required double confidence,
    String? thumbnailUrl,
    String? country,
    String? regionLabel,
  }) = _RecognitionCandidate;

  const RecognitionCandidate._();

  bool get isHighConfidence => confidence >= 0.7;
}

@freezed
class RecognitionResult with _$RecognitionResult {
  const factory RecognitionResult({
    required String requestId,
    required RecognitionCandidate topCandidate,
    @Default(<RecognitionCandidate>[]) List<RecognitionCandidate> alternatives,
    String? language,
  }) = _RecognitionResult;
}
