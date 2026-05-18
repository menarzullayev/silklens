// Pure-Dart domain tests. No Flutter binding required.

import "package:flutter_test/flutter_test.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";

void main() {
  group("Heritage entity", () {
    test("hasGeolocation is false when coordinates are null", () {
      const h = Heritage(
        id: "h1",
        pubId: "h1",
        kindSlug: "monument",
        name: <String, String>{"en": "Registan"},
      );
      expect(h.hasGeolocation, isFalse);
    });

    test("hasGeolocation is true when both lat & lng are set", () {
      const h = Heritage(
        id: "h1",
        pubId: "h1",
        kindSlug: "monument",
        name: <String, String>{"en": "Registan"},
        latitude: 39.65,
        longitude: 66.97,
      );
      expect(h.hasGeolocation, isTrue);
    });

    test("localizedName falls back to English when locale missing", () {
      const h = Heritage(
        id: "h1",
        pubId: "h1",
        kindSlug: "monument",
        name: <String, String>{"en": "Registan", "uz": "Registon"},
      );
      expect(h.localizedName("uz"), "Registon");
      expect(h.localizedName("fr"), "Registan"); // fallback
    });

    test("periodLabel formats single year and range", () {
      const single = Heritage(
        id: "h",
        pubId: "h",
        kindSlug: "monument",
        name: <String, String>{"en": "Test"},
        periodStartYear: 1417,
        periodEndYear: 1417,
      );
      expect(single.periodLabel, "1417");

      const range = Heritage(
        id: "h",
        pubId: "h",
        kindSlug: "monument",
        name: <String, String>{"en": "Test"},
        periodStartYear: 1417,
        periodEndYear: 1420,
      );
      expect(range.periodLabel, "1417 – 1420");

      const bce = Heritage(
        id: "h",
        pubId: "h",
        kindSlug: "monument",
        name: <String, String>{"en": "Test"},
        periodStartYear: -500,
      );
      expect(bce.periodLabel, "500 BCE");
    });

    test("isUnescoListed reflects unescoInscriptionYear", () {
      const a = Heritage(
        id: "h",
        pubId: "h",
        kindSlug: "monument",
        name: <String, String>{"en": "Test"},
      );
      const b = Heritage(
        id: "h",
        pubId: "h",
        kindSlug: "monument",
        name: <String, String>{"en": "Test"},
        unescoInscriptionYear: 2001,
      );
      expect(a.isUnescoListed, isFalse);
      expect(b.isUnescoListed, isTrue);
    });
  });

  group("HeritagePage", () {
    test("hasMore reflects offset + items.length vs total", () {
      const page = HeritagePage(
        items: <Heritage>[],
        total: 100,
        limit: 20,
        offset: 0,
      );
      expect(page.hasMore, isTrue);

      const full = HeritagePage(
        items: <Heritage>[
          Heritage(
            id: "1",
            pubId: "1",
            kindSlug: "k",
            name: <String, String>{"en": "x"},
          ),
        ],
        total: 1,
        limit: 20,
        offset: 0,
      );
      expect(full.hasMore, isFalse);
    });
  });
}
