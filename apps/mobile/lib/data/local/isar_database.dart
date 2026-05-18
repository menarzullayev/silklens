// Isar database open/close wrapper.
//
// Master Architecture §8 — offline-first L1/L2 storage lives here. The
// schemas under `lib/data/local/schemas/` are added to the constructor
// below; they generate `*.g.dart` files (e.g. `cached_heritage_schema.g.dart`)
// that expose a `CachedHeritageSchema` constant we register.
//
// During the FAZA 1 skeleton we ship just one schema (`CachedHeritage`) so
// the boot path can be exercised end-to-end without dragging the whole
// offline-bundle subsystem in.

import "dart:async";

import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:isar/isar.dart";
import "package:path_provider/path_provider.dart";
import "package:silklens/data/local/schemas/cached_heritage.dart";

class IsarDatabase {
  IsarDatabase._(this.instance);

  final Isar instance;

  static Future<IsarDatabase> open() async {
    final dir = await getApplicationDocumentsDirectory();
    final isar = await Isar.open(
      <CollectionSchema<dynamic>>[
        CachedHeritageSchema,
      ],
      directory: dir.path,
      name: "silklens",
      inspector: false,
    );
    return IsarDatabase._(isar);
  }

  Future<void> close() => instance.close();
}

/// Always overridden in `main.dart`. The default `throw` keeps a missed
/// override loud rather than silently constructing an unused stub.
final Provider<IsarDatabase> isarDatabaseProvider = Provider<IsarDatabase>(
  (Ref ref) => throw UnimplementedError(
    "isarDatabaseProvider must be overridden in main.dart with an opened IsarDatabase.",
  ),
  name: "isarDatabaseProvider",
);
