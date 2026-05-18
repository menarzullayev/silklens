// Centralized path constants. Keeps the API surface visible in one place
// and lets us bump versions or add a `/v2` prefix in a single edit.

abstract final class ApiEndpoints {
  static const String version = "/version";
  static const String health = "/health";
  static const String ready = "/ready";

  // Identity (FAZA 2 — placeholders so retrofit can be wired today).
  static const String authRegister = "/v1/auth/register";
  static const String authLogin = "/v1/auth/login";
  static const String authRefresh = "/v1/auth/refresh";
  static const String authMe = "/v1/auth/me";

  // Heritage
  static const String heritageList = "/v1/heritage";
  static String heritageById(String id) => "/v1/heritage/$id";

  // Media / vision (FAZA 2)
  static const String visionIdentify = "/v1/vision/identify";

  // Tenant branding & remote config (Project-Decisions §1, §21)
  static const String tenantBranding = "/v1/tenant/branding";
  static const String featureFlags = "/v1/feature-flags";
}
