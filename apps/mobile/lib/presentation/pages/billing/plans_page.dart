// /v1/billing/plans → cards for Free / Premium Monthly / Premium Yearly.
//
// `pricingZone` is resolved server-side from the device country. We do not
// re-compute zones client-side — we just render the price + currency the API
// returns.

import "package:flutter/material.dart";
import "package:go_router/go_router.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/domain/billing/entities/subscription_plan.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/billing_provider.dart";

class PlansPage extends ConsumerWidget {
  const PlansPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final asyncPlans = ref.watch(plansProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n?.billingPlansTitle ?? "Choose a plan")),
      body: asyncPlans.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (Object e, _) => Center(child: Text(e.toString())),
        data: (plans) {
          if (plans.isEmpty) {
            return Center(
              key: const Key("billing.plans.empty"),
              child: Text(l10n?.billingPlansEmpty ?? "No plans available"),
            );
          }
          return ListView.builder(
            key: const Key("billing.plans.list"),
            padding: const EdgeInsets.all(16),
            itemCount: plans.length,
            itemBuilder: (BuildContext ctx, int i) =>
                _PlanCard(plan: plans[i]),
          );
        },
      ),
    );
  }
}

class _PlanCard extends StatelessWidget {
  const _PlanCard({required this.plan});

  final SubscriptionPlan plan;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final l10n = AppLocalizations.of(context);
    final periodLabel = switch (plan.interval) {
      PlanInterval.month => l10n?.billingPerMonth ?? "/month",
      PlanInterval.year => l10n?.billingPerYear ?? "/year",
      PlanInterval.lifetime => "",
    };
    return Card(
      key: Key("billing.plan.${plan.slug}"),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: plan.isHighlighted
            ? BorderSide(color: theme.colorScheme.primary, width: 2)
            : BorderSide.none,
      ),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: <Widget>[
            Text(plan.name, style: theme.textTheme.titleLarge),
            const SizedBox(height: 4),
            Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: <Widget>[
                Text(
                  plan.isFree
                      ? (l10n?.billingFreeLabel ?? "Free")
                      : "${plan.currency} ${plan.amountMajor.toStringAsFixed(2)}",
                  style: theme.textTheme.headlineMedium,
                ),
                Text(periodLabel, style: theme.textTheme.bodyLarge),
              ],
            ),
            const SizedBox(height: 12),
            ...plan.features.map(
              (String f) => Padding(
                padding: const EdgeInsets.symmetric(vertical: 2),
                child: Row(
                  children: <Widget>[
                    Icon(Icons.check, color: theme.colorScheme.primary, size: 18),
                    const SizedBox(width: 8),
                    Expanded(child: Text(f)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),
            FilledButton(
              key: Key("billing.plan.${plan.slug}.select"),
              onPressed: plan.isFree
                  ? null
                  : () => context.push("/billing/checkout/${plan.slug}"),
              child: Text(plan.isFree
                  ? (l10n?.billingCurrentPlan ?? "Current")
                  : (l10n?.billingChoosePlan ?? "Choose")),
            ),
          ],
        ),
      ),
    );
  }
}
