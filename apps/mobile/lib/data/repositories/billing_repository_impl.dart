// HTTP-backed [BillingRepository]. Plans / subscription / invoices.

import "package:dio/dio.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/api/dio_client.dart";
import "package:silklens/domain/billing/entities/invoice.dart";
import "package:silklens/domain/billing/entities/subscription.dart";
import "package:silklens/domain/billing/entities/subscription_plan.dart";
import "package:silklens/domain/billing/repositories/billing_repository.dart";

class BillingRepositoryImpl implements BillingRepository {
  BillingRepositoryImpl({required Dio dio}) : _dio = dio;

  final Dio _dio;

  @override
  Future<Result<List<SubscriptionPlan>>> plans() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>("/v1/billing/plans");
      final items = (response.data?["items"] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .map(_parsePlan)
          .toList(growable: false);
      return Success<List<SubscriptionPlan>>(items);
    } on DioException catch (e, st) {
      return FailureResult<List<SubscriptionPlan>>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<Subscription>> mySubscription() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        "/v1/billing/me/subscription",
      );
      return Success<Subscription>(
        _parseSubscription(response.data ?? const <String, dynamic>{}),
      );
    } on DioException catch (e, st) {
      return FailureResult<Subscription>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<List<String>>> myEntitlements() async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        "/v1/billing/me/entitlements",
      );
      final items = (response.data?["items"] as List<dynamic>? ?? const <dynamic>[])
          .whereType<String>()
          .toList(growable: false);
      return Success<List<String>>(items);
    } on DioException catch (e, st) {
      return FailureResult<List<String>>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<Subscription>> startSubscription({
    required String planSlug,
    required String paymentMethodToken,
    required String idempotencyKey,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/v1/billing/subscriptions",
        data: <String, dynamic>{
          "plan_slug": planSlug,
          "payment_method_token": paymentMethodToken,
        },
        options: Options(headers: <String, String>{
          "Idempotency-Key": idempotencyKey,
        }),
      );
      return Success<Subscription>(
        _parseSubscription(response.data ?? const <String, dynamic>{}),
      );
    } on DioException catch (e, st) {
      return FailureResult<Subscription>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<Subscription>> cancelSubscription() async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/v1/billing/subscriptions/cancel",
      );
      return Success<Subscription>(
        _parseSubscription(response.data ?? const <String, dynamic>{}),
      );
    } on DioException catch (e, st) {
      return FailureResult<Subscription>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<Subscription>> resumeSubscription() async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/v1/billing/subscriptions/resume",
      );
      return Success<Subscription>(
        _parseSubscription(response.data ?? const <String, dynamic>{}),
      );
    } on DioException catch (e, st) {
      return FailureResult<Subscription>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<List<Invoice>>> invoices({int page = 1, int pageSize = 20}) async {
    try {
      final response = await _dio.get<Map<String, dynamic>>(
        "/v1/billing/me/invoices",
        queryParameters: <String, dynamic>{
          "page": page,
          "page_size": pageSize,
        },
      );
      final items = (response.data?["items"] as List<dynamic>? ?? const <dynamic>[])
          .whereType<Map<String, dynamic>>()
          .map(_parseInvoice)
          .toList(growable: false);
      return Success<List<Invoice>>(items);
    } on DioException catch (e, st) {
      return FailureResult<List<Invoice>>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  SubscriptionPlan _parsePlan(Map<String, dynamic> json) => SubscriptionPlan(
        slug: json["slug"] as String? ?? "",
        name: json["name"] as String? ?? "",
        interval: switch (json["interval"] as String?) {
          "year" => PlanInterval.year,
          "lifetime" => PlanInterval.lifetime,
          _ => PlanInterval.month,
        },
        amountMinor: (json["amount_minor"] as int?) ?? 0,
        currency: json["currency"] as String? ?? "USD",
        pricingZone: json["pricing_zone"] as String? ?? "GLOBAL",
        features: (json["features"] as List<dynamic>? ?? const <dynamic>[])
            .whereType<String>()
            .toList(growable: false),
        isFree: (json["is_free"] as bool?) ?? false,
        isHighlighted: (json["is_highlighted"] as bool?) ?? false,
      );

  Subscription _parseSubscription(Map<String, dynamic> json) {
    SubscriptionStatus parseStatus(String? raw) => switch (raw) {
          "active" => SubscriptionStatus.active,
          "trialing" => SubscriptionStatus.trialing,
          "past_due" => SubscriptionStatus.pastDue,
          "canceled" => SubscriptionStatus.canceled,
          "paused" => SubscriptionStatus.paused,
          _ => SubscriptionStatus.none,
        };

    DateTime? parseDate(Object? raw) =>
        raw is String ? DateTime.tryParse(raw) : null;

    return Subscription(
      status: parseStatus(json["status"] as String?),
      planSlug: json["plan_slug"] as String? ?? "",
      planName: json["plan_name"] as String?,
      currentPeriodStart: parseDate(json["current_period_start"]),
      currentPeriodEnd: parseDate(json["current_period_end"]),
      cancelAt: parseDate(json["cancel_at"]),
      cancelAtPeriodEnd: (json["cancel_at_period_end"] as bool?) ?? false,
    );
  }

  Invoice _parseInvoice(Map<String, dynamic> json) {
    InvoiceStatus parseStatus(String? raw) => switch (raw) {
          "paid" => InvoiceStatus.paid,
          "voided" => InvoiceStatus.voided,
          "uncollectible" => InvoiceStatus.uncollectible,
          _ => InvoiceStatus.open,
        };
    return Invoice(
      id: json["id"] as String? ?? "",
      status: parseStatus(json["status"] as String?),
      amountMinor: (json["amount_minor"] as int?) ?? 0,
      currency: json["currency"] as String? ?? "USD",
      issuedAt: DateTime.tryParse(json["issued_at"] as String? ?? "") ??
          DateTime.now().toUtc(),
      paidAt: json["paid_at"] is String
          ? DateTime.tryParse(json["paid_at"] as String)
          : null,
      hostedUrl: json["hosted_url"] as String?,
    );
  }
}

final Provider<BillingRepository> billingRepositoryProvider =
    Provider<BillingRepository>(
  (Ref ref) => BillingRepositoryImpl(dio: ref.watch(dioProvider)),
  name: "billingRepositoryProvider",
);
