// Plain Dio HTTP client — retrofit dependency removed for FAZA 1.
// Per ADR-0003: repositories depend on this client. Domain does not.

import 'package:dio/dio.dart';
import 'package:silklens/core/network/api_endpoints.dart';
import 'package:silklens/data/api/dto/auth_dto.dart';
import 'package:silklens/data/api/dto/branding_dto.dart';
import 'package:silklens/data/api/dto/heritage_dto.dart';
import 'package:silklens/data/api/dto/tenant_branding_dto.dart';
import 'package:silklens/data/api/dto/version_dto.dart';
import 'package:silklens/data/api/dto/vocab_dto.dart';

class SilkLensApiClient {
  SilkLensApiClient(this._dio);

  final Dio _dio;

  // --- Meta ----------------------------------------------------------------

  Future<VersionDto> getVersion() async {
    final r = await _dio.get<Map<String, dynamic>>(ApiEndpoints.version);
    return VersionDto.fromJson(r.data!);
  }

  Future<TenantBrandingDto> getTenantBranding() async {
    final r = await _dio.get<Map<String, dynamic>>(ApiEndpoints.tenantBranding);
    return TenantBrandingDto.fromJson(r.data!);
  }

  Future<BrandingDto> getBranding({String? tenantSlug}) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.branding,
      queryParameters: tenantSlug != null ? {'tenant': tenantSlug} : null,
    );
    return BrandingDto.fromJson(r.data!);
  }

  Future<VocabDto> getVocabulary(String slug) async {
    final r = await _dio.get<Map<String, dynamic>>('/v1/vocab/$slug');
    return VocabDto.fromJson(r.data!);
  }

  // --- Auth ----------------------------------------------------------------

  Future<LoginResponseDto> register(RegisterRequestDto body) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.authRegister,
      data: body.toJson(),
    );
    return LoginResponseDto.fromJson(r.data!);
  }

  Future<LoginResponseDto> login(LoginRequestDto body) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.authLogin,
      data: body.toJson(),
    );
    return LoginResponseDto.fromJson(r.data!);
  }

  Future<LoginResponseDto> refresh(RefreshRequestDto body) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.authRefresh,
      data: body.toJson(),
    );
    return LoginResponseDto.fromJson(r.data!);
  }

  Future<LogoutResponseDto> logout() async {
    final r = await _dio.post<Map<String, dynamic>>(ApiEndpoints.authLogout);
    return LogoutResponseDto.fromJson(r.data!);
  }

  Future<LoginResponseDto> googleSignIn(String accessToken) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/auth/google',
      data: {'access_token': accessToken},
    );
    return LoginResponseDto.fromJson(r.data!);
  }

  // --- Facebook OAuth (SILK-0172) -------------------------------------------
  // Backend route: POST /v1/auth/facebook — verifies access_token with Graph
  // API and returns a SilkLens session. Requires flutter_facebook_auth on
  // the Flutter side to obtain the access_token.

  Future<LoginResponseDto> facebookSignIn(String accessToken) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/auth/facebook',
      data: {'access_token': accessToken},
    );
    return LoginResponseDto.fromJson(r.data!);
  }

  // --- Instagram OAuth (SILK-0172) ------------------------------------------
  // Backend route: POST /v1/auth/instagram — exchanges short-lived Instagram
  // OAuth 2.0 token for a SilkLens session.

  Future<LoginResponseDto> instagramSignIn(String accessToken) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/auth/instagram',
      data: {'access_token': accessToken},
    );
    return LoginResponseDto.fromJson(r.data!);
  }

  Future<MeResponseDto> me() async {
    final r = await _dio.get<Map<String, dynamic>>(ApiEndpoints.authMe);
    return MeResponseDto.fromJson(r.data!);
  }

  Future<VerifyEmailResponseDto> verifyEmail(VerifyEmailRequestDto body) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.authVerifyEmail,
      data: body.toJson(),
    );
    return VerifyEmailResponseDto.fromJson(r.data!);
  }

  Future<ResendVerificationResponseDto> resendVerification(
    ResendVerificationRequestDto body,
  ) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.authResendVerification,
      data: body.toJson(),
    );
    return ResendVerificationResponseDto.fromJson(r.data!);
  }

  // --- Heritage ------------------------------------------------------------

  Future<HeritagePageDto> listHeritage({
    String? kind,
    String? country,
    String? status,
    String? search,
    int limit = 20,
    int offset = 0,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.heritageList,
      queryParameters: {
        if (kind != null) 'kind': kind,
        if (country != null) 'country': country,
        if (status != null) 'status': status,
        if (search != null) 'search': search,
        'limit': limit,
        'offset': offset,
      },
    );
    return HeritagePageDto.fromJson(r.data!);
  }

  Future<HeritageDto> getHeritage(String pubId) async {
    final r = await _dio.get<Map<String, dynamic>>('/v1/heritage/$pubId');
    return HeritageDto.fromJson(r.data!);
  }

  // --- Gamification (SILK-0108..0112) ----------------------------------------

  Future<Map<String, dynamic>> getXpBalance() async {
    final r = await _dio.get<Map<String, dynamic>>(ApiEndpoints.meXp);
    return r.data!;
  }

  Future<Map<String, dynamic>> getStreak() async {
    final r = await _dio.get<Map<String, dynamic>>(ApiEndpoints.meStreak);
    return r.data!;
  }

  Future<Map<String, dynamic>> tickStreak() async {
    final r = await _dio.post<Map<String, dynamic>>(ApiEndpoints.meStreakTick);
    return r.data!;
  }

  Future<List<dynamic>> getBadges() async {
    final r = await _dio.get<Map<String, dynamic>>(ApiEndpoints.meBadges);
    return (r.data!['items'] as List?) ?? [];
  }

  Future<List<dynamic>> listLeaderboards() async {
    final r = await _dio.get<Map<String, dynamic>>(ApiEndpoints.leaderboards);
    return (r.data!['items'] as List?) ?? [];
  }

  Future<Map<String, dynamic>> getLeaderboard(
    String slug, {
    String period = 'weekly',
    int limit = 50,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.leaderboardBySlug(slug),
      queryParameters: {'period': period, 'limit': limit},
    );
    return r.data!;
  }

  // --- Social ----------------------------------------------------------------

  Future<Map<String, dynamic>> getSocialFeed({
    int limit = 20,
    String? before,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/social/feed',
      queryParameters: {
        'limit': limit,
        if (before != null) 'before': before,
      },
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> getFollowing(
    String pubId, {
    int limit = 30,
    int offset = 0,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/social/following/$pubId',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> getFollowers(
    String pubId, {
    int limit = 30,
    int offset = 0,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/social/followers/$pubId',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return r.data!;
  }

  Future<void> followUser(String pubId) async {
    await _dio.post<void>('/v1/social/follow/$pubId');
  }

  Future<void> unfollowUser(String pubId) async {
    await _dio.delete<void>('/v1/social/follow/$pubId');
  }

  Future<void> blockUser(String pubId, {String? reason}) async {
    await _dio.post<void>(
      '/v1/social/block/$pubId',
      data: reason != null ? {'reason': reason} : null,
    );
  }

  Future<void> unblockUser(String pubId) async {
    await _dio.delete<void>('/v1/social/block/$pubId');
  }

  Future<Map<String, dynamic>> createFriendInvite({
    String? targetPubId,
    String? targetEmail,
    String? message,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/social/friends/invite',
      data: {
        if (targetPubId != null) 'target_pub_id': targetPubId,
        if (targetEmail != null) 'target_email': targetEmail,
        if (message != null) 'message': message,
      },
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> acceptFriendInvitation(String token) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/social/friends/accept',
      data: {'token': token},
    );
    return r.data!;
  }

  // --- Notifications ---------------------------------------------------------

  Future<Map<String, dynamic>> getNotifications({
    int limit = 30,
    bool unreadOnly = false,
    String? before,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/notifications',
      queryParameters: {
        'limit': limit,
        'unread_only': unreadOnly,
        if (before != null) 'before': before,
      },
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> markNotificationRead(
    String notificationId,
  ) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/notifications/$notificationId/read',
    );
    return r.data ?? {};
  }

  Future<Map<String, dynamic>> markAllNotificationsRead() async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/notifications/mark-all-read',
    );
    return r.data ?? {};
  }

  // --- Billing ---------------------------------------------------------------

  Future<Map<String, dynamic>> getBillingPlans({String? pricingZone}) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/billing/plans',
      queryParameters:
          pricingZone != null ? {'pricing_zone': pricingZone} : null,
    );
    return r.data!;
  }

  Future<Map<String, dynamic>?> getCurrentSubscription() async {
    try {
      final r =
          await _dio.get<Map<String, dynamic>>('/v1/billing/me/subscription');
      return r.data;
    } on DioException catch (e) {
      if (e.response?.statusCode == 404) return null;
      rethrow;
    }
  }

  Future<List<dynamic>> getInvoices({int limit = 20, int offset = 0}) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/billing/me/invoices',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return (r.data!['items'] as List?) ?? [];
  }

  Future<List<dynamic>> getEntitlements() async {
    final r =
        await _dio.get<Map<String, dynamic>>('/v1/billing/me/entitlements');
    return (r.data!['items'] as List?) ?? [];
  }

  Future<void> cancelSubscription({bool atPeriodEnd = true}) async {
    await _dio.post<void>(
      '/v1/billing/subscriptions/cancel',
      data: {'at_period_end': atPeriodEnd},
    );
  }

  Future<void> resumeSubscription() async {
    await _dio.post<void>('/v1/billing/subscriptions/resume');
  }

  /// Creates a new subscription. Returns the full API response envelope which
  /// contains a `subscription` key. Accepts an optional `Idempotency-Key`
  /// header to prevent duplicate charges on network retry.
  Future<Map<String, dynamic>> createSubscription({
    required String planSlug,
    required String paymentMethodToken,
    String? pricingZoneSlug,
    String? idempotencyKey,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/billing/subscriptions',
      data: {
        'plan_slug': planSlug,
        'payment_method_token': paymentMethodToken,
        if (pricingZoneSlug != null) 'pricing_zone_slug': pricingZoneSlug,
      },
      options: Options(
        headers: {
          if (idempotencyKey != null) 'Idempotency-Key': idempotencyKey,
        },
      ),
    );
    return r.data!;
  }

  Future<Map<String, dynamic>?> validateCoupon(
    String code,
    double orderValueUsd,
  ) async {
    try {
      final r = await _dio.post<Map<String, dynamic>>(
        '/v1/billing/coupons/validate',
        data: {'code': code, 'order_value_usd': orderValueUsd},
      );
      return r.data;
    } on DioException catch (e) {
      if (e.response?.statusCode == 404 || e.response?.statusCode == 422) {
        return null;
      }
      rethrow;
    }
  }

  // --- Notification Preferences --------------------------------------------

  Future<void> registerPushDevice({
    required String platform,
    required String installationId,
    String? fcmToken,
  }) async {
    await _dio.post<void>('/v1/notifications/push-devices', data: {
      'platform': platform,
      'installation_id': installationId,
      if (fcmToken != null) 'fcm_token': fcmToken,
    },);
  }

  Future<Map<String, dynamic>> getNotificationPreferences() async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.notificationPreferences,
    );
    return r.data!;
  }

  Future<void> updateNotificationPreferences(
    List<Map<String, dynamic>> prefs,
  ) async {
    await _dio.patch<void>(ApiEndpoints.notificationPreferences, data: prefs);
  }

  Future<Map<String, dynamic>> updateQuietHours({
    required String timezone,
    required String startTime,
    required String endTime,
    required List<int> weekdays,
  }) async {
    final r = await _dio.put<Map<String, dynamic>>(
      ApiEndpoints.quietHours,
      data: {
        'timezone': timezone,
        'start_time': startTime,
        'end_time': endTime,
        'weekdays': weekdays,
      },
    );
    return r.data!;
  }

  // --- GDPR / Account -------------------------------------------------------

  Future<List<dynamic>> getConsents() async {
    final r = await _dio.get<Map<String, dynamic>>(ApiEndpoints.consents);
    final data = r.data!;
    return (data['items'] as List?) ?? (data['consents'] as List?) ?? [];
  }

  Future<Map<String, dynamic>> requestDataExport() async {
    final r = await _dio.post<Map<String, dynamic>>(ApiEndpoints.dataExport);
    return r.data!;
  }

  Future<Map<String, dynamic>> getDataExportStatus(String requestId) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '${ApiEndpoints.dataExport}/$requestId',
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> requestAccountDeletion({String? reason}) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.deleteAccount,
      data: {if (reason != null) 'reason': reason},
    );
    return r.data!;
  }

  // --- Password Reset (SILK-0122) -------------------------------------------

  Future<Map<String, dynamic>> forgotPassword(String email) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.authForgotPassword,
      data: {'email': email},
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> resetPassword({
    required String email,
    required String code,
    required String newPassword,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.authResetPassword,
      data: {'email': email, 'code': code, 'new_password': newPassword},
    );
    return r.data!;
  }

  // --- Reviews ---------------------------------------------------------------

  Future<Map<String, dynamic>> createReview({
    required String heritagePubId,
    required String bodyMd,
    required String languageTag,
    List<Map<String, dynamic>>? ratings,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/heritage/$heritagePubId/reviews',
      data: {
        'body_md': bodyMd,
        'language_tag': languageTag,
        if (ratings != null) 'ratings': ratings,
      },
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> getHeritageReviews(
    String pubId, {
    int limit = 10,
    int offset = 0,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/heritage/$pubId/reviews',
      queryParameters: {'limit': limit, 'offset': offset},
    );
    return r.data!;
  }

  // --- User Profile ----------------------------------------------------------

  Future<Map<String, dynamic>> updateProfile({
    String? displayName,
    String? bio,
    List<String>? dietaryPrefs,
    List<String>? travelStyle,
    List<String>? interests,
  }) async {
    final r = await _dio.patch<Map<String, dynamic>>(
      '/v1/me/profile',
      data: {
        if (displayName != null) 'display_name': displayName,
        if (bio != null) 'bio': bio,
        if (dietaryPrefs != null) 'dietary_prefs': dietaryPrefs,
        if (travelStyle != null) 'travel_style': travelStyle,
        if (interests != null) 'interests': interests,
      },
    );
    return r.data!;
  }

  // --- Search (SILK-0095) ---------------------------------------------------

  Future<Map<String, dynamic>> searchHeritage({
    required String query,
    String lang = 'en',
    String? country,
    String? kind,
    int limit = 20,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      ApiEndpoints.search,
      queryParameters: {
        'q': query,
        'lang': lang,
        'limit': limit,
        if (country != null) 'country': country,
        if (kind != null) 'kind': kind,
      },
    );
    return r.data!;
  }

  // --- TTS / Audio Guide (SILK-0096) ----------------------------------------

  Future<Map<String, dynamic>> generateTts({
    required String text,
    required String language,
    String? voiceId,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      ApiEndpoints.aiTts,
      data: {
        'text': text,
        'language': language,
        if (voiceId != null) 'voice_id': voiceId,
      },
    );
    return r.data!;
  }

  // --- Trips (SILK-0103) ----------------------------------------------------

  Future<Map<String, dynamic>> createTrip({
    required List<String> cities,
    String? startDate,
    String? endDate,
    double? budgetUsd,
    List<String>? interests,
    String language = 'en',
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/trips',
      data: {
        'cities': cities,
        if (startDate != null) 'start_date': startDate,
        if (endDate != null) 'end_date': endDate,
        if (budgetUsd != null) 'budget_usd': budgetUsd,
        'interests': interests ?? [],
        'language': language,
      },
    );
    return r.data!;
  }

  Future<List<dynamic>> getMyTrips() async {
    final r = await _dio.get<Map<String, dynamic>>('/v1/trips');
    return (r.data!['items'] as List?) ?? [];
  }

  Future<Map<String, dynamic>> quickPlan({
    required double availableHours,
    double? lat,
    double? lng,
    String language = 'en',
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/trips/quick-plan',
      data: {
        'available_hours': availableHours,
        if (lat != null) 'lat': lat,
        if (lng != null) 'lng': lng,
        'language': language,
      },
    );
    return r.data!;
  }

  // --- Emergency (SILK-0127) ------------------------------------------------

  Future<List<dynamic>> getEmergencyContacts({
    String countryCode = 'UZ',
    String language = 'en',
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/emergency',
      queryParameters: {'country_code': countryCode, 'language': language},
    );
    return (r.data!['items'] as List?) ?? [];
  }

  // --- Tickets (SILK-0126) --------------------------------------------------

  Future<List<dynamic>> getTicketTypes(
    String heritagePubId, {
    String language = 'en',
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/ticket-types',
      queryParameters: {
        'heritage_pub_id': heritagePubId,
        'language': language,
      },
    );
    return (r.data!['items'] as List?) ?? [];
  }

  Future<Map<String, dynamic>> purchaseTicket({
    required String ticketTypeId,
    String? visitDate,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/tickets/purchase',
      data: {
        'ticket_type_id': ticketTypeId,
        if (visitDate != null) 'visit_date': visitDate,
      },
    );
    return r.data!;
  }

  Future<List<dynamic>> getMyTickets() async {
    final r = await _dio.get<Map<String, dynamic>>('/v1/tickets/me');
    return (r.data!['items'] as List?) ?? [];
  }

  // --- Cultural Tips (SILK-0128) --------------------------------------------

  Future<List<dynamic>> getCulturalTips({
    String countryCode = 'UZ',
    String language = 'en',
    String? tipContext,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/cultural-tips',
      queryParameters: {
        'country_code': countryCode,
        'language': language,
        if (tipContext != null) 'context': tipContext,
      },
    );
    return (r.data!['items'] as List?) ?? [];
  }

  // --- Weather Guide (SILK-0129) -------------------------------------------

  Future<Map<String, dynamic>> getWeatherGuide({
    required double lat,
    required double lng,
    String language = 'en',
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/ai/weather-guide',
      queryParameters: {'lat': lat, 'lng': lng, 'language': language},
    );
    return r.data!;
  }

  // --- Mood Travel (SILK-0131) ----------------------------------------------

  Future<Map<String, dynamic>> getMoodRecommendations({
    required String mood,
    double availableHours = 2.0,
    double? lat,
    double? lng,
    String language = 'en',
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/ai/mood-recommendations',
      data: {
        'mood': mood,
        'available_hours': availableHours,
        if (lat != null) 'lat': lat,
        if (lng != null) 'lng': lng,
        'language': language,
      },
    );
    return r.data!;
  }

  // --- Vision Recognition (SILK-0099) ----------------------------------------

  Future<Map<String, dynamic>> uploadMedia({
    required List<int> bytes,
    required String filename,
    required String mimeType,
    String kind = 'image',
  }) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        bytes,
        filename: filename,
        contentType: DioMediaType.parse(mimeType),
      ),
      'kind': kind,
      'license_type_slug': 'ugc',
    });
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/media/uploads',
      data: formData,
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> recognizeImage({
    required String mediaAssetId,
    String language = 'en',
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/ai/recognize',
      data: {'media_asset_id': mediaAssetId, 'language': language},
    );
    return r.data!;
  }

  // --- Photo Guide (SILK-0100) -----------------------------------------------

  Future<Map<String, dynamic>> getPhotoGuide({
    required String heritagePubId,
    String mode = 'angle',
    String language = 'en',
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/ai/photo-guide',
      data: {
        'heritage_pub_id': heritagePubId,
        'mode': mode,
        'language': language,
      },
    );
    return r.data!;
  }

  // --- ASR / Voice Assistant (SILK-0101) ------------------------------------

  Future<Map<String, dynamic>> transcribeAudio({
    required List<int> bytes,
    required String filename,
    String language = 'en',
  }) async {
    final formData = FormData.fromMap({
      'file': MultipartFile.fromBytes(
        bytes,
        filename: filename,
        contentType: DioMediaType.parse('audio/m4a'),
      ),
      'language': language,
    });
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/ai/asr',
      data: formData,
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> resolveVoiceIntent({
    required String transcript,
    String language = 'en',
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/ai/voice-intent',
      data: {'transcript': transcript, 'language': language},
    );
    return r.data!;
  }

  // --- Offline Bundles (SILK-0097) ------------------------------------------

  Future<Map<String, dynamic>> getOfflineBundles({
    String region = 'uz_all',
    String? language,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/offline/bundles',
      queryParameters: {
        'region': region,
        if (language != null) 'language': language,
      },
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> getOfflineBundleManifest({
    required String bundleId,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/offline/bundles/$bundleId/manifest',
    );
    return r.data!;
  }

  // --- Kids Story (SILK-0098) -----------------------------------------------

  Future<String?> getKidsStory({
    required String pubId,
    String language = 'uz',
  }) async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(
        '/v1/heritage/$pubId/kids-story',
        queryParameters: {'language': language},
      );
      return r.data?['story'] as String?;
    } on DioException {
      return null;
    }
  }

  // --- Heritage Cultural Tips (SILK-0098) -----------------------------------
  // Per-heritage-object tips (distinct from the global /v1/cultural-tips).

  Future<List<dynamic>> getHeritageCulturalTips({
    required String pubId,
    String language = 'uz',
  }) async {
    try {
      final r = await _dio.get<Map<String, dynamic>>(
        '/v1/heritage/$pubId/cultural-tips',
        queryParameters: {'language': language},
      );
      return (r.data?['items'] as List?) ?? [];
    } on DioException {
      return [];
    }
  }

  // --- Expense Tracker (SILK-0130) ------------------------------------------

  Future<Map<String, dynamic>> createBudget({
    required double totalBudgetUsd,
    String currency = 'USD',
    String? title,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/me/budget',
      data: {
        'total_budget_usd': totalBudgetUsd,
        'currency': currency,
        if (title != null) 'title': title,
      },
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> getExpenseSummary() async {
    final r = await _dio.get<Map<String, dynamic>>('/v1/me/expenses/summary');
    return r.data!;
  }

  Future<Map<String, dynamic>> addExpense({
    required double amountUsd,
    required String category,
    String? description,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/me/expenses',
      data: {
        'amount_usd': amountUsd,
        'category': category,
        if (description != null) 'description': description,
      },
    );
    return r.data!;
  }

  // --- Food Assistant (SILK-0133) -------------------------------------------

  Future<Map<String, dynamic>> getFoodRecommendations({
    required String message,
    String language = 'en',
    List<String>? dietaryPreferences,
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/ai/food-assistant',
      data: {
        'message': message,
        'language': language,
        if (dietaryPreferences != null && dietaryPreferences.isNotEmpty)
          'dietary_preferences': dietaryPreferences,
      },
    );
    return r.data!;
  }

  // --- Carbon Footprint (SILK-0134) -----------------------------------------

  Future<Map<String, dynamic>> calculateCarbonFootprint({
    required List<Map<String, dynamic>> journeyLegs,
    String language = 'en',
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/me/carbon-footprint',
      data: {
        'journey_legs': journeyLegs,
        'language': language,
      },
    );
    return r.data!;
  }

  // --- AI Utilities (SILK-0080) -----------------------------------------------

  Future<Map<String, dynamic>> checkFairPrice({
    required String item,
    required String market,
    String currency = 'USD',
    String language = 'en',
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/ai/fair-price',
      data: {'item': item, 'market': market, 'currency': currency, 'language': language},
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> checkScam({
    required String venueName,
    required String serviceDescription,
    required double quotedPriceUsd,
    String language = 'en',
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/ai/scam-check',
      data: {
        'venue_name': venueName,
        'service_description': serviceDescription,
        'quoted_price_usd': quotedPriceUsd,
        'language': language,
      },
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> getLostFoundHelp({
    required String itemType,
    double lat = 39.65,
    double lng = 66.97,
    String language = 'en',
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/ai/lost-found',
      queryParameters: {'item_type': itemType, 'lat': lat, 'lng': lng, 'language': language},
    );
    return r.data!;
  }

  // --- Government Info (SILK-0086) ------------------------------------------

  Future<List<dynamic>> getGovernmentInfo({
    String countryCode = 'UZ',
    String language = 'en',
    String? kind,
  }) async {
    final r = await _dio.get<List<dynamic>>(
      '/v1/government',
      queryParameters: {
        'country_code': countryCode,
        'language': language,
        if (kind != null) 'kind': kind,
      },
    );
    return r.data ?? [];
  }

  // --- Memory Book (SILK-0076) -----------------------------------------------

  Future<Map<String, dynamic>> getMemoryBookPreview({int limit = 5}) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/me/memory-book/preview',
      queryParameters: {'limit': limit},
    );
    return r.data!;
  }

  Future<Map<String, dynamic>> generateMemoryBook({
    String? title,
    String? dateFrom,
    String? dateTo,
    String language = 'en',
    String format = 'json',
  }) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/me/memory-book/generate',
      data: {
        if (title != null) 'title': title,
        if (dateFrom != null) 'date_from': dateFrom,
        if (dateTo != null) 'date_to': dateTo,
        'language': language,
        'format': format,
      },
    );
    return r.data!;
  }

  // --- Ticket QR (SILK-0126) ------------------------------------------------

  Future<Map<String, dynamic>> getTicketQr(String ticketId) async {
    final r = await _dio.get<Map<String, dynamic>>('/v1/tickets/$ticketId/qr');
    return r.data!;
  }

  // --- Nearest Emergency (SILK-0127) ----------------------------------------

  Future<List<Map<String, dynamic>>> getNearestEmergency({
    required double lat,
    required double lng,
    String kind = 'hospital',
    String language = 'en',
    int limit = 3,
  }) async {
    final r = await _dio.get<List<dynamic>>(
      '/v1/emergency/nearest',
      queryParameters: {
        'lat': lat,
        'lng': lng,
        'kind': kind,
        'language': language,
        'limit': limit,
      },
    );
    return (r.data ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  // --- Health Tips (SILK-0129) -----------------------------------------------

  Future<Map<String, dynamic>> getHealthTips({
    double temperatureC = 25,
    String activity = 'walking',
    String language = 'en',
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/ai/health-tips',
      queryParameters: {
        'temperature_c': temperatureC,
        'activity': activity,
        'language': language,
      },
    );
    return r.data!;
  }

  // --- Budget list (SILK-0130) -----------------------------------------------

  Future<List<Map<String, dynamic>>> listBudgets() async {
    final r = await _dio.get<List<dynamic>>('/v1/me/budget');
    return (r.data ?? [])
        .map((e) => Map<String, dynamic>.from(e as Map))
        .toList();
  }

  // --- Listings search (SILK-0133) ------------------------------------------

  Future<Map<String, dynamic>> searchListings({
    required String category,
    double? lat,
    double? lng,
    double radiusKm = 10,
    String? dietary,
    String? city,
    String language = 'en',
    int limit = 20,
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/listings',
      queryParameters: {
        'category': category,
        if (lat != null) 'lat': lat,
        if (lng != null) 'lng': lng,
        'radius_km': radiusKm,
        if (dietary != null) 'dietary': dietary,
        if (city != null) 'city': city,
        'language': language,
        'limit': limit,
      },
    );
    return r.data!;
  }

  // --- Crowd Forecast (SILK-0138) -------------------------------------------

  Future<Map<String, dynamic>> getCrowdForecast(
    String heritagePubId, {
    String language = 'en',
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/heritage/$heritagePubId/crowd-forecast',
      queryParameters: {'language': language},
    );
    return r.data!;
  }

  // --- Check-in (SILK-0138) -------------------------------------------------

  Future<Map<String, dynamic>> checkIn(String heritagePubId) async {
    final r = await _dio.post<Map<String, dynamic>>(
      '/v1/me/check-in',
      data: {'heritage_pub_id': heritagePubId},
    );
    return r.data!;
  }

  // --- Review Analysis (SILK-0138) ------------------------------------------

  Future<Map<String, dynamic>> getReviewAnalysis(
    String heritagePubId, {
    String language = 'en',
  }) async {
    final r = await _dio.get<Map<String, dynamic>>(
      '/v1/heritage/$heritagePubId/reviews/analysis',
      queryParameters: {'language': language},
    );
    return r.data!;
  }
}
