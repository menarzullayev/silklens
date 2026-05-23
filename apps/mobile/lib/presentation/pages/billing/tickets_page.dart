// SILK-0126 — My Tickets: fetches real tickets via SilkLensApiClient and
// renders QR codes with qr_flutter for valid tickets.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class TicketsPage extends ConsumerStatefulWidget {
  const TicketsPage({super.key});

  @override
  ConsumerState<TicketsPage> createState() => _TicketsPageState();
}

class _TicketsPageState extends ConsumerState<TicketsPage> {
  static const _bg = Color(0xFF0D2337);
  static const _gold = Color(0xFFB78628);

  List<Map<String, dynamic>> _tickets = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: _bg,
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );
    _load();
  }

  String _s(String key) {
    final locale = ref.read(activeLocaleProvider).languageCode;
    return AppStrings.get(locale, key);
  }

  Future<void> _load() async {
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final items = await ref.read(silkLensApiClientProvider).getMyTickets();
      if (!mounted) return;
      setState(() {
        _tickets = items
            .map((e) => Map<String, dynamic>.from(e as Map))
            .toList();
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      appBar: AppBar(
        backgroundColor: _bg,
        leading: GestureDetector(
          onTap: () => context.pop(),
          child: const Icon(Icons.arrow_back_ios_new, color: Colors.white, size: 20),
        ),
        title: Text(
          _s('tickets_title'),
          style: const TextStyle(color: Colors.white, fontSize: 20, fontWeight: FontWeight.w700),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.refresh_rounded, color: Colors.white70),
            onPressed: _load,
          ),
        ],
      ),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator(color: _gold))
          : _error != null
              ? _buildError()
              : _tickets.isEmpty
                  ? _buildEmpty()
                  : RefreshIndicator(
                      color: _gold,
                      backgroundColor: _bg,
                      onRefresh: _load,
                      child: ListView.builder(
                        padding: const EdgeInsets.all(16),
                        itemCount: _tickets.length,
                        itemBuilder: (_, i) => _buildCard(_tickets[i]),
                      ),
                    ),
    );
  }

  Widget _buildError() {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.cloud_off_rounded, size: 56, color: Colors.white38),
          const SizedBox(height: 16),
          Text(
            _s('tickets_error'),
            style: const TextStyle(color: Colors.white60, fontSize: 16),
          ),
          const SizedBox(height: 16),
          GestureDetector(
            onTap: _load,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
              decoration: BoxDecoration(
                color: _gold.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: _gold.withValues(alpha: 0.5)),
              ),
              child: Text(
                _s('tickets_retry'),
                style: const TextStyle(color: _gold, fontWeight: FontWeight.w700),
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildEmpty() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(40),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.confirmation_number_outlined, size: 64, color: Colors.white24),
            const SizedBox(height: 16),
            Text(
              _s('tickets_empty_title'),
              style: const TextStyle(color: Colors.white70, fontSize: 18, fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(
              _s('tickets_empty_sub'),
              textAlign: TextAlign.center,
              style: const TextStyle(color: Colors.white38, fontSize: 14),
            ),
            const SizedBox(height: 24),
            GestureDetector(
              onTap: () => context.go('/home'),
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
                decoration: BoxDecoration(
                  gradient: const LinearGradient(
                    colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                  ),
                  borderRadius: BorderRadius.circular(12),
                  boxShadow: [
                    BoxShadow(
                      color: _gold.withValues(alpha: 0.3),
                      blurRadius: 12,
                      offset: const Offset(0, 4),
                    ),
                  ],
                ),
                child: Text(
                  _s('tickets_browse_heritage'),
                  style: const TextStyle(color: Color(0xFF1A1200), fontWeight: FontWeight.w700),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCard(Map<String, dynamic> ticket) {
    final status = ticket['status'] as String? ?? 'valid';
    final isValid = status == 'valid';
    final isUsed = status == 'used';
    final name = ticket['ticket_name'] as String? ?? _s('tickets_ticket_label');
    final visitDate = ticket['visit_date'] as String? ?? '';
    final heritageName = ticket['heritage_name'] as String? ?? '';

    final statusLabel = isValid
        ? _s('tickets_status_active')
        : isUsed
            ? _s('tickets_status_used')
            : _s('tickets_status_expired');
    final statusColor = isValid ? _gold : Colors.white38;

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.07),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: isValid ? _gold.withValues(alpha: 0.5) : Colors.white.withValues(alpha: 0.1),
          width: isValid ? 1.5 : 1,
        ),
        boxShadow: isValid
            ? [BoxShadow(color: _gold.withValues(alpha: 0.08), blurRadius: 16)]
            : [],
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: isValid ? () => _showQr(ticket) : null,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: [
              Container(
                width: 52,
                height: 52,
                decoration: BoxDecoration(
                  color: isValid
                      ? _gold.withValues(alpha: 0.15)
                      : Colors.white.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Icon(
                  Icons.confirmation_number_rounded,
                  color: isValid ? _gold : Colors.white38,
                  size: 28,
                ),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      name,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    if (heritageName.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Text(
                        heritageName,
                        style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 12),
                      ),
                    ],
                    if (visitDate.isNotEmpty) ...[
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          Icon(Icons.calendar_today_rounded, size: 11, color: Colors.white.withValues(alpha: 0.4)),
                          const SizedBox(width: 4),
                          Text(visitDate, style: TextStyle(color: Colors.white.withValues(alpha: 0.5), fontSize: 12)),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(width: 12),
              Column(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                    decoration: BoxDecoration(
                      color: statusColor.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(
                      statusLabel,
                      style: TextStyle(color: statusColor, fontSize: 11, fontWeight: FontWeight.w700),
                    ),
                  ),
                  if (isValid) ...[
                    const SizedBox(height: 8),
                    const Icon(Icons.qr_code_rounded, color: _gold, size: 20),
                  ],
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _showQr(Map<String, dynamic> ticket) {
    final qrPayload = ticket['qr_payload'] as String?;
    if (qrPayload == null) return;
    final name = ticket['ticket_name'] as String? ?? _s('tickets_ticket_label');
    final visitDate = ticket['visit_date'] as String? ?? '';

    showDialog<void>(
      context: context,
      builder: (ctx) => Dialog(
        backgroundColor: Colors.transparent,
        child: Container(
          padding: const EdgeInsets.all(24),
          decoration: BoxDecoration(
            color: const Color(0xFF102844),
            borderRadius: BorderRadius.circular(24),
            border: Border.all(color: _gold.withValues(alpha: 0.3)),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                name,
                style: const TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w700),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: QrImageView(
                  data: qrPayload,
                  version: QrVersions.auto,
                  size: 200,
                  backgroundColor: Colors.white,
                ),
              ),
              if (visitDate.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(visitDate, style: const TextStyle(color: Colors.white60, fontSize: 13)),
              ],
              const SizedBox(height: 20),
              GestureDetector(
                onTap: () => Navigator.of(ctx).pop(),
                child: Container(
                  height: 44,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Center(
                    child: Text(
                      _s('tickets_close'),
                      style: const TextStyle(color: _gold, fontWeight: FontWeight.w700),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
