import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:qr_flutter/qr_flutter.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/social_provider.dart';

class FriendInvitePage extends ConsumerStatefulWidget {
  const FriendInvitePage({super.key});

  @override
  ConsumerState<FriendInvitePage> createState() =>
      _FriendInvitePageState();
}

class _FriendInvitePageState extends ConsumerState<FriendInvitePage> {
  static const _gold = Color(0xFFB78628);
  static const _bg = Color(0xFF0D2337);

  bool _copied = false;

  String _s(String key) =>
      AppStrings.get(LocaleService.instance.locale, key);

  String _inviteLink(String token) =>
      'silklens://invite?token=$token';

  String _expiryLabel(String? expiresAt) {
    if (expiresAt == null) return '';
    try {
      final dt = DateTime.parse(expiresAt).toLocal();
      return '${_s('invite_expires')}: '
          '${dt.day.toString().padLeft(2, '0')}.'
          '${dt.month.toString().padLeft(2, '0')}.'
          '${dt.year} '
          '${dt.hour.toString().padLeft(2, '0')}:'
          '${dt.minute.toString().padLeft(2, '0')}';
    } catch (_) {
      return expiresAt;
    }
  }

  Future<void> _copyLink(String link) async {
    await Clipboard.setData(ClipboardData(text: link));
    if (!mounted) return;
    setState(() => _copied = true);
    await Future<void>.delayed(const Duration(seconds: 2));
    if (mounted) setState(() => _copied = false);
  }

  @override
  Widget build(BuildContext context) {
    final inviteState = ref.watch(friendInviteProvider);
    final token = inviteState.token;
    final link = token != null ? _inviteLink(token) : null;

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
          _s('invite_title'),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            const SizedBox(height: 8),

            // Headline
            Text(
              _s('invite_headline'),
              textAlign: TextAlign.center,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 22,
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              _s('invite_sub'),
              textAlign: TextAlign.center,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.55),
                fontSize: 14,
              ),
            ),
            const SizedBox(height: 32),

            // QR code — real when token available, loading/error otherwise
            Container(
              width: 216,
              height: 216,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.04),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(color: _gold, width: 2),
              ),
              child: inviteState.isLoading
                  ? const Center(
                      child: CircularProgressIndicator(
                        color: _gold,
                        strokeWidth: 2,
                      ),
                    )
                  : inviteState.error != null
                      ? Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(
                                Icons.error_outline_rounded,
                                color: Colors.white.withValues(alpha: 0.4),
                                size: 36,
                              ),
                              const SizedBox(height: 8),
                              Text(
                                _s('invite_error'),
                                style: TextStyle(
                                  color:
                                      Colors.white.withValues(alpha: 0.45),
                                  fontSize: 12,
                                ),
                                textAlign: TextAlign.center,
                              ),
                              const SizedBox(height: 12),
                              GestureDetector(
                                onTap: () => ref
                                    .read(
                                      friendInviteProvider.notifier,
                                    )
                                    .createInvite(),
                                child: Text(
                                  _s('social_feed_retry'),
                                  style: const TextStyle(
                                    color: _gold,
                                    fontSize: 12,
                                    fontWeight: FontWeight.w600,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        )
                      : link != null
                          ? ClipRRect(
                              borderRadius: BorderRadius.circular(22),
                              child: QrImageView(
                                data: link,
                                size: 212,
                                backgroundColor: Colors.white,
                              ),
                            )
                          : Center(
                              child: Column(
                                mainAxisAlignment:
                                    MainAxisAlignment.center,
                                children: [
                                  const Icon(
                                    Icons.qr_code_2_rounded,
                                    color: _gold,
                                    size: 100,
                                  ),
                                  const SizedBox(height: 8),
                                  Text(
                                    _s('invite_qr_label'),
                                    style: TextStyle(
                                      color: Colors.white.withValues(
                                        alpha: 0.45,
                                      ),
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
            ),

            // Expiry label
            if (inviteState.expiresAt != null) ...[
              const SizedBox(height: 8),
              Text(
                _expiryLabel(inviteState.expiresAt),
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.4),
                  fontSize: 11,
                ),
              ),
            ],

            const SizedBox(height: 32),

            // +500 XP glass card
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(
                horizontal: 20,
                vertical: 16,
              ),
              decoration: BoxDecoration(
                color: _gold.withValues(alpha: 0.10),
                borderRadius: BorderRadius.circular(20),
                border:
                    Border.all(color: _gold.withValues(alpha: 0.35)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 48,
                    height: 48,
                    decoration: BoxDecoration(
                      gradient: const LinearGradient(
                        colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                      ),
                      shape: BoxShape.circle,
                      boxShadow: [
                        BoxShadow(
                          color: _gold.withValues(alpha: 0.35),
                          blurRadius: 12,
                        ),
                      ],
                    ),
                    child: const Center(
                      child: Text(
                        '★',
                        style: TextStyle(
                          color: Color(0xFF1A1200),
                          fontSize: 22,
                          fontWeight: FontWeight.w900,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          _s('invite_xp_first'),
                          style: const TextStyle(
                            color: _gold,
                            fontSize: 15,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 3),
                        Text(
                          _s('invite_xp_each'),
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.55),
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Share link row — shown only when token available
            if (link != null) ...[
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 14,
                  vertical: 12,
                ),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.12),
                  ),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Text(
                        link,
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.7),
                          fontSize: 13,
                        ),
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    const SizedBox(width: 10),
                    GestureDetector(
                      onTap: () => _copyLink(link),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 8,
                        ),
                        decoration: BoxDecoration(
                          color: _copied
                              ? Colors.green.withValues(alpha: 0.2)
                              : _gold,
                          borderRadius: BorderRadius.circular(10),
                        ),
                        child: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Icon(
                              _copied
                                  ? Icons.check_rounded
                                  : Icons.copy_rounded,
                              color: _copied
                                  ? Colors.green
                                  : const Color(0xFF1A1200),
                              size: 16,
                            ),
                            const SizedBox(width: 4),
                            Text(
                              _copied
                                  ? _s('invite_copied')
                                  : _s('invite_copy'),
                              style: TextStyle(
                                color: _copied
                                    ? Colors.green
                                    : const Color(0xFF1A1200),
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
            ],

            // Share button
            GestureDetector(
              onTap: link != null ? () => _copyLink(link) : null,
              child: Container(
                width: double.infinity,
                height: 52,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(
                    alpha: link != null ? 0.08 : 0.04,
                  ),
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(
                    color: Colors.white.withValues(
                      alpha: link != null ? 0.18 : 0.08,
                    ),
                  ),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.share_rounded,
                      color: Colors.white.withValues(
                        alpha: link != null ? 1.0 : 0.35,
                      ),
                      size: 20,
                    ),
                    const SizedBox(width: 10),
                    Text(
                      _s('invite_share'),
                      style: TextStyle(
                        color: Colors.white.withValues(
                          alpha: link != null ? 1.0 : 0.35,
                        ),
                        fontSize: 16,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}
