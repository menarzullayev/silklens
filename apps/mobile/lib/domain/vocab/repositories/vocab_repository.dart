import "package:silklens/core/utils/result.dart";
import "package:silklens/domain/vocab/entities/vocab_term.dart";

abstract interface class VocabRepository {
  Future<Result<List<VocabTerm>>> list(String vocabularySlug);
}
