// Retrofit-generated REST client. The actual .g.dart file is produced by
// `dart run build_runner build` on a contributor machine. Until then the
// abstract class itself is enough to drive imports and let the IDE find
// symbols.
//
// Per ADR-0003: repositories depend on this client. Domain code does not.

import "package:dio/dio.dart";
import "package:retrofit/retrofit.dart";
import "package:silklens/core/network/api_endpoints.dart";
import "package:silklens/data/api/dto/auth_dto.dart";
import "package:silklens/data/api/dto/branding_dto.dart";
import "package:silklens/data/api/dto/heritage_dto.dart";
import "package:silklens/data/api/dto/tenant_branding_dto.dart";
import "package:silklens/data/api/dto/version_dto.dart";
import "package:silklens/data/api/dto/vocab_dto.dart";

part "silklens_api_client.g.dart";

@RestApi()
abstract class SilkLensApiClient {
  factory SilkLensApiClient(Dio dio, {String baseUrl}) = _SilkLensApiClient;

  // --- Meta ----------------------------------------------------------------

  @GET(ApiEndpoints.version)
  Future<VersionDto> getVersion();

  // Legacy alias — kept for the tenant_branding admin endpoint (FAZA 1).
  // New code uses [getBranding] which hits `/v1/branding`.
  @GET(ApiEndpoints.tenantBranding)
  Future<TenantBrandingDto> getTenantBranding();

  @GET(ApiEndpoints.branding)
  Future<BrandingDto> getBranding({
    @Query("tenant") String? tenantSlug,
  });

  @GET("/v1/vocab/{slug}")
  Future<VocabDto> getVocabulary(@Path("slug") String slug);

  // --- Auth ----------------------------------------------------------------

  @POST(ApiEndpoints.authRegister)
  Future<LoginResponseDto> register(@Body() RegisterRequestDto body);

  @POST(ApiEndpoints.authLogin)
  Future<LoginResponseDto> login(@Body() LoginRequestDto body);

  @POST(ApiEndpoints.authRefresh)
  Future<LoginResponseDto> refresh(@Body() RefreshRequestDto body);

  @POST(ApiEndpoints.authLogout)
  Future<LogoutResponseDto> logout();

  @GET(ApiEndpoints.authMe)
  Future<MeResponseDto> me();

  // --- Heritage ------------------------------------------------------------

  @GET(ApiEndpoints.heritageList)
  Future<HeritagePageDto> listHeritage({
    @Query("kind") String? kind,
    @Query("country") String? country,
    @Query("status") String? status,
    @Query("search") String? search,
    @Query("limit") int limit = 20,
    @Query("offset") int offset = 0,
  });

  @GET("/v1/heritage/{pubId}")
  Future<HeritageDto> getHeritage(@Path("pubId") String pubId);
}
