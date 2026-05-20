class VersionDto {
  const VersionDto({required this.version});
  factory VersionDto.fromJson(Map<String, dynamic> j) =>
      VersionDto(version: j['version'] as String? ?? '0.1.0');
  final String version;
}
