// Manage current subscription — cancel / resume + period info.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/domain/billing/entities/subscription.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/billing_provider.dart";

class ManageSubscriptionPage extends ConsumerWidget {
  const ManageSubscriptionPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final asyncSub = ref.watch(mySubscriptionProvider);
    return Scaffold(
      appBar: AppBar(
        title: Text(l10n?.billingManageTitle ?? "Manage subscription"),
      ),
      body: asyncSub.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (Object e, _) => Center(child: Text(e.toString())),
        data: (Subscription? sub) {
          if (sub == null || sub.status == SubscriptionStatus.none) {
            return Center(
              key: const Key("billing.manage.empty"),
              child: Text(l10n?.billingNoActive ?? "No active subscription"),
            );
          }
          return ListView(
            key: const Key("billing.manage.body"),
            padding: const EdgeInsets.all(20),
            children: <Widget>[
              ListTile(
                title: Text(sub.planName ?? sub.planSlug),
                subtitle: Text(sub.status.name),
              ),
              if (sub.currentPeriodEnd != null)
                ListTile(
                  leading: const Icon(Icons.calendar_today),
                  title: Text(
                    l10n?.billingRenewsOn ?? "Renews on",
                  ),
                  subtitle: Text(sub.currentPeriodEnd!.toLocal().toIso8601String()),
                ),
              const SizedBox(height: 16),
              if (sub.isActive && !sub.cancelAtPeriodEnd)
                FilledButton.tonal(
                  key: const Key("billing.manage.cancel"),
                  onPressed: () =>
                      ref.read(mySubscriptionProvider.notifier).cancel(),
                  child: Text(l10n?.billingCancel ?? "Cancel"),
                ),
              if (sub.cancelAtPeriodEnd ||
                  sub.status == SubscriptionStatus.canceled)
                FilledButton(
                  key: const Key("billing.manage.resume"),
                  onPressed: () =>
                      ref.read(mySubscriptionProvider.notifier).resume(),
                  child: Text(l10n?.billingResume ?? "Resume"),
                ),
            ],
          );
        },
      ),
    );
  }
}
