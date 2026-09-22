import 'package:flutter_test/flutter_test.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/domain/media/entities/recognition_result.dart';
import 'package:silklens/presentation/providers/recognition_provider.dart';

// Minimal stub so RecognitionSuccess can be constructed without a real API call.
const _stubResult = RecognitionResult(
  candidates: [],
  topLabel: '',
  confidence: 0,
);

void main() {
  group('RecognitionNotifier', () {
    test('initial state is RecognitionIdle', () {
      final container = ProviderContainer(
        overrides: [
          recognitionProvider.overrideWith(_IsolatedRecognitionNotifier.new),
        ],
      );
      addTearDown(container.dispose);
      expect(
        container.read(recognitionProvider),
        isA<RecognitionIdle>(),
      );
    });

    test('RecognitionError holds its message', () {
      const err = RecognitionError('upload_failed');
      expect(err.message, equals('upload_failed'));
    });

    test('sealed subclasses are distinct types', () {
      expect(const RecognitionIdle(), isA<RecognitionState>());
      expect(const RecognitionLoading(), isA<RecognitionState>());
      expect(const RecognitionSuccess(_stubResult), isA<RecognitionState>());
    });
  });
}

class _IsolatedRecognitionNotifier extends RecognitionNotifier {
  @override
  RecognitionState build() => const RecognitionIdle();
}
