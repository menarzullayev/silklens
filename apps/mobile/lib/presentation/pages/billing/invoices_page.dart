// Paginated invoice history.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/billing_provider.dart";

class InvoicesPage extends ConsumerWidget {
  const InvoicesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final l10n = AppLocalizations.of(context);
    final asyncInvoices = ref.watch(invoicesProvider);
    return Scaffold(
      appBar: AppBar(title: Text(l10n?.billingInvoicesTitle ?? "Invoices")),
      body: asyncInvoices.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (Object e, _) => Center(child: Text(e.toString())),
        data: (invoices) {
          if (invoices.isEmpty) {
            return Center(
              key: const Key("billing.invoices.empty"),
              child: Text(l10n?.billingInvoicesEmpty ?? "No invoices"),
            );
          }
          return ListView.separated(
            key: const Key("billing.invoices.list"),
            padding: const EdgeInsets.all(8),
            itemCount: invoices.length,
            separatorBuilder: (_, __) => const Divider(height: 1),
            itemBuilder: (BuildContext ctx, int i) {
              final inv = invoices[i];
              return ListTile(
                leading: const Icon(Icons.receipt_long_outlined),
                title: Text(
                  "${inv.currency} ${inv.amountMajor.toStringAsFixed(2)}",
                ),
                subtitle: Text(inv.issuedAt.toLocal().toIso8601String()),
                trailing: Text(inv.status.name),
              );
            },
          );
        },
      ),
    );
  }
}
