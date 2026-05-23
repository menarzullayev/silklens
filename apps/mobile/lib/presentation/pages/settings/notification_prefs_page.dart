import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

class NotificationPrefsPage extends ConsumerStatefulWidget {
  const NotificationPrefsPage({super.key});

  @override
  ConsumerState<NotificationPrefsPage> createState() =>
      _NotificationPrefsPageState();
}

class _NotificationPrefsPageState extends ConsumerState<NotificationPrefsPage> {
  // Quiet hours
  bool _quietHours = true;

  // FAOLLIK
  bool _visitCheckin = true;
  bool _xpGained = true;
  bool _levelUp = true;

  // IJTIMOIY
  bool _newFollower = true;
  bool _commentReply = true;
  bool _friendVisit = false;

  // YANGILIKLAR
  bool _newHeritage = true;
  bool _weeklyDigest = false;
  bool _promotions = false;

  // Delivery channels
  bool _push = true;
  bool _email = false;
  bool _sms = false;

  @override
  void initState() {
    super.initState();
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: Color(0xFF0D2337),
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );
    _loadPreferences();
  }

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  Future<void> _loadPreferences() async {
    final client = ref.read(silkLensApiClientProvider);
    try {
      final prefs = await client.getNotificationPreferences();
      if (!mounted) return;
      // Map API response to local toggles; fall through to defaults on
      // any shape mismatch — the UI still works offline.
      final items =
          prefs['items'] as List? ?? prefs['preferences'] as List? ?? [];
      for (final rawItem in items) {
        final item =
            rawItem is Map<String, dynamic> ? rawItem : <String, dynamic>{};
        final slug = item['category_slug'] as String? ?? '';
        final channel = item['channel'] as String? ?? '';
        final enabled = (item['enabled'] as bool?) ?? true;
        setState(() {
          _mapToggle(slug, channel, enabled);
        });
      }
      // Quiet hours
      final qh = prefs['quiet_hours'] as Map<String, dynamic>?;
      if (qh != null) {
        setState(() => _quietHours = (qh['enabled'] as bool?) ?? _quietHours);
      }
      // Channels
      final channels = prefs['channels'] as Map<String, dynamic>?;
      if (channels != null) {
        setState(() {
          _push = (channels['push'] as bool?) ?? _push;
          _email = (channels['email'] as bool?) ?? _email;
          _sms = (channels['sms'] as bool?) ?? _sms;
        });
      }
    } catch (_) {
      // Use defaults if API fails — page remains fully functional
    }
  }

  void _mapToggle(String slug, String channel, bool enabled) {
    if (channel.isNotEmpty) return; // channel-level prefs handled separately
    switch (slug) {
      case 'visit_checkin':
        _visitCheckin = enabled;
      case 'xp_gained':
        _xpGained = enabled;
      case 'level_up':
        _levelUp = enabled;
      case 'new_follower':
        _newFollower = enabled;
      case 'comment_reply':
        _commentReply = enabled;
      case 'friend_visit':
        _friendVisit = enabled;
      case 'new_heritage':
        _newHeritage = enabled;
      case 'weekly_digest':
        _weeklyDigest = enabled;
      case 'promotions':
        _promotions = enabled;
    }
  }

  Future<void> _savePreference(String categorySlug, bool enabled) async {
    final client = ref.read(silkLensApiClientProvider);
    try {
      await client.updateNotificationPreferences([
        {'category_slug': categorySlug, 'enabled': enabled},
      ]);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_s('notif_prefs_save_error'))),
      );
    }
  }

  Future<void> _saveChannelPreference(String channel, bool enabled) async {
    final client = ref.read(silkLensApiClientProvider);
    try {
      await client.updateNotificationPreferences([
        {'channel': channel, 'enabled': enabled},
      ]);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_s('notif_prefs_save_error'))),
      );
    }
  }

  Future<void> _saveQuietHours(bool enabled) async {
    final client = ref.read(silkLensApiClientProvider);
    try {
      await client.updateQuietHours(
        timezone: 'Asia/Tashkent',
        startTime: '22:00',
        endTime: '08:00',
        weekdays: [1, 2, 3, 4, 5, 6, 7],
      );
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_s('notif_quiet_hours_error'))),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        leading: GestureDetector(
          onTap: () => context.pop(),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: const Text(
          'Bildirishnomalar',
          style: TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Quiet hours glass card
            Container(
              padding: const EdgeInsets.symmetric(
                horizontal: 20,
                vertical: 16,
              ),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(18),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Row(
                children: [
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: const Color(0xFF1F3A93).withValues(alpha: 0.5),
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child: const Icon(
                      Icons.nightlight_round,
                      color: Color(0xFFB78628),
                      size: 20,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Tinch soatlar',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 14,
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                        Text(
                          '22:00 – 08:00',
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.5),
                            fontSize: 12,
                          ),
                        ),
                      ],
                    ),
                  ),
                  Switch(
                    value: _quietHours,
                    onChanged: (v) {
                      setState(() => _quietHours = v);
                      _saveQuietHours(v);
                    },
                    activeThumbColor: const Color(0xFFB78628),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // FAOLLIK
            const _SectionLabel('FAOLLIK'),
            _ToggleRow(
              icon: Icons.place_outlined,
              label: 'Joy tashrif buyurish',
              value: _visitCheckin,
              onChanged: (v) {
                setState(() => _visitCheckin = v);
                _savePreference('visit_checkin', v);
              },
            ),
            _ToggleRow(
              icon: Icons.star_outline_rounded,
              label: 'XP qozonish',
              value: _xpGained,
              onChanged: (v) {
                setState(() => _xpGained = v);
                _savePreference('xp_gained', v);
              },
            ),
            _ToggleRow(
              icon: Icons.emoji_events_outlined,
              label: 'Daraja oshishi',
              value: _levelUp,
              onChanged: (v) {
                setState(() => _levelUp = v);
                _savePreference('level_up', v);
              },
            ),
            const SizedBox(height: 16),

            // IJTIMOIY
            const _SectionLabel('IJTIMOIY'),
            _ToggleRow(
              icon: Icons.person_add_outlined,
              label: 'Yangi obunachilar',
              value: _newFollower,
              onChanged: (v) {
                setState(() => _newFollower = v);
                _savePreference('new_follower', v);
              },
            ),
            _ToggleRow(
              icon: Icons.chat_bubble_outline_rounded,
              label: 'Izoh javoblari',
              value: _commentReply,
              onChanged: (v) {
                setState(() => _commentReply = v);
                _savePreference('comment_reply', v);
              },
            ),
            _ToggleRow(
              icon: Icons.group_outlined,
              label: "Do'st tashrifi",
              value: _friendVisit,
              onChanged: (v) {
                setState(() => _friendVisit = v);
                _savePreference('friend_visit', v);
              },
            ),
            const SizedBox(height: 16),

            // YANGILIKLAR
            const _SectionLabel('YANGILIKLAR'),
            _ToggleRow(
              icon: Icons.new_releases_outlined,
              label: 'Yangi meros joylari',
              value: _newHeritage,
              onChanged: (v) {
                setState(() => _newHeritage = v);
                _savePreference('new_heritage', v);
              },
            ),
            _ToggleRow(
              icon: Icons.mail_outline_rounded,
              label: 'Haftalik xulosa',
              value: _weeklyDigest,
              onChanged: (v) {
                setState(() => _weeklyDigest = v);
                _savePreference('weekly_digest', v);
              },
            ),
            _ToggleRow(
              icon: Icons.local_offer_outlined,
              label: 'Aksiyalar',
              value: _promotions,
              onChanged: (v) {
                setState(() => _promotions = v);
                _savePreference('promotions', v);
              },
            ),
            const SizedBox(height: 24),

            // Delivery channels
            const Padding(
              padding: EdgeInsets.only(left: 4, bottom: 12),
              child: Text(
                'YUBORISH KANALLARI',
                style: TextStyle(
                  color: Color(0xFFB78628),
                  fontSize: 11,
                  letterSpacing: 1.5,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
            Container(
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.08),
                ),
              ),
              child: Column(
                children: [
                  _ChannelTile(
                    icon: Icons.notifications_outlined,
                    label: 'Push',
                    value: _push,
                    onChanged: (v) {
                      setState(() => _push = v);
                      _saveChannelPreference('push', v);
                    },
                    isFirst: true,
                  ),
                  Divider(
                    height: 1,
                    color: Colors.white.withValues(alpha: 0.06),
                    indent: 56,
                  ),
                  _ChannelTile(
                    icon: Icons.email_outlined,
                    label: 'Email',
                    value: _email,
                    onChanged: (v) {
                      setState(() => _email = v);
                      _saveChannelPreference('email', v);
                    },
                  ),
                  Divider(
                    height: 1,
                    color: Colors.white.withValues(alpha: 0.06),
                    indent: 56,
                  ),
                  _ChannelTile(
                    icon: Icons.sms_outlined,
                    label: 'SMS',
                    value: _sms,
                    onChanged: (v) {
                      setState(() => _sms = v);
                      _saveChannelPreference('sms', v);
                    },
                    isLast: true,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}

class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.title);
  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(left: 4, bottom: 8),
      child: Text(
        title,
        style: TextStyle(
          color: Colors.white.withValues(alpha: 0.4),
          fontSize: 11,
          letterSpacing: 1.5,
          fontWeight: FontWeight.w600,
        ),
      ),
    );
  }
}

class _ToggleRow extends StatelessWidget {
  const _ToggleRow({
    required this.icon,
    required this.label,
    required this.value,
    required this.onChanged,
  });

  final IconData icon;
  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.white.withValues(alpha: 0.08)),
      ),
      child: Row(
        children: [
          Icon(
            icon,
            color: Colors.white.withValues(alpha: 0.6),
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: Colors.white, fontSize: 14),
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeThumbColor: const Color(0xFFB78628),
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ],
      ),
    );
  }
}

class _ChannelTile extends StatelessWidget {
  const _ChannelTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.onChanged,
    this.isFirst = false,
    this.isLast = false,
  });

  final IconData icon;
  final String label;
  final bool value;
  final ValueChanged<bool> onChanged;
  final bool isFirst;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(
        left: 16,
        right: 8,
        top: isFirst ? 4 : 0,
        bottom: isLast ? 4 : 0,
      ),
      child: Row(
        children: [
          Icon(icon, color: Colors.white.withValues(alpha: 0.6), size: 20),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(color: Colors.white, fontSize: 14),
            ),
          ),
          Switch(
            value: value,
            onChanged: onChanged,
            activeThumbColor: const Color(0xFFB78628),
            materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
          ),
        ],
      ),
    );
  }
}
