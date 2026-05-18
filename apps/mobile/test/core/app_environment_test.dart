import "package:flutter_test/flutter_test.dart";
import "package:silklens/core/env/app_environment.dart";

void main() {
  group("AppEnvironment.fromDotEnv", () {
    test("falls back to defaults when env is empty", () {
      final env = AppEnvironment.fromDotEnv(const <String, String>{});
      expect(env.appName, equals("SilkLens"));
      expect(env.appEnv, equals("local"));
      expect(env.defaultLocale, equals("uz"));
      expect(env.apiBaseUrl.startsWith("http"), isTrue);
    });

    test("uses API_BASE_URL_OVERRIDE when set", () {
      final env = AppEnvironment.fromDotEnv(const <String, String>{
        "API_BASE_URL_OVERRIDE": "http://192.168.0.10:8000",
      });
      expect(env.apiBaseUrl, equals("http://192.168.0.10:8000"));
    });
  });
}
