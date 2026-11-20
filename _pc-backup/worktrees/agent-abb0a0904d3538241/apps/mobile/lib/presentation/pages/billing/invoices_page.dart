import 'package:flutter/material.dart';

class InvoicesPage extends StatefulWidget {
  const InvoicesPage({super.key});

  @override
  State<InvoicesPage> createState() => _InvoicesPageState();
}

class _InvoicesPageState extends State<InvoicesPage> {
  static const _bg = Color(0xFF0D2337);
  static const _gold = Color(0xFFB78628);

  String _yearFilter = 'Hammasi';

  static const _invoices = [
    (
      '2026-05-01',
      'Explorer ⭐',
      '29,900',
      'paid',
    ),
    (
      '2026-04-01',
      'Explorer ⭐',
      '29,900',
      'paid',
    ),
    (
      '2026-03-01',
      'Heritage Pro 💎',
      '89,900',
      'paid',
    ),
    (
      '2026-02-01',
      'Explorer ⭐',
      '29,900',
      'failed',
    ),
    (
      '2026-01-01',
      'Explorer ⭐',
      '29,900',
      'paid',
    ),
    (
      '2025-12-01',
      'Bepul',
      '0',
      'paid',
    ),
    (
      '2025-11-01',
      'Explorer ⭐',
      '29,900',
      'pending',
    ),
    (
      '2025-10-01',
      'Explorer ⭐',
      '29,900',
      'paid',
    ),
  ];

  List<(String, String, String, String)> get _filtered {
    if (_yearFilter == 'Hammasi') return _invoices;
    return _invoices.where((inv) => inv.$1.startsWith(_yearFilter)).toList();
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
        title: const Text(
          "To'lov tarixi",
          style: TextStyle(color: Colors.white),
        ),
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _yearFilterChips(),
          Expanded(child: _invoiceList()),
        ],
      ),
    );
  }

  Widget _yearFilterChips() {
    const years = ['Hammasi', '2026', '2025'];
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Row(
          children: years.map((y) {
            final active = _yearFilter == y;
            return GestureDetector(
              onTap: () => setState(() => _yearFilter = y),
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 180),
                margin: const EdgeInsets.only(right: 8),
                padding: const EdgeInsets.symmetric(
                  horizontal: 18,
                  vertical: 8,
                ),
                decoration: BoxDecoration(
                  color: active ? _gold : Colors.white.withValues(alpha: 0.07),
                  borderRadius: BorderRadius.circular(20),
                  border: Border.all(
                    color: active
                        ? _gold
                        : Colors.white.withValues(alpha: 0.15),
                  ),
                ),
                child: Text(
                  y,
                  style: TextStyle(
                    color: active ? const Color(0xFF1A1200) : Colors.white,
                    fontWeight: FontWeight.w600,
                    fontSize: 13,
                  ),
                ),
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  Widget _invoiceList() {
    final items = _filtered;
    if (items.isEmpty) {
      return Center(
        child: Text(
          "Bu yil uchun hisob-faktura yo'q",
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

  Widget _invoiceRow((String, String, String, String) inv) {
    final (date, plan, amount, status) = inv;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.05),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.white.withValues(alpha: 0.09)),
      ),
      child: Row(
        children: [
          // Date column
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
                plan,
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.45),
                  fontSize: 11,
                ),
              ),
            ],
          ),
          const Spacer(),
          // Amount
          Text(
            amount == '0' ? 'Bepul' : "$amount so'm",
            style: const TextStyle(
              color: _gold,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(width: 10),
          // Status badge
          _statusBadge(status),
          const SizedBox(width: 10),
          // Download button
          GestureDetector(
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
    late String label;
    switch (status) {
      case 'paid':
        bg = const Color(0xFF1B4332);
        fg = const Color(0xFF4CAF50);
        label = "To'langan";
      case 'pending':
        bg = const Color(0xFF3D2800);
        fg = _gold;
        label = 'Kutilmoqda';
      default:
        bg = const Color(0xFF3D1010);
        fg = const Color(0xFFEF5350);
        label = 'Rad etilgan';
    }
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
      decoration: BoxDecoration(
        color: bg,
        borderRadius: BorderRadius.circular(8),
      ),
      child: Text(
        label,
        style: TextStyle(color: fg, fontSize: 10, fontWeight: FontWeight.w700),
      ),
    );
  }

  String _formatDate(String iso) {
    final parts = iso.split('-');
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
    return '${parts[2]} ${months[m]} ${parts[0]}';
  }
}
