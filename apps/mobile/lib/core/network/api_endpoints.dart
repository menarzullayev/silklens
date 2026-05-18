// Centralized path constants. Keeps the API surface visible in one place
// and lets us bump versions or add a `/v2` prefix in a single edit.

abstract final class ApiEndpoints {
  static const String version = "/version";
  static const String health = "/health";
  static const String ready = "/ready";

  // Identity (wired against services/api/.../auth.py).
  static const String authRegister = "/v1/auth/register";
  static const String authLogin = "/v1/auth/login";
  static const String authRefresh = "/v1/auth/refresh";
  static const String authLogout = "/v1/auth/logout";
  static const String authMe = "/v1/auth/me";

  // Heritage
  static const String heritageList = "/v1/heritage";
  static String heritageById(String pubId) => "/v1/heritage/$pubId";

  // Media / vision (FAZA 2)
  static const String visionIdentify = "/v1/vision/identify";

  // Branding (Project-Decisions §1, §21). The legacy `/v1/tenant/branding`
  // path is admin-only; the public mobile-facing endpoint is `/v1/branding`.
  static const String branding = "/v1/branding";
  static const String tenantBranding = "/v1/tenant/branding";

  // Controlled vocabularies (heritage_kinds, languages, ...)
  static String vocab(String slug) => "/v1/vocab/$slug";

  static const String featureFlags = "/v1/feature-flags";
}
