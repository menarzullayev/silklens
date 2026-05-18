// Riverpod wrapper around the [VocabRepository]. Specialized providers
// expose the two vocabularies the FAZA 1 mobile UI actually needs
// (heritage_kinds for the list filter, languages for the locale picker).

import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/data/repositories/vocab_repository_impl.dart"
    show vocabRepositoryProvider;
import "package:silklens/domain/vocab/entities/vocab_term.dart";

final FutureProviderFamily<List<VocabTerm>, String> vocabProvider =
    FutureProvider.family<List<VocabTerm>, String>(
  (Ref ref, String slug) async {
    final result = await ref.read(vocabRepositoryProvider).list(slug);
    return result.fold<List<VocabTerm>>(
      onSuccess: (List<VocabTerm> v) => v,
      onFailure: (_) => const <VocabTerm>[],
    );
  },
  name: "vocabProvider",
);

final FutureProvider<List<VocabTerm>> heritageKindsProvider =
    FutureProvider<List<VocabTerm>>(
  (Ref ref) => ref.watch(vocabProvider("heritage_kinds").future),
  name: "heritageKindsProvider",
);

final FutureProvider<List<VocabTerm>> languagesVocabProvider =
    FutureProvider<List<VocabTerm>>(
  (Ref ref) => ref.watch(vocabProvider("languages").future),
  name: "languagesVocabProvider",
);
