class RecognitionCandidate {
  const RecognitionCandidate({required this.heritagePubId, required this.confidence, this.name});
  final String heritagePubId;
  final double confidence;
  final String? name;
}

class RecognitionResult {
  const RecognitionResult(
      {required this.candidates, required this.topLabel, required this.confidence,});
  final List<RecognitionCandidate> candidates;
  final String topLabel;
  final double confidence;
  bool get hasMatch => confidence > 0.5;
}
