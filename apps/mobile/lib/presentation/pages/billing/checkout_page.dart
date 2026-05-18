// Checkout — collect a payment method token and start the subscription.
//
// When a Stripe publishable key is configured we'll wire up flutter_stripe in
// a follow-up; for FAZA 1 we accept a manual token field. The "Mock payment"
// button generates a tokenised string for development builds so the UX flow
// can be exercised end-to-end against the backend.

import "package:flutter/material.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/billing_provider.dart";
import "package:uuid/uuid.dart";

class CheckoutPage extends ConsumerStatefulWidget {
  const CheckoutPage({required this.planSlug, super.key});

  final String planSlug;

  @override
  ConsumerState<CheckoutPage> createState() => _CheckoutPageState();
}

class _CheckoutPageState extends ConsumerState<CheckoutPage> {
  final TextEditingController _tokenController = TextEditingController();
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _tokenController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() {
      _submitting = true;
      _error = null;
    });
    final token = _tokenController.text.trim();
    if (token.isEmpty) {
      setState(() {
        _submitting = false;
        _error = "missing_token";
      });
      return;
    }
    final Result result = await ref
        .read(mySubscriptionProvider.notifier)
        .startCheckout(planSlug: widget.planSlug, paymentMethodToken: token);
    if (!mounted) return;
    setState(() => _submitting = false);
    if (result.isSuccess) {
      context.go("/billing/manage");
    } else {
      setState(() => _error = result.failureOrNull?.message);
    }
  }

  void _generateMockToken() {
    _tokenController.text = "mock_tok_${const Uuid().v4()}";
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(l10n?.billingCheckoutTitle ?? "Checkout")),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: <Widget>[
            Text(
              l10n?.billingCheckoutSubtitle ??
                  "Enter your payment method to subscribe",
              style: Theme.of(context).textTheme.bodyLarge,
            ),
            const SizedBox(height: 16),
            TextField(
              key: const Key("billing.checkout.token"),
              controller: _tokenController,
              decoration: InputDecoration(
                border: const OutlineInputBorder(),
                labelText: l10n?.billingCheckoutToken ?? "Payment token",
                errorText: _error,
              ),
            ),
            const SizedBox(height: 8),
            TextButton.icon(
              key: const Key("billing.checkout.mock"),
              onPressed: _generateMockToken,
              icon: const Icon(Icons.bug_report_outlined),
              label: Text(
                l10n?.billingCheckoutMock ?? "Mock payment (development only)",
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              key: const Key("billing.checkout.submit"),
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(
                      height: 18,
                      width: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : Text(l10n?.billingCheckoutSubmit ?? "Subscribe"),
            ),
          ],
        ),
      ),
    );
  }
}
