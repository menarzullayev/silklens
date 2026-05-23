// SILK-0138 — Review Analysis provider.
// Fetches AI-generated review analysis for a heritage site.
// Used by ReviewAnalysisWidget embedded in HeritageDetailPage.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

/// `FutureProvider.family` keyed by `heritagePubId` (string).
/// Cached per heritage pub_id for the lifetime of the provider scope.
final reviewAnalysisProvider =
    FutureProvider.family<Map<String, dynamic>, String>(
  (Ref ref, String pubId) async {
    final client = ref.read(silkLensApiClientProvider);
    return client.getReviewAnalysis(pubId);
  },
);
