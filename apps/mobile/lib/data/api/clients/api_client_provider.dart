// Single source of truth for the retrofit-generated API client.
//
// The repository implementations (auth, heritage, branding, ...) all
// watch this provider. The composition root (main.dart) overrides it with
// a real client once `dart run build_runner build` has produced
// `silklens_api_client.g.dart`.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';
import 'package:silklens/data/api/dio_client.dart';

final Provider<SilkLensApiClient> silkLensApiClientProvider = Provider<SilkLensApiClient>(
  (Ref ref) => SilkLensApiClient(ref.watch(dioProvider)),
  name: 'silkLensApiClientProvider',
);
