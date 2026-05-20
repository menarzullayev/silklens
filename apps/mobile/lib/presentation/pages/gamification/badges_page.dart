import 'package:flutter/material.dart';

class BadgesPage extends StatefulWidget {
  const BadgesPage({super.key});
  @override
  State<BadgesPage> createState() => _BadgesPageState();
}

class _BadgesPageState extends State<BadgesPage> {
  int _activeFilter = 0;
  static const _filters = ['Barchasi', 'Meros', 'AI', 'Ijtimoiy', 'Sayyoh'];
  static const _gold = Color(0xFFB78628);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        title: const Text('Nishonlar', style: TextStyle(color: Colors.white)),
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: const Icon(Icons.arrow_back_ios_new,
              color: Colors.white, size: 20,),
        ),
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
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
                  decoration: BoxDecoration(
                    color: _activeFilter == i
                        ? _gold
                        : Colors.white.withValues(alpha: 0.08),
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
                      fontSize: 13,
                    ),
                  ),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          // Progress
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Row(children: [
              Text('5 / 24 nishon',
                  style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.6),
                      fontSize: 13,),),
              const SizedBox(width: 12),
              Expanded(
                child: Container(
                  height: 4,
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(2),
                  ),
                  child: FractionallySizedBox(
                    widthFactor: 5 / 24,
                    alignment: Alignment.centerLeft,
                    child: Container(
                      decoration: BoxDecoration(
                        color: _gold,
                        borderRadius: BorderRadius.circular(2),
                      ),
                    ),
                  ),
                ),
              ),
            ],),
          ),
          const SizedBox(height: 16),
          // Badge grid
          Expanded(
            child: GridView.builder(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 3,
                crossAxisSpacing: 12,
                mainAxisSpacing: 12,
              ),
              itemCount: 12,
              itemBuilder: (_, i) => _BadgeTile(earned: i < 5, index: i),
            ),
          ),
        ],
      ),
    );
  }
}

class _BadgeTile extends StatelessWidget {
  const _BadgeTile({required this.earned, required this.index});
  final bool earned;
  final int index;

  @override
  Widget build(BuildContext context) {
    return Opacity(
      opacity: earned ? 1.0 : 0.4,
      child: Container(
        decoration: BoxDecoration(
          gradient: earned
              ? const LinearGradient(
                  colors: [Color(0xFF8C6418), Color(0xFFB78628)],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                )
              : null,
          color: earned ? null : Colors.white.withValues(alpha: 0.06),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(
            color: earned
                ? const Color(0xFFB78628)
                : Colors.white.withValues(alpha: 0.12),
          ),
          boxShadow: earned
              ? const [BoxShadow(color: Color(0x40B78628), blurRadius: 12)]
              : null,
        ),
        child: Column(mainAxisAlignment: MainAxisAlignment.center, children: [
          Icon(
            earned
                ? Icons.workspace_premium_rounded
                : Icons.lock_outline_rounded,
            color: earned
                ? const Color(0xFF1A1200)
                : Colors.white.withValues(alpha: 0.4),
            size: 28,
          ),
          const SizedBox(height: 6),
          Text(
            'Nishon ${index + 1}',
            style: TextStyle(
              color: earned
                  ? const Color(0xFF1A1200)
                  : Colors.white.withValues(alpha: 0.4),
              fontSize: 10,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],),
      ),
    );
  }
}
