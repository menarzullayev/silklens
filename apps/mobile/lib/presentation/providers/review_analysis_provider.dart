// SILK-0138 — Review Analysis provider.
// Fetches AI-generated review analysis for a heritage site.
// Used by ReviewAnalysisWidget embedded in HeritageDetailPage.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';

/// FutureProvider.family keyed by [heritagePubId].
/// Automatically cached per heritage until the widget is disposed.
final reviewAnalysisProvider =
    FutureProvider.family<Map<String, dynamic>, String>(
  (FutureProviderRef<Map<String, dynamic>> ref, String pubId) async {
    final SilkLensApiClient client = ref.read(silkLensApiClientProvider);
    return client.getReviewAnalysis(pubId);
  },
);
