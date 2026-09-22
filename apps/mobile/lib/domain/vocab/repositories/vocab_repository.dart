import 'package:silklens/core/utils/result.dart';
import 'package:silklens/domain/vocab/entities/vocab_term.dart';

// Clean Arch domain interface — abstract for future ContractContract growth.
// ignore: one_member_abstracts
abstract interface class VocabRepository {
  Future<Result<List<VocabTerm>>> list(String vocabularySlug);
}
