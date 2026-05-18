// Pure-Dart domain test. No Flutter binding required.

import "package:flutter_test/flutter_test.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";

void main() {
  group("Heritage entity", () {
    test("hasGeolocation is false when coordinates are null", () {
      const h = Heritage(id: "h1", name: "Registan");
      expect(h.hasGeolocation, isFalse);
    });

    test("hasGeolocation is true when both lat & lng are set", () {
      const h = Heritage(id: "h1", name: "Registan", latitude: 39.65, longitude: 66.97);
      expect(h.hasGeolocation, isTrue);
    });
  });
}
