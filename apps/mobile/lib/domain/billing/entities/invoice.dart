class Invoice {
  const Invoice({
    required this.id,
    required this.number,
    required this.total,
    required this.currency,
    required this.status,
    this.issuedAt,
    this.paidAt,
  });

  factory Invoice.fromJson(Map<String, dynamic> j) => Invoice(
        id: j['id'] as String,
        number: j['number'] as String? ?? '',
        total: (j['total'] as num?)?.toDouble() ?? 0,
        currency: j['currency'] as String? ?? 'USD',
        status: j['status'] as String? ?? 'open',
        issuedAt: j['issued_at'] != null ? DateTime.tryParse(j['issued_at'] as String) : null,
        paidAt: j['paid_at'] != null ? DateTime.tryParse(j['paid_at'] as String) : null,
      );
  final String id;
  final String number;
  final double total;
  final String currency;
  final String status;
  final DateTime? issuedAt;
  final DateTime? paidAt;

  String get amountMajor => '${total.toStringAsFixed(2)} $currency';
}
