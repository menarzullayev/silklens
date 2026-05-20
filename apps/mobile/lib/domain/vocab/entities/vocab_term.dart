// Pure-Dart vocabulary term entity. Mirrors `VocabTermOut` in the backend.

import 'package:meta/meta.dart';

@immutable
class VocabTerm {
  const VocabTerm({
    required this.slug,
    required this.displayName,
    this.parentSlug,
    this.sortOrder = 0,
  });

  final String slug;
  final Map<String, String> displayName;
  final String? parentSlug;
  final int sortOrder;

  String localizedName(String languageCode) {
    if (displayName.isEmpty) return slug;
    return displayName[languageCode] ??
        displayName['en'] ??
        displayName.values.firstWhere(
          (String v) => v.isNotEmpty,
          orElse: () => slug,
        );
  }
}
