import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

class ExpenseTrackerPage extends HookConsumerWidget {
  const ExpenseTrackerPage({super.key});

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    useEffect(
      () {
        SystemChrome.setSystemUIOverlayStyle(
          const SystemUiOverlayStyle(
            statusBarColor: Colors.transparent,
            statusBarIconBrightness: Brightness.light,
            systemNavigationBarColor: Color(0xFF0D2337),
            systemNavigationBarIconBrightness: Brightness.light,
          ),
        );
        return null;
      },
      const [],
    );

    final summary = useState<Map<String, dynamic>?>(null);
    final isLoading = useState(true);
    final hasError = useState(false);

    Future<void> reload() async {
      isLoading.value = true;
      hasError.value = false;
      try {
        final client = ref.read(silkLensApiClientProvider);
        summary.value = await client.getExpenseSummary();
      } catch (_) {
        hasError.value = true;
      }
      isLoading.value = false;
    }

    useEffect(
      () {
        Future(reload);
        return null;
      },
      const [],
    );

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: GestureDetector(
          onTap: () => Navigator.of(context).pop(),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: Text(
          _s('expense_title'),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton(
        backgroundColor: const Color(0xFFB78628),
        onPressed: () => _showAddExpenseSheet(context, ref, reload),
        child: const Icon(Icons.add, color: Colors.white),
      ),
      body: isLoading.value
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFFB78628)),
            )
          : hasError.value || summary.value == null
              ? _NoBudgetView(
                  s: _s,
                  onCreateBudget: () =>
                      _showCreateBudgetSheet(context, ref, reload),
                )
              : _SummaryView(summary: summary.value!, s: _s),
    );
  }

  void _showAddExpenseSheet(
    BuildContext context,
    WidgetRef ref,
    Future<void> Function() onDone,
  ) {
    final amountCtrl = TextEditingController();
    const category = 'food';

    showModalBottomSheet<void>(
      context: context,
      backgroundColor: const Color(0xFF1A3A5C),
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (sheetCtx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(sheetCtx).viewInsets.bottom,
          left: 20,
          right: 20,
          top: 20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _s('expense_add_title'),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: amountCtrl,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: _s('expense_amount_label'),
                labelStyle: const TextStyle(color: Colors.white60),
                prefixText: r'$ ',
                prefixStyle: const TextStyle(color: Colors.white60),
                enabledBorder: const UnderlineInputBorder(
                  borderSide: BorderSide(color: Colors.white24),
                ),
                focusedBorder: const UnderlineInputBorder(
                  borderSide: BorderSide(color: Color(0xFFB78628)),
                ),
              ),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFB78628),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                onPressed: () async {
                  final amount = double.tryParse(amountCtrl.text) ?? 0;
                  if (amount <= 0) return;
                  await ref.read(silkLensApiClientProvider).addExpense(
                        amountUsd: amount,
                        category: category,
                      );
                  if (sheetCtx.mounted) Navigator.pop(sheetCtx);
                  await onDone();
                },
                child: Text(
                  _s('expense_add_btn'),
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  void _showCreateBudgetSheet(
    BuildContext context,
    WidgetRef ref,
    Future<void> Function() onDone,
  ) {
    final amountCtrl = TextEditingController();

    showModalBottomSheet<void>(
      context: context,
      backgroundColor: const Color(0xFF1A3A5C),
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (sheetCtx) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(sheetCtx).viewInsets.bottom,
          left: 20,
          right: 20,
          top: 20,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _s('expense_budget_create_title'),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 18,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: amountCtrl,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              style: const TextStyle(color: Colors.white),
              decoration: InputDecoration(
                labelText: _s('expense_amount_label'),
                labelStyle: const TextStyle(color: Colors.white60),
                hintText: '500',
                hintStyle: const TextStyle(color: Colors.white38),
                prefixText: r'$ ',
                prefixStyle: const TextStyle(color: Colors.white60),
                enabledBorder: const UnderlineInputBorder(
                  borderSide: BorderSide(color: Colors.white24),
                ),
                focusedBorder: const UnderlineInputBorder(
                  borderSide: BorderSide(color: Color(0xFFB78628)),
                ),
              ),
            ),
            const SizedBox(height: 20),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton(
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFFB78628),
                  padding: const EdgeInsets.symmetric(vertical: 14),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
                onPressed: () async {
                  final amount = double.tryParse(amountCtrl.text) ?? 0;
                  if (amount <= 0) return;
                  await ref.read(silkLensApiClientProvider).createBudget(
                        totalBudgetUsd: amount,
                      );
                  if (sheetCtx.mounted) Navigator.pop(sheetCtx);
                  await onDone();
                },
                child: Text(
                  _s('expense_budget_create_btn'),
                  style: const TextStyle(
                    color: Colors.white,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------

class _NoBudgetView extends StatelessWidget {
  const _NoBudgetView({required this.s, required this.onCreateBudget});
  final String Function(String) s;
  final VoidCallback onCreateBudget;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.account_balance_wallet_outlined,
              size: 64,
              color: Colors.white30,
            ),
            const SizedBox(height: 16),
            Text(
              s('expense_no_budget'),
              style: const TextStyle(color: Colors.white60, fontSize: 18),
            ),
            const SizedBox(height: 20),
            ElevatedButton(
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFFB78628),
                padding: const EdgeInsets.symmetric(
                  horizontal: 28,
                  vertical: 14,
                ),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(12),
                ),
              ),
              onPressed: onCreateBudget,
              child: Text(
                s('expense_budget_create_btn'),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------

class _SummaryView extends StatelessWidget {
  const _SummaryView({required this.summary, required this.s});
  final Map<String, dynamic> summary;
  final String Function(String) s;

  @override
  Widget build(BuildContext context) {
    final total = (summary['total_spent_usd'] as num?)?.toDouble() ?? 0.0;
    final remaining = (summary['remaining_usd'] as num?)?.toDouble();
    final byCategory = (summary['by_category'] as List?) ?? [];

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        // Hero spend card
        Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            gradient: const LinearGradient(
              colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Column(
            children: [
              Text(
                s('expense_total_spent'),
                style: const TextStyle(
                  color: Colors.white70,
                  fontSize: 14,
                ),
              ),
              const SizedBox(height: 4),
              Text(
                '\$${total.toStringAsFixed(2)}',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 40,
                  fontWeight: FontWeight.bold,
                ),
              ),
              if (remaining != null) ...[
                const SizedBox(height: 4),
                Text(
                  '${s("expense_remaining")}: \$${remaining.toStringAsFixed(2)}',
                  style: const TextStyle(color: Colors.white70, fontSize: 14),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 20),
        if (byCategory.isNotEmpty) ...[
          Text(
            s('expense_by_category'),
            style: const TextStyle(
              color: Colors.white70,
              fontWeight: FontWeight.bold,
              fontSize: 13,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 8),
          ...byCategory.map((cat) {
            final c = cat as Map<String, dynamic>;
            final catName = c['category'] as String? ?? '';
            final catTotal = (c['total_usd'] as num?)?.toDouble() ?? 0.0;
            return Container(
              margin: const EdgeInsets.only(bottom: 8),
              padding: const EdgeInsets.symmetric(
                horizontal: 16,
                vertical: 12,
              ),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: Colors.white12),
              ),
              child: Row(
                children: [
                  Text(
                    catName,
                    style: const TextStyle(color: Colors.white),
                  ),
                  const Spacer(),
                  Text(
                    '\$${catTotal.toStringAsFixed(2)}',
                    style: const TextStyle(
                      color: Color(0xFFB78628),
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            );
          }),
        ],
        const SizedBox(height: 80), // FAB clearance
      ],
    );
  }
}
