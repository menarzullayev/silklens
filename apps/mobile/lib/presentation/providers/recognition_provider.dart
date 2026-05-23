// Recognition + Voice-Assistant state — SILK-0099, SILK-0101
//
// Calls go through SilkLensApiClient (Dio-backed).
// Pages watch these providers; they never touch Dio directly.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/domain/media/entities/recognition_result.dart';

// ---------------------------------------------------------------------------
// Recognition state
// ---------------------------------------------------------------------------

sealed class RecognitionState {
  const RecognitionState();
}

class RecognitionIdle extends RecognitionState {
  const RecognitionIdle();
}

class RecognitionLoading extends RecognitionState {
  const RecognitionLoading();
}

class RecognitionSuccess extends RecognitionState {
  const RecognitionSuccess(this.result);
  final RecognitionResult result;
}

class RecognitionError extends RecognitionState {
  const RecognitionError(this.message);
  final String message;
}

// ---------------------------------------------------------------------------
// Recognition notifier
// ---------------------------------------------------------------------------

class RecognitionNotifier extends Notifier<RecognitionState> {
  @override
  RecognitionState build() => const RecognitionIdle();

  Future<void> analyzeBytes({
    required List<int> bytes,
    required String filename,
    required String mimeType,
    required String language,
  }) async {
    state = const RecognitionLoading();
    try {
      final client = ref.read(silkLensApiClientProvider);

      final uploadResult = await client.uploadMedia(
        bytes: bytes,
        filename: filename,
        mimeType: mimeType,
      );
      final assetId = (uploadResult['asset'] as Map<String, dynamic>?)?['id'] as String?;

      if (assetId == null) {
        state = const RecognitionError('Upload failed: no asset id returned');
        return;
      }

      final raw = await client.recognizeImage(
        mediaAssetId: assetId,
        language: language,
      );

      final rawCandidates = (raw['candidates'] as List<dynamic>?) ?? <dynamic>[];
      final candidates = rawCandidates.map((dynamic e) {
        final entry = e as Map<String, dynamic>;
        return RecognitionCandidate(
          heritagePubId: entry['heritage_pub_id'] as String? ?? '',
          confidence: (entry['confidence'] as num? ?? 0).toDouble(),
          name: entry['name'] as String?,
        );
      }).toList();

      state = RecognitionSuccess(
        RecognitionResult(
          candidates: candidates,
          topLabel: raw['label'] as String? ?? '',
          confidence: (raw['confidence'] as num? ?? 0).toDouble(),
        ),
      );
    } on Exception catch (e) {
      state = RecognitionError(e.toString());
    }
  }

  void reset() => state = const RecognitionIdle();
}

final recognitionProvider = NotifierProvider<RecognitionNotifier, RecognitionState>(
  RecognitionNotifier.new,
);

// ---------------------------------------------------------------------------
// Voice-assistant state
// ---------------------------------------------------------------------------

sealed class VoiceState {
  const VoiceState();
}

class VoiceIdle extends VoiceState {
  const VoiceIdle();
}

class VoiceListening extends VoiceState {
  const VoiceListening();
}

class VoiceProcessing extends VoiceState {
  const VoiceProcessing();
}

class VoiceResult extends VoiceState {
  const VoiceResult({required this.transcript, this.intent});
  final String transcript;
  final String? intent;
}

class VoiceError extends VoiceState {
  const VoiceError(this.message);
  final String message;
}

// ---------------------------------------------------------------------------
// Voice notifier
// ---------------------------------------------------------------------------

class VoiceNotifier extends Notifier<VoiceState> {
  @override
  VoiceState build() => const VoiceIdle();

  void startListening() => state = const VoiceListening();

  void stopListening() {
    if (state is VoiceListening) state = const VoiceIdle();
  }

  Future<void> submitAudio({
    required List<int> bytes,
    required String filename,
    required String language,
  }) async {
    state = const VoiceProcessing();
    try {
      final client = ref.read(silkLensApiClientProvider);

      // Transcribe
      final asr = await client.transcribeAudio(
        bytes: bytes,
        filename: filename,
        language: language,
      );
      final transcript = asr['transcript'] as String? ?? '';

      if (transcript.isEmpty) {
        state = const VoiceError('No speech detected');
        return;
      }

      // Resolve intent
      final intentResult = await client.resolveVoiceIntent(
        transcript: transcript,
        language: language,
      );
      final intent = intentResult['intent'] as String?;

      state = VoiceResult(transcript: transcript, intent: intent);
    } on Exception catch (e) {
      state = VoiceError(e.toString());
    }
  }

  void reset() => state = const VoiceIdle();
}

final voiceProvider = NotifierProvider<VoiceNotifier, VoiceState>(
  VoiceNotifier.new,
);
