// SILK-0104 — Billing Riverpod state.
//
// BillingNotifier loads plans, current subscription, and entitlements in
// parallel on first build. Pages watch `billingProvider` for plans/manage
// screens and `invoicesProvider` for the invoices list.

import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/data/repositories/billing_repository_impl.dart';

// ─── State ───────────────────────────────────────────────────────────────────

class BillingState {
  const BillingState({
    this.plans = const [],
    this.currentSubscription,
    this.entitlements = const [],
    this.isLoading = false,
    this.isCancelling = false,
    this.isValidatingCoupon = false,
    this.error,
    this.billingCycle = 'monthly',
    this.couponResult,
  });

  final List<Map<String, dynamic>> plans;
  final Map<String, dynamic>? currentSubscription;
  final List<Map<String, dynamic>> entitlements;
  final bool isLoading;
  final bool isCancelling;
  final bool isValidatingCoupon;
  final String? error;
  /// 'monthly' or 'yearly'
  final String billingCycle;
  final Map<String, dynamic>? couponResult;

  bool get hasActiveSubscription =>
      currentSubscription != null &&
      (currentSubscription!['status'] == 'active' ||
          currentSubscription!['status'] == 'trialing');

  bool get cancelAtPeriodEnd =>
      currentSubscription?['cancel_at_period_end'] as bool? ?? false;

  String get currentPlanSlug =>
      currentSubscription?['plan_slug'] as String? ?? 'free';

  BillingState copyWith({
    List<Map<String, dynamic>>? plans,
    Map<String, dynamic>? currentSubscription,
    bool clearSubscription = false,
    List<Map<String, dynamic>>? entitlements,
    bool? isLoading,
    bool? isCancelling,
    bool? isValidatingCoupon,
    String? error,
    bool clearError = false,
    String? billingCycle,
    Map<String, dynamic>? couponResult,
    bool clearCoupon = false,
  }) =>
      BillingState(
        plans: plans ?? this.plans,
        currentSubscription: clearSubscription
            ? null
            : (currentSubscription ?? this.currentSubscription),
        entitlements: entitlements ?? this.entitlements,
        isLoading: isLoading ?? this.isLoading,
        isCancelling: isCancelling ?? this.isCancelling,
        isValidatingCoupon: isValidatingCoupon ?? this.isValidatingCoupon,
        error: clearError ? null : (error ?? this.error),
        billingCycle: billingCycle ?? this.billingCycle,
        couponResult: clearCoupon ? null : (couponResult ?? this.couponResult),
      );
}

// ─── Notifier ────────────────────────────────────────────────────────────────

class BillingNotifier extends Notifier<BillingState> {
  @override
  BillingState build() {
    Future.microtask(refresh);
    return const BillingState(isLoading: true);
  }

  Future<void> refresh() async {
    state = state.copyWith(isLoading: true, clearError: true);
    try {
      final repo = ref.read(billingRepositoryProvider);
      final results = await Future.wait([
        repo.getPlans(),
        repo.getCurrentSubscription(),
        repo.getEntitlements(),
      ]);

      final plansData = results[0]! as Map<String, dynamic>;
      final sub = results[1] as Map<String, dynamic>?;
      final ents = results[2]! as List<dynamic>;

      state = state.copyWith(
        plans: ((plansData['items'] as List?) ?? [])
            .cast<Map<String, dynamic>>(),
        currentSubscription: sub,
        clearSubscription: sub == null,
        entitlements: ents.cast<Map<String, dynamic>>(),
        isLoading: false,
      );
    } catch (e) {
      state = state.copyWith(isLoading: false, error: e.toString());
    }
  }

  void setBillingCycle(String cycle) {
    assert(cycle == 'monthly' || cycle == 'yearly');
    state = state.copyWith(billingCycle: cycle);
  }

  /// Returns true if cancellation succeeded.
  Future<bool> cancelSubscription() async {
    state = state.copyWith(isCancelling: true, clearError: true);
    try {
      await ref
          .read(billingRepositoryProvider)
          .cancelSubscription(atPeriodEnd: true);
      // Optimistically reflect cancellation flag.
      final updated = state.currentSubscription != null
          ? Map<String, dynamic>.from(state.currentSubscription!)
          : <String, dynamic>{};
      updated['cancel_at_period_end'] = true;
      state = state.copyWith(
        isCancelling: false,
        currentSubscription: updated,
      );
      return true;
    } catch (e) {
      state = state.copyWith(isCancelling: false, error: e.toString());
      return false;
    }
  }

  /// Returns true if resumption succeeded.
  Future<bool> resumeSubscription() async {
    state = state.copyWith(isCancelling: true, clearError: true);
    try {
      await ref.read(billingRepositoryProvider).resumeSubscription();
      final updated = state.currentSubscription != null
          ? Map<String, dynamic>.from(state.currentSubscription!)
          : <String, dynamic>{};
      updated['cancel_at_period_end'] = false;
      state = state.copyWith(
        isCancelling: false,
        currentSubscription: updated,
      );
      return true;
    } catch (e) {
      state = state.copyWith(isCancelling: false, error: e.toString());
      return false;
    }
  }

  /// Validates a coupon code. Returns true when valid, false otherwise.
  Future<bool> validateCoupon(String code, double orderValueUsd) async {
    state = state.copyWith(isValidatingCoupon: true, clearError: true);
    try {
      final result = await ref
          .read(billingRepositoryProvider)
          .validateCoupon(code, orderValueUsd);
      state = state.copyWith(
        isValidatingCoupon: false,
        couponResult: result,
        clearCoupon: result == null,
      );
      return result != null;
    } catch (e) {
      state = state.copyWith(
        isValidatingCoupon: false,
        clearCoupon: true,
        error: e.toString(),
      );
      return false;
    }
  }

  void clearCoupon() => state = state.copyWith(clearCoupon: true);
}

// ─── Providers ───────────────────────────────────────────────────────────────

final billingProvider = NotifierProvider<BillingNotifier, BillingState>(
  BillingNotifier.new,
);

/// Separate FutureProvider so the invoices list can be independently
/// refreshed without rebuilding the full billing state.
final invoicesProvider =
    FutureProvider<List<Map<String, dynamic>>>((ref) async {
  final repo = ref.watch(billingRepositoryProvider);
  final items = await repo.getInvoices();
  return items.cast<Map<String, dynamic>>();
});
