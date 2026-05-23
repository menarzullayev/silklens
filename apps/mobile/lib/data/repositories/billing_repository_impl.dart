// SILK-0104 — Billing repository implementation.
// Wraps SilkLensApiClient billing methods and exposes them via Riverpod.
//
// Per ADR-0003: domain code must not import this file; only presentation
// providers may read `billingRepositoryProvider`.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/data/api/clients/silklens_api_client.dart';

class BillingRepositoryImpl {
  const BillingRepositoryImpl(this._client);
  final SilkLensApiClient _client;

  Future<Map<String, dynamic>> getPlans() =>
      _client.getBillingPlans(pricingZone: 'central_asia');

  Future<Map<String, dynamic>?> getCurrentSubscription() =>
      _client.getCurrentSubscription();

  Future<List<dynamic>> getInvoices({int limit = 20, int offset = 0}) =>
      _client.getInvoices(limit: limit, offset: offset);

  Future<List<dynamic>> getEntitlements() => _client.getEntitlements();

  /// Creates a subscription and returns the `subscription` map from the
  /// response envelope. Uses a millisecond-epoch idempotency key to guard
  /// against double-charges on network retry.
  Future<Map<String, dynamic>> startSubscription({
    required String planSlug,
    required String paymentMethodToken,
    String pricingZoneSlug = 'central_asia',
  }) async {
    final key = DateTime.now().millisecondsSinceEpoch.toString();
    final data = await _client.createSubscription(
      planSlug: planSlug,
      paymentMethodToken: paymentMethodToken,
      pricingZoneSlug: pricingZoneSlug,
      idempotencyKey: key,
    );
    final sub = data['subscription'] as Map<String, dynamic>?;
    if (sub == null) {
      throw Exception(
        'createSubscription: missing subscription in response',
      );
    }
    return sub;
  }

  Future<void> cancelSubscription({bool atPeriodEnd = true}) =>
      _client.cancelSubscription(atPeriodEnd: atPeriodEnd);

  Future<void> resumeSubscription() => _client.resumeSubscription();

  Future<Map<String, dynamic>?> validateCoupon(
    String code,
    double orderValueUsd,
  ) =>
      _client.validateCoupon(code, orderValueUsd);
}

final billingRepositoryProvider = Provider<BillingRepositoryImpl>((ref) {
  return BillingRepositoryImpl(ref.watch(silkLensApiClientProvider));
});
