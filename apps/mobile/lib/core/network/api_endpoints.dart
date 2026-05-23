// Centralized path constants. Keeps the API surface visible in one place
// and lets us bump versions or add a `/v2` prefix in a single edit.

abstract final class ApiEndpoints {
  static const String version = '/version';
  static const String health = '/health';
  static const String ready = '/ready';

  // Identity (wired against services/api/.../auth.py).
  static const String authRegister = '/v1/auth/register';
  static const String authLogin = '/v1/auth/login';
  static const String authRefresh = '/v1/auth/refresh';
  static const String authLogout = '/v1/auth/logout';
  static const String authMe = '/v1/auth/me';
  static const String authVerifyEmail = '/v1/auth/verify-email';
  static const String authResendVerification = '/v1/auth/resend-verification';
  static const String authForgotPassword = '/v1/auth/forgot-password';
  static const String authResetPassword = '/v1/auth/reset-password';

  // Heritage
  static const String heritageList = '/v1/heritage';
  static String heritageById(String pubId) => '/v1/heritage/$pubId';

  // Media / vision (FAZA 2)
  static const String visionIdentify = '/v1/vision/identify';

  // Branding (Project-Decisions §1, §21). The legacy `/v1/tenant/branding`
  // path is admin-only; the public mobile-facing endpoint is `/v1/branding`.
  static const String branding = '/v1/branding';
  static const String tenantBranding = '/v1/tenant/branding';

  // Controlled vocabularies (heritage_kinds, languages, ...)
  static String vocab(String slug) => '/v1/vocab/$slug';

  static const String featureFlags = '/v1/feature-flags';

  // Notifications
  static const String notificationPreferences = '/v1/notifications/preferences';
  static const String quietHours = '/v1/notifications/quiet-hours';

  // GDPR / account
  static const String consents = '/v1/me/consents';
  static const String dataExport = '/v1/me/data-export';
  static const String deleteAccount = '/v1/me/account/delete';

  // Search (SILK-0095)
  static const String search = '/v1/search';

  // AI — Text-to-Speech (SILK-0096)
  static const String aiTts = '/v1/ai/tts';

  // Billing (SILK-0104..0107)
  static const String billingPlans = '/v1/billing/plans';
  static const String billingSubscriptions = '/v1/billing/subscriptions';
  static const String billingSubscriptionsCancel =
      '/v1/billing/subscriptions/cancel';
  static const String billingSubscriptionsResume =
      '/v1/billing/subscriptions/resume';
  static const String billingMeSubscription = '/v1/billing/me/subscription';
  static const String billingMeInvoices = '/v1/billing/me/invoices';
  static const String billingMeEntitlements = '/v1/billing/me/entitlements';
  static const String billingCouponsValidate = '/v1/billing/coupons/validate';

  // Gamification (SILK-0108..0112)
  static const String meXp = '/v1/me/xp';
  static const String meBadges = '/v1/me/badges';
  static const String meStreak = '/v1/me/streak';
  static const String meStreakTick = '/v1/me/streak/tick';
  static const String leaderboards = '/v1/leaderboards';
  static String leaderboardBySlug(String slug) => '/v1/leaderboards/$slug';
}
