// Camera recognition state machine.
//
// Lifecycle:
//   idle → uploading(capture) → recognising(capture, mediaAssetId)
//        → done(result) | failed(error)
//
// The provider is pure orchestration; HTTP lives in [RecognitionRepository].
// The Camera UI listens to the state and renders the appropriate overlay.

import "dart:async";

import "package:flutter/foundation.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/recognition_repository_impl.dart";
import "package:silklens/domain/media/entities/media_capture.dart";
import "package:silklens/domain/media/entities/recognition_result.dart";
import "package:silklens/domain/media/repositories/recognition_repository.dart";

/// Discriminated state for the camera recognition pipeline.
@immutable
sealed class RecognitionState {
  const RecognitionState();
}

class RecognitionIdle extends RecognitionState {
  const RecognitionIdle();
}

class RecognitionUploading extends RecognitionState {
  const RecognitionUploading(this.capture);
  final MediaCapture capture;
}

class RecognitionRecognising extends RecognitionState {
  const RecognitionRecognising({
    required this.capture,
    required this.mediaAssetId,
  });
  final MediaCapture capture;
  final String mediaAssetId;
}

class RecognitionDone extends RecognitionState {
  const RecognitionDone(this.result);
  final RecognitionResult result;
}

class RecognitionFailed extends RecognitionState {
  const RecognitionFailed(this.failure);
  final Failure failure;
}

class RecognitionController extends Notifier<RecognitionState> {
  @override
  RecognitionState build() => const RecognitionIdle();

  Future<void> run(MediaCapture capture, {required String language}) async {
    state = RecognitionUploading(capture);
    final repo = ref.read(recognitionRepositoryProvider);

    final upload = await repo.uploadMedia(capture);
    if (upload.isFailure) {
      state = RecognitionFailed(upload.failureOrNull!);
      return;
    }
    final assetId = upload.successOrNull!.mediaAssetId;
    state = RecognitionRecognising(capture: capture, mediaAssetId: assetId);

    final recognised = await repo.recognize(
      mediaAssetId: assetId,
      language: language,
    );
    state = recognised.fold<RecognitionState>(
      onSuccess: RecognitionDone.new,
      onFailure: RecognitionFailed.new,
    );
  }

  void reset() {
    state = const RecognitionIdle();
  }

  @visibleForTesting
  void setStateForTest(RecognitionState newState) {
    state = newState;
  }
}

final NotifierProvider<RecognitionController, RecognitionState>
    recognitionControllerProvider =
    NotifierProvider<RecognitionController, RecognitionState>(
  RecognitionController.new,
  name: "recognitionControllerProvider",
);

/// Recent recognitions kept in memory for the bottom carousel.
class RecentRecognitionsController extends Notifier<List<RecognitionCandidate>> {
  static const int _maxItems = 12;

  @override
  List<RecognitionCandidate> build() {
    ref.listen<RecognitionState>(recognitionControllerProvider,
        (RecognitionState? prev, RecognitionState next) {
      if (next is RecognitionDone) {
        add(next.result.topCandidate);
      }
    });
    return const <RecognitionCandidate>[];
  }

  void add(RecognitionCandidate candidate) {
    final next = <RecognitionCandidate>[
      candidate,
      ...state.where((RecognitionCandidate c) => c.heritagePubId != candidate.heritagePubId),
    ];
    state = next.length > _maxItems ? next.sublist(0, _maxItems) : next;
  }
}

final NotifierProvider<RecentRecognitionsController, List<RecognitionCandidate>>
    recentRecognitionsProvider =
    NotifierProvider<RecentRecognitionsController, List<RecognitionCandidate>>(
  RecentRecognitionsController.new,
  name: "recentRecognitionsProvider",
);
