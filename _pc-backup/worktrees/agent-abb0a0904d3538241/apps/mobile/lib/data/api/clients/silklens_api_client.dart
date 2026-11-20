// Plain Dio HTTP client — retrofit dependency removed for FAZA 1 device testing.
// Per ADR-0003: repositories depend on this client. Domain code does not.

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
}
