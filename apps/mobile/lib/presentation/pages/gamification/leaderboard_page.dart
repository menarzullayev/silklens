import 'package:flutter/material.dart';

class LeaderboardPage extends StatefulWidget {
  const LeaderboardPage({super.key});

  @override
  State<LeaderboardPage> createState() => _LeaderboardPageState();
}

class _LeaderboardPageState extends State<LeaderboardPage>
    with SingleTickerProviderStateMixin {
  int _periodIndex = 0;
  static const _periods = ['Hafta', 'Oy', 'Hammasi'];
  static const _gold = Color(0xFFB78628);
  static const _goldLight = Color(0xFFE5C97A);

  static const _entries = [
    _LBEntry(
        rank: 1,
        name: 'Jasur Toshmatov',
        level: 18,
        xp: 12480,
        delta: 320,
        isMe: false,),
    _LBEntry(
        rank: 2,
        name: 'Malika Yusupova',
        level: 15,
        xp: 10230,
        delta: 210,
        isMe: false,),
    _LBEntry(
        rank: 3,
        name: 'Bobur Rahimov',
        level: 14,
        xp: 9870,
        delta: 180,
        isMe: false,),
    _LBEntry(
        rank: 4,
        name: 'Nilufar Karimova',
        level: 13,
        xp: 8550,
        delta: -40,
        isMe: false,),
    _LBEntry(rank: 5, name: 'Siz', level: 12, xp: 7320, delta: 95, isMe: true),
    _LBEntry(
        rank: 6,
        name: 'Otabek Saidov',
        level: 11,
        xp: 6900,
        delta: -20,
        isMe: false,),
    _LBEntry(
        rank: 7,
        name: 'Zulfiya Ergasheva',
        level: 10,
        xp: 5430,
        delta: 130,
        isMe: false,),
    _LBEntry(
        rank: 8,
        name: 'Doniyor Xolmatov',
        level: 9,
        xp: 4210,
        delta: 60,
        isMe: false,),
  ];

  Color _medalColor(int rank) {
    if (rank == 1) return const Color(0xFFFFD700);
    if (rank == 2) return const Color(0xFFC0C0C0);
    if (rank == 3) return const Color(0xFFCD7F32);
    return Colors.white.withValues(alpha: 0.2);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        title: const Text(
          'Reyting',
          style: TextStyle(color: Colors.white),
        ),
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
      ),
      body: Column(
        children: [
          // Period tab bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Container(
              height: 44,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(22),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Row(
                children: List.generate(_periods.length, (i) {
                  final active = _periodIndex == i;
                  return Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _periodIndex = i),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        margin: const EdgeInsets.all(4),
                        decoration: BoxDecoration(
                          gradient: active
                              ? const LinearGradient(
                                  colors: [_gold, _goldLight],
                                )
                              : null,
                          borderRadius: BorderRadius.circular(18),
                        ),
                        child: Center(
                          child: Text(
                            _periods[i],
                            style: TextStyle(
                              color: active
                                  ? const Color(0xFF1A1200)
                                  : Colors.white.withValues(alpha: 0.6),
                              fontSize: 13,
                              fontWeight:
                                  active ? FontWeight.w700 : FontWeight.w400,
                            ),
                          ),
                        ),
                      ),
                    ),
                  );
                }),
              ),
            ),
          ),
          const SizedBox(height: 16),
          // List
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _entries.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (_, i) => _LeaderboardRow(
                entry: _entries[i],
                medalColor: _medalColor(_entries[i].rank),
              ),
            ),
          ),
          const SizedBox(height: 16),
        ],
      ),
    );
  }
}

class _LBEntry {
  const _LBEntry({
    required this.rank,
    required this.name,
    required this.level,
    required this.xp,
    required this.delta,
    required this.isMe,
  });
  final int rank;
  final String name;
  final int level;
  final int xp;
  final int delta;
  final bool isMe;
}

class _LeaderboardRow extends StatelessWidget {
  const _LeaderboardRow({required this.entry, required this.medalColor});
  final _LBEntry entry;
  final Color medalColor;

  static const _gold = Color(0xFFB78628);

  @override
  Widget build(BuildContext context) {
    final isTop3 = entry.rank <= 3;
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: entry.isMe
            ? _gold.withValues(alpha: 0.12)
            : Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: entry.isMe
              ? _gold.withValues(alpha: 0.6)
              : isTop3
                  ? medalColor.withValues(alpha: 0.4)
                  : Colors.white.withValues(alpha: 0.08),
          width: entry.isMe ? 1.5 : 1,
        ),
        boxShadow: entry.isMe
            ? [BoxShadow(color: _gold.withValues(alpha: 0.15), blurRadius: 12)]
            : null,
      ),
      child: Row(
        children: [
          // Rank circle
          Container(
            width: 32,
            height: 32,
            decoration: BoxDecoration(
              color: isTop3 ? medalColor : Colors.white.withValues(alpha: 0.1),
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                '${entry.rank}',
                style: TextStyle(
                  color: isTop3
                      ? const Color(0xFF1A1200)
                      : Colors.white.withValues(alpha: 0.7),
                  fontSize: 13,
                  fontWeight: FontWeight.w800,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          // Avatar placeholder
          Container(
            width: 38,
            height: 38,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.12),
              shape: BoxShape.circle,
              border: Border.all(
                color: entry.isMe ? _gold : Colors.transparent,
                width: 1.5,
              ),
            ),
            child: Center(
              child: Text(
                entry.name.substring(0, 1),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                ),
              ),
            ),
          ),
          const SizedBox(width: 10),
          // Name + level
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  entry.name,
                  style: TextStyle(
                    color: entry.isMe ? _gold : Colors.white,
                    fontSize: 13,
                    fontWeight: entry.isMe ? FontWeight.w700 : FontWeight.w500,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
                Text(
                  'Daraja ${entry.level}',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.45),
                    fontSize: 11,
                  ),
                ),
              ],
            ),
          ),
          // XP
          Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              Text(
                '${entry.xp} XP',
                style: TextStyle(
                  color: entry.isMe ? _gold : Colors.white,
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                ),
              ),
              Row(
                children: [
                  Icon(
                    entry.delta >= 0
                        ? Icons.arrow_drop_up_rounded
                        : Icons.arrow_drop_down_rounded,
                    color: entry.delta >= 0
                        ? Colors.greenAccent
                        : Colors.redAccent,
                    size: 16,
                  ),
                  Text(
                    '${entry.delta.abs()}',
                    style: TextStyle(
                      color: entry.delta >= 0
                          ? Colors.greenAccent
                          : Colors.redAccent,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
}
