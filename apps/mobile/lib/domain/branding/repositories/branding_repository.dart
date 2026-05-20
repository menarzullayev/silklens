// Domain protocol for tenant branding.
//
// Implementation lives in `lib/data/repositories/branding_repository_impl.dart`.
// The presentation layer reads through `brandingProvider` and never imports
// the implementation directly (Clean Architecture invariant).

import 'package:silklens/core/utils/result.dart';
import 'package:silklens/domain/branding/entities/branding.dart';

abstract interface class BrandingRepository {
  /// Fetches branding from the live API and writes it to the Isar cache.
  /// On network error the cached value is returned if present.
  Future<Result<Branding>> fetch({String? tenantSlug});

  /// One-shot read from the local cache. Returns `null` when nothing has
  /// been cached yet (cold start without network).
  Future<Branding?> cached({String? tenantSlug});
}
