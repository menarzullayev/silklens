// Unit tests for [RecognitionController].
//
// We use mocktail to stub [RecognitionRepository] and drive the state machine
// through its happy path + each failure branch.

import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/recognition_repository_impl.dart";
import "package:silklens/domain/media/entities/media_capture.dart";
import "package:silklens/domain/media/entities/media_upload.dart";
import "package:silklens/domain/media/entities/recognition_result.dart";
import "package:silklens/domain/media/repositories/recognition_repository.dart";
import "package:silklens/presentation/providers/recognition_provider.dart";

class _MockRepo extends Mock implements RecognitionRepository {}

class _FakeCapture extends Fake implements MediaCapture {}

void main() {
  setUpAll(() {
    registerFallbackValue(_FakeCapture());
  });

  const capture = MediaCapture(
    localPath: "/tmp/sample.jpg",
    kind: MediaCaptureKind.photo,
  );
  const upload = MediaUpload(mediaAssetId: "asset-1");
  const result = RecognitionResult(
    requestId: "req-1",
    topCandidate: RecognitionCandidate(
      heritagePubId: "pub-1",
      name: "Registan",
      confidence: 0.92,
    ),
  );

  ProviderContainer makeContainer(RecognitionRepository repo) =>
      ProviderContainer(
        overrides: <Override>[
          recognitionRepositoryProvider.overrideWithValue(repo),
        ],
      );

  test("transitions idle → uploading → recognising → done on success",
      () async {
    final repo = _MockRepo();
    when(() => repo.uploadMedia(any())).thenAnswer(
      (_) async => const Success<MediaUpload>(upload),
    );
    when(() =>
            repo.recognize(mediaAssetId: "asset-1", language: "en"))
        .thenAnswer((_) async => const Success<RecognitionResult>(result));

    final container = makeContainer(repo);
    final notifier = container.read(recognitionControllerProvider.notifier);

    final states = <RecognitionState>[];
    container.listen<RecognitionState>(
      recognitionControllerProvider,
      (RecognitionState? _, RecognitionState next) => states.add(next),
      fireImmediately: true,
    );

    await notifier.run(capture, language: "en");

    expect(states.first, isA<RecognitionIdle>());
    expect(states.any((RecognitionState s) => s is RecognitionUploading),
        isTrue);
    expect(states.any((RecognitionState s) => s is RecognitionRecognising),
        isTrue);
    expect(states.last, isA<RecognitionDone>());
    expect((states.last as RecognitionDone).result.topCandidate.name,
        equals("Registan"));
  });

  test("transitions to failed when upload fails", () async {
    final repo = _MockRepo();
    when(() => repo.uploadMedia(any())).thenAnswer(
      (_) async => const FailureResult<MediaUpload>(
        NetworkFailure("offline"),
      ),
    );
    final container = makeContainer(repo);
    final notifier = container.read(recognitionControllerProvider.notifier);
    await notifier.run(capture, language: "en");

    final state = container.read(recognitionControllerProvider);
    expect(state, isA<RecognitionFailed>());
    expect((state as RecognitionFailed).failure, isA<NetworkFailure>());
    // recognize() must never be called when upload fails.
    verifyNever(() => repo.recognize(
          mediaAssetId: any(named: "mediaAssetId"),
          language: any(named: "language"),
        ));
  });

  test("transitions to failed when recognise fails", () async {
    final repo = _MockRepo();
    when(() => repo.uploadMedia(any())).thenAnswer(
      (_) async => const Success<MediaUpload>(upload),
    );
    when(() => repo.recognize(
          mediaAssetId: any(named: "mediaAssetId"),
          language: any(named: "language"),
        )).thenAnswer(
      (_) async => const FailureResult<RecognitionResult>(
        ServerFailure("500", statusCode: 500),
      ),
    );

    final container = makeContainer(repo);
    final notifier = container.read(recognitionControllerProvider.notifier);
    await notifier.run(capture, language: "uz");

    final state = container.read(recognitionControllerProvider);
    expect(state, isA<RecognitionFailed>());
  });

  test("recent recognitions carousel grows on success", () async {
    final repo = _MockRepo();
    when(() => repo.uploadMedia(any())).thenAnswer(
      (_) async => const Success<MediaUpload>(upload),
    );
    when(() => repo.recognize(
          mediaAssetId: any(named: "mediaAssetId"),
          language: any(named: "language"),
        )).thenAnswer((_) async => const Success<RecognitionResult>(result));

    final container = makeContainer(repo);
    // Force the controller to initialise.
    container.read(recentRecognitionsProvider);
    await container
        .read(recognitionControllerProvider.notifier)
        .run(capture, language: "en");

    final recent = container.read(recentRecognitionsProvider);
    expect(recent, hasLength(1));
    expect(recent.first.heritagePubId, equals("pub-1"));
  });
}
