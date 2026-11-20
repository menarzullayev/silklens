class VocabTermDto {
  const VocabTermDto({required this.slug, required this.displayName});
  factory VocabTermDto.fromJson(Map<String, dynamic> j) => VocabTermDto(
        slug: j['slug'] as String,
        displayName: (j['display_name'] as Map?)?.cast<String, String>() ?? {'en': j['slug'] as String},
      );
  final String slug;
  final Map<String, String> displayName;
}

class VocabDto {
  const VocabDto({required this.terms});
  factory VocabDto.fromJson(Map<String, dynamic> j) => VocabDto(
        terms: (j['items'] as List?)
                ?.map((e) => VocabTermDto.fromJson(e as Map<String, dynamic>))
                .toList() ??
            [],
      );
  final List<VocabTermDto> terms;
}
