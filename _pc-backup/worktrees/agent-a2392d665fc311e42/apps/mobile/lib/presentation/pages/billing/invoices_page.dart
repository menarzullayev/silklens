// SILK-0107 — Invoices page wired to invoicesProvider (real API).

import 'package:flutter/material.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/billing_provider.dart';

class InvoicesPage extends ConsumerStatefulWidget {
  const InvoicesPage({super.key});

  @override
  ConsumerState<InvoicesPage> createState() => _InvoicesPageState();
}

class _InvoicesPageState extends ConsumerState<InvoicesPage> {
  static const _bg = Color(0xFF0D2337);
  static const _gold = Color(0xFFB78628);

  String _yearFilter = 'all';

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  List<Map<String, dynamic>> _applyFilter(
    List<Map<String, dynamic>> invoices,
  ) {
    if (_yearFilter == 'all') return invoices;
    return invoices.where((inv) {
      final date = inv['created_at'] as String? ?? '';
      return date.startsWith(_yearFilter);
    }).toList();
  }

  /// Extract distinct years from the invoice list, sorted descending.
  List<String> _years(List<Map<String, dynamic>> invoices) {
    final years = <String>{};
    for (final inv in invoices) {
      final date = inv['created_at'] as String? ?? '';
      if (date.length >= 4) years.add(date.substring(0, 4));
    }
    return years.toList()..sort((a, b) => b.compareTo(a));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: Text(
          _s('billing_invoices_title'),
          style: const TextStyle(color: Colors.white),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.white),
            onPressed: () => ref.invalidate(invoicesProvider),
            tooltip: _s('billing_retry'),
          ),
        ],
      ),
      body: ref.watch(invoicesProvider).when(
            loading: () => const Center(
              child: CircularProgressIndicator(color: _gold),
            ),
            error: (err, _) => Center(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    _s('billing_load_error'),
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.6),
                      fontSize: 14,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  GestureDetector(
                    onTap: () => ref.invalidate(invoicesProvider),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                        vertical: 10,
                      ),
                      decoration: BoxDecoration(
                        color: _gold.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color: _gold.withValues(alpha: 0.4),
                        ),
                      ),
                      child: Text(
                        _s('billing_retry'),
                        style: const TextStyle(
                          color: _gold,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
            data: (invoices) => Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _yearFilterChips(invoices),
                Expanded(child: _invoiceList(_applyFilter(invoices))),
              ],
            ),
          ),
    );
  }

  Widget _yearFilterChips(List<Map<String, dynamic>> invoices) {
    final years = _years(invoices);

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: [
            _chip('all', _s('billing_filter_all')),
            ...years.map((y) => _chip(y, y)),
          ],
        ),
      ),
    );
  }

  Widget _chip(String value, String label) {
    final active = _yearFilter == value;
    return GestureDetector(
      onTap: () => setState(() => _yearFilter = value),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 180),
        margin: const EdgeInsets.only(right: 8),
        padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 8),
        decoration: BoxDecoration(
          color: active ? _gold : Colors.white.withValues(alpha: 0.07),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: active ? _gold : Colors.white.withValues(alpha: 0.15),
          ),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active ? const Color(0xFF1A1200) : Colors.white,
            fontWeight: FontWeight.w600,
            fontSize: 13,
          ),
        ),
      ),
    );
  }

  Widget _invoiceList(List<Map<String, dynamic>> items) {
    if (items.isEmpty) {
      return Center(
        child: Text(
          _s('billing_invoices_empty'),
          style: TextStyle(
            color: Colors.white.withValues(alpha: 0.4),
            fontSize: 14,
          ),
        ),
      );
    }

    return ListView.separated(
      padding: const EdgeInsets.all(16),
      itemCount: items.length,
      separatorBuilder: (_, __) => const SizedBox(height: 10),
      itemBuilder: (_, i) => _invoiceRow(items[i]),
    );
  }

  Widget _invoiceRow(Map<String, dynamic> inv) {
    final date = inv['created_at'] as String? ?? '';
    final planName = inv['plan_display_name'] as String? ?? inv['plan_slug'] as String? ?? '—';
    final amount = inv['amount_due'] as num? ?? 0;
    final currency = inv['currency'] as String? ?? '';
    final status = inv['status'] as String? ?? 'unknown';

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.09)),
      ),
      child: Row(
        children: [
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                _formatDate(date),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w600,
                ),
              ),
              const SizedBox(height: 2),
              Text(
                planName,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.45),
                  fontSize: 11,
                ),
              ),
            ],
          ),
          const Spacer(),
          Text(
            amount == 0 ? _s('billing_free') : '$amount $currency',
            style: const TextStyle(
              color: _gold,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: 10),
          _statusBadge(status),
          const SizedBox(width: 10),
          GestureDetector(
            // PDF download is Phase 2; tap is intentionally no-op for now.
            onTap: () {},
            child: Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(8),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Icon(
                Icons.download_rounded,
                size: 16,
                color: Colors.white.withValues(alpha: 0.6),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _statusBadge(String status) {
    late Color bg;
    late Color fg;
    late String key;

    switch (status) {
      case 'paid':
        bg = const Color(0xFF1B4332);
        fg = const Color(0xFF4CAF50);
        key = 'billing_status_paid';
      case 'pending':
        bg = const Color(0xFF3D2800);
        fg = _gold;
        key = 'billing_status_pending';
      default:
        bg = const Color(0xFF3D1010);
        fg = const Color(0xFFEF5350);
        key = 'billing_status_failed';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        _s(key),
        style: TextStyle(color: fg, fontSize: 10, fontWeight: FontWeight.w700),
      ),
    );
  }

  String _formatDate(String iso) {
    if (iso.length < 10) return iso;
    final parts = iso.substring(0, 10).split('-');
    if (parts.length < 3) return iso;
    const months = [
      '',
      'Yan',
      'Fev',
      'Mar',
      'Apr',
      'May',
      'Iyn',
      'Iyl',
      'Avg',
      'Sen',
      'Okt',
      'Noy',
      'Dek',
    ];
    final m = int.tryParse(parts[1]) ?? 0;
    return '${parts[2]} ${m > 0 && m < 13 ? months[m] : parts[1]} ${parts[0]}';
  }
}
