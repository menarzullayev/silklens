import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class HeritageDetailPage extends StatefulWidget {
  const HeritageDetailPage({required this.pubId, super.key});
  final String pubId;

  @override
  State<HeritageDetailPage> createState() => _HeritageDetailPageState();
}

class _HeritageDetailPageState extends State<HeritageDetailPage>
    with SingleTickerProviderStateMixin {
  late TabController _tabCtrl;
  bool _saved = false;
  int _activeTab = 0;

  static const _tabs = ['Haqida', 'Faktlar', 'Sharhlar'];
  static const _gold = Color(0xFFB78628);
  static const _bg = Color(0xFF0D2337);

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: _tabs.length, vsync: this);
    _tabCtrl.addListener(() => setState(() => _activeTab = _tabCtrl.index));
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: _bg,
      body: CustomScrollView(
        slivers: [
          // Hero image sliver
          SliverAppBar(
            expandedHeight: MediaQuery.sizeOf(context).height * 0.48,
            pinned: true,
            backgroundColor: _bg,
            leading: GestureDetector(
              onTap: () => context.pop(),
              child: Container(
                margin: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.black.withValues(alpha: 0.35),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.2),
                  ),
                ),
                child: const Icon(
                  Icons.arrow_back_ios_new,
                  color: Colors.white,
                  size: 18,
                ),
              ),
            ),
            actions: [
              GestureDetector(
                onTap: () => setState(() => _saved = !_saved),
                child: Container(
                  margin: const EdgeInsets.all(8),
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.black.withValues(alpha: 0.35),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.2),
                    ),
                  ),
                  child: Icon(
                    _saved
                        ? Icons.bookmark_rounded
                        : Icons.bookmark_outline_rounded,
                    color: _saved ? _gold : Colors.white,
                    size: 20,
                  ),
                ),
              ),
              Container(
                margin: const EdgeInsets.only(right: 8, top: 8, bottom: 8),
                padding: const EdgeInsets.all(8),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.black.withValues(alpha: 0.35),
                  border: Border.all(
                    color: Colors.white.withValues(alpha: 0.2),
                  ),
                ),
                child: const Icon(
                  Icons.share_outlined,
                  color: Colors.white,
                  size: 20,
                ),
              ),
            ],
            flexibleSpace: FlexibleSpaceBar(
              background: Stack(
                fit: StackFit.expand,
                children: [
                  // Heritage tone gradient placeholder
                  Container(
                    decoration: const BoxDecoration(
                      gradient: LinearGradient(
                        begin: Alignment.topLeft,
                        end: Alignment.bottomRight,
                        colors: [
                          Color(0xFF8B3A2A),
                          Color(0xFFD2691E),
                          Color(0xFF8B6914),
                        ],
                      ),
                    ),
                  ),
                  // Photo caption
                  Positioned(
                    bottom: 16,
                    left: 16,
                    child: Text(
                      'REGISTON · SAMARQAND · UZ',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.65),
                        fontSize: 9,
                        fontFamily: 'monospace',
                        letterSpacing: 2,
                      ),
                    ),
                  ),
                  // UNESCO badge
                  Positioned(
                    top: 16,
                    right: 16,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 8,
                        vertical: 4,
                      ),
                      decoration: BoxDecoration(
                        color: _gold,
                        borderRadius: BorderRadius.circular(6),
                      ),
                      child: const Text(
                        'UNESCO',
                        style: TextStyle(
                          color: Color(0xFF1A1200),
                          fontSize: 10,
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                    ),
                  ),
                  // Bottom gradient overlay
                  Positioned(
                    bottom: 0,
                    left: 0,
                    right: 0,
                    child: Container(
                      height: 80,
                      decoration: BoxDecoration(
                        gradient: LinearGradient(
                          begin: Alignment.topCenter,
                          end: Alignment.bottomCenter,
                          colors: [
                            Colors.transparent,
                            _bg.withValues(alpha: 0.9),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),

          // Glass info card
          SliverToBoxAdapter(
            child: Container(
              margin: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.07),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    'Registon',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Row(
                    children: [
                      const Icon(
                        Icons.location_on,
                        color: Color(0xFFB78628),
                        size: 14,
                      ),
                      const SizedBox(width: 4),
                      Text(
                        "Samarqand, O'zbekiston",
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.7),
                          fontSize: 13,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      const Icon(
                        Icons.star_rounded,
                        color: Color(0xFFB78628),
                        size: 16,
                      ),
                      const SizedBox(width: 4),
                      const Text(
                        '4.9',
                        style: TextStyle(
                          color: Color(0xFFB78628),
                          fontSize: 14,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(width: 4),
                      Text(
                        '(2,847 sharh)',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.5),
                          fontSize: 12,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  // Info chips
                  const Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      _InfoChip('XIV asr', Icons.history_edu_rounded),
                      _InfoChip(
                        'Saroy majmuasi',
                        Icons.account_balance_rounded,
                      ),
                      _InfoChip(
                        'UNESCO 1001',
                        Icons.workspace_premium_rounded,
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  // Tab bar
                  Container(
                    decoration: BoxDecoration(
                      color: Colors.white.withValues(alpha: 0.06),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: TabBar(
                      controller: _tabCtrl,
                      indicatorSize: TabBarIndicatorSize.tab,
                      indicator: BoxDecoration(
                        color: const Color(0xFFB78628),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      labelColor: const Color(0xFF1A1200),
                      unselectedLabelColor:
                          Colors.white.withValues(alpha: 0.6),
                      labelStyle: const TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                      ),
                      tabs: _tabs.map((t) => Tab(text: t)).toList(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  // Tab content
                  if (_activeTab == 0)
                    Text(
                      "Registon — O'rta Osiyoning eng mashhur arxitektura"
                      " yodgorligi. U uch madrasadan iborat: Ulug'bek"
                      ' (1420), Sher-Dor (1636) va Tillakori (1660). UNESCO'
                      " tomonidan Jahon merosi ro'yxatiga kiritilgan.",
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.85),
                        fontSize: 14,
                        height: 1.6,
                      ),
                    )
                  else if (_activeTab == 1)
                    const Column(
                      children: [
                        _FactRow('Qurilgan yil', '1420 — 1660'),
                        _FactRow('Maydoni', '3.6 gektar'),
                        _FactRow('UNESCO', '1001-raqam'),
                        _FactRow('Kirish', "50,000 so'm"),
                      ],
                    )
                  else
                    Text(
                      'Sharhlar yuklanmoqda...',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.5),
                        fontSize: 14,
                      ),
                    ),
                ],
              ),
            ),
          ),

          // Action buttons
          SliverToBoxAdapter(
            child: Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 32),
              child: Row(
                children: [
                  _ActionBtn(Icons.volume_up_rounded, 'Audio', () {}),
                  const SizedBox(width: 8),
                  _ActionBtn(
                    Icons.view_in_ar_rounded,
                    'AR',
                    () {},
                    isGold: true,
                  ),
                  const SizedBox(width: 8),
                  _ActionBtn(Icons.map_rounded, "Yo'nalish", () {}),
                  const SizedBox(width: 8),
                  _ActionBtn(Icons.photo_library_outlined, 'Foto', () {}),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoChip extends StatelessWidget {
  const _InfoChip(this.label, this.icon);
  final String label;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: Colors.white.withValues(alpha: 0.15)),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 12, color: const Color(0xFFB78628)),
          const SizedBox(width: 4),
          Text(
            label,
            style: const TextStyle(color: Colors.white, fontSize: 11),
          ),
        ],
      ),
    );
  }
}

class _FactRow extends StatelessWidget {
  const _FactRow(this.key2, this.value);
  final String key2;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            key2,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.55),
              fontSize: 13,
            ),
          ),
          Text(
            value,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ),
    );
  }
}

class _ActionBtn extends StatelessWidget {
  const _ActionBtn(this.icon, this.label, this.onTap, {this.isGold = false});
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool isGold;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: GestureDetector(
        onTap: onTap,
        child: Container(
          height: 54,
          decoration: BoxDecoration(
            color: isGold
                ? const Color(0xFFB78628)
                : Colors.white.withValues(alpha: 0.08),
            borderRadius: BorderRadius.circular(14),
            border: isGold
                ? null
                : Border.all(
                    color: Colors.white.withValues(alpha: 0.15),
                  ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                icon,
                color: isGold ? const Color(0xFF1A1200) : Colors.white,
                size: 20,
              ),
              const SizedBox(height: 2),
              Text(
                label,
                style: TextStyle(
                  color: isGold ? const Color(0xFF1A1200) : Colors.white,
                  fontSize: 10,
                  fontWeight: FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
