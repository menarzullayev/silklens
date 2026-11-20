import 'package:flutter/material.dart';

class NotificationsPage extends StatefulWidget {
  const NotificationsPage({super.key});

  @override
  State<NotificationsPage> createState() => _NotificationsPageState();
}

class _NotificationsPageState extends State<NotificationsPage> {
  static const _gold = Color(0xFFB78628);
  static const _bg = Color(0xFF0D2337);

  int _activeFilter = 0;
  static const _filters = ['Barchasi', "O'qilmagan", 'Ijtimoiy', 'Daraja'];

  final _notifications = [
    _NotifData(
      icon: Icons.favorite_rounded,
      iconColor: Colors.redAccent,
      title: 'Aziz Karimov sizning postingizga like bosdi',
      time: '5 daqiqa oldin',
      isRead: false,
      category: 'Ijtimoiy',
    ),
    _NotifData(
      icon: Icons.workspace_premium_rounded,
      iconColor: const Color(0xFFB78628),
      title: "Yangi nishon qo'lga kiritildi: Sayyoh I",
      time: '1 soat oldin',
      isRead: false,
      category: 'Daraja',
    ),
    _NotifData(
      icon: Icons.person_add_rounded,
      iconColor: const Color(0xFF1F3A93),
      title: 'Dilnoza Yusupova sizni kuzata boshladi',
      time: '3 soat oldin',
      isRead: false,
      category: 'Ijtimoiy',
    ),
    _NotifData(
      icon: Icons.trending_up_rounded,
      iconColor: Colors.greenAccent,
      title: "Tabriklaymiz! Daraja 12 ga ko'tarildingiz",
      time: 'Kecha',
      isRead: true,
      category: 'Daraja',
    ),
    _NotifData(
      icon: Icons.chat_bubble_rounded,
      iconColor: const Color(0xFF7B68EE),
      title: 'Jasur Rahimov sharhingizga javob berdi',
      time: 'Kecha',
      isRead: true,
      category: 'Ijtimoiy',
    ),
    _NotifData(
      icon: Icons.local_fire_department_rounded,
      iconColor: Colors.orange,
      title: '12 kunlik streak — davom eting!',
      time: '2 kun oldin',
      isRead: true,
      category: 'Daraja',
    ),
  ];

  List<_NotifData> get _filtered {
    if (_activeFilter == 0) return _notifications;
    if (_activeFilter == 1) {
      return _notifications.where((n) => !n.isRead).toList();
    }
    final cat = _filters[_activeFilter];
    return _notifications.where((n) => n.category == cat).toList();
  }

  void _markAllRead() {
    setState(() {
      for (final n in _notifications) {
        n.isRead = true;
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filtered;
    final unreadCount = _notifications.where((n) => !n.isRead).length;

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
        title: Row(children: [
          const Text(
            'Bildirishnomalar',
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),
          if (unreadCount > 0) ...[
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
              decoration: BoxDecoration(
                color: _gold,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                '$unreadCount',
                style: const TextStyle(
                  color: Color(0xFF1A1200),
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ],
        ],),
        actions: [
          if (unreadCount > 0)
            TextButton(
              onPressed: _markAllRead,
              child: const Text(
                "Hammasi o'qildi",
                style: TextStyle(color: _gold, fontSize: 12),
              ),
            ),
        ],
      ),
      body: Column(
        children: [
          // Filter chips
          SizedBox(
            height: 44,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _filters.length,
              separatorBuilder: (_, __) => const SizedBox(width: 8),
              itemBuilder: (_, i) => GestureDetector(
                onTap: () => setState(() => _activeFilter = i),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: _activeFilter == i
                        ? _gold
                        : Colors.white.withValues(alpha: 0.07),
                    borderRadius: BorderRadius.circular(22),
                    border: Border.all(
                      color: _activeFilter == i
                          ? _gold
                          : Colors.white.withValues(alpha: 0.15),
                    ),
                  ),
                  child: Text(
                    _filters[i],
                    style: TextStyle(
                      color: _activeFilter == i
                          ? const Color(0xFF1A1200)
                          : Colors.white,
                      fontSize: 12,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          // Notification list
          Expanded(
            child: filtered.isEmpty
                ? Center(
                    child: Text(
                      "Bildirishnoma yo'q",
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.4),
                        fontSize: 15,
                      ),
                    ),
                  )
                : ListView.separated(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 8,
                    ),
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (_, i) => _NotifCard(
                      data: filtered[i],
                      onTap: () => setState(() => filtered[i].isRead = true),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}

class _NotifData {
  _NotifData({
    required this.icon,
    required this.iconColor,
    required this.title,
    required this.time,
    required this.isRead,
    required this.category,
  });

  final IconData icon;
  final Color iconColor;
  final String title;
  final String time;
  bool isRead;
  final String category;
}

class _NotifCard extends StatelessWidget {
  const _NotifCard({required this.data, required this.onTap});

  final _NotifData data;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: data.isRead ? 0.04 : 0.08),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: Colors.white.withValues(alpha: data.isRead ? 0.08 : 0.14),
          ),
        ),
        child: Row(children: [
          // Left gold bar for unread
          AnimatedContainer(
            duration: const Duration(milliseconds: 300),
            width: 4,
            height: 64,
            decoration: BoxDecoration(
              color: data.isRead
                  ? Colors.transparent
                  : const Color(0xFFB78628),
              borderRadius: const BorderRadius.horizontal(
                left: Radius.circular(16),
              ),
            ),
          ),
          const SizedBox(width: 12),
          // Icon circle
          Container(
            width: 42,
            height: 42,
            decoration: BoxDecoration(
              color: data.iconColor.withValues(alpha: 0.15),
              shape: BoxShape.circle,
            ),
            child: Icon(data.icon, color: data.iconColor, size: 20),
          ),
          const SizedBox(width: 12),
          // Text
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    data.title,
                    style: TextStyle(
                      color: Colors.white.withValues(
                        alpha: data.isRead ? 0.65 : 1.0,
                      ),
                      fontSize: 13,
                      fontWeight: data.isRead
                          ? FontWeight.w400
                          : FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    data.time,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.4),
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(width: 12),
        ],),
      ),
    );
  }
}
