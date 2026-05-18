import "package:freezed_annotation/freezed_annotation.dart";

part "invoice.freezed.dart";

enum InvoiceStatus { open, paid, voided, uncollectible }

@freezed
class Invoice with _$Invoice {
  const factory Invoice({
    required String id,
    required InvoiceStatus status,
    required int amountMinor,
    required String currency,
    required DateTime issuedAt,
    DateTime? paidAt,
    String? hostedUrl,
  }) = _Invoice;

  const Invoice._();

  double get amountMajor => amountMinor / 100.0;
}
