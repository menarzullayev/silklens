// Retrofit-generated REST client. The actual .g.dart file is produced by
// `dart run build_runner build`. Until then the abstract class itself is
// enough to drive imports and let the IDE find symbols.
//
// Per ADR-0003: repositories depend on this client. Domain code does not.

import "package:dio/dio.dart";
import "package:retrofit/retrofit.dart";
import "package:silklens/core/network/api_endpoints.dart";
import "package:silklens/data/api/dto/heritage_dto.dart";
import "package:silklens/data/api/dto/tenant_branding_dto.dart";
import "package:silklens/data/api/dto/version_dto.dart";

part "silklens_api_client.g.dart";

@RestApi()
abstract class SilkLensApiClient {
  factory SilkLensApiClient(Dio dio, {String baseUrl}) = _SilkLensApiClient;

  @GET(ApiEndpoints.version)
  Future<VersionDto> getVersion();

  @GET(ApiEndpoints.tenantBranding)
  Future<TenantBrandingDto> getTenantBranding();

  @GET(ApiEndpoints.heritageList)
  Future<List<HeritageDto>> listHeritage({
    @Query("q") String? query,
    @Query("page") int page = 1,
    @Query("page_size") int pageSize = 20,
  });

  @GET("/v1/heritage/{id}")
  Future<HeritageDto> getHeritage(@Path("id") String id);
}
