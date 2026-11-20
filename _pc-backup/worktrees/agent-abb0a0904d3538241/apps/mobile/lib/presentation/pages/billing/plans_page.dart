import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

class PlansPage extends StatefulWidget {
  const PlansPage({super.key});
  @override
  State<PlansPage> createState() => _PlansPageState();
}

class _PlansPageState extends State<PlansPage> {
  bool _annual = false;
  int _selected = 1; // Explorer recommended
  static const _gold = Color(0xFFB78628);

  static const _plans = [
    ('Bepul', '0', "AI tanish: 5/oy\nAudio: 3 ta\nAR: Yo'q"),
    ('Explorer ⭐', '29,900', 'AI tanish: 50/oy\nAudio: 20 ta\nAR: 5/oy'),
    (
      'Heritage Pro 💎',
      '89,900',
      'AI tanish: Cheksiz\nAudio: Cheksiz\nAR: Cheksiz',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: const Color(0xFF0D2337),
        leading: GestureDetector(
          onTap: () => Navigator.pop(context),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: const Text(
          'Obuna rejalar',
          style: TextStyle(color: Colors.white),
        ),
      ),
      body: Column(
        children: [
          // Monthly/Annual toggle
          Padding(
            padding: const EdgeInsets.all(16),
            child: Container(
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.08),
                borderRadius: BorderRadius.circular(24),
                border: Border.all(
                  color: Colors.white.withValues(alpha: 0.15),
                ),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _annual = false),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: !_annual ? _gold : Colors.transparent,
                          borderRadius: BorderRadius.circular(22),
                        ),
                        child: Center(
                          child: Text(
                            'Oylik',
                            style: TextStyle(
                              color: !_annual
                                  ? const Color(0xFF1A1200)
                                  : Colors.white,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                  Expanded(
                    child: GestureDetector(
                      onTap: () => setState(() => _annual = true),
                      child: AnimatedContainer(
                        duration: const Duration(milliseconds: 200),
                        padding: const EdgeInsets.symmetric(vertical: 10),
                        decoration: BoxDecoration(
                          color: _annual ? _gold : Colors.transparent,
                          borderRadius: BorderRadius.circular(22),
                        ),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Text(
                              'Yillik',
                              style: TextStyle(
                                color: _annual
                                    ? const Color(0xFF1A1200)
                                    : Colors.white,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 2,
                              ),
                              decoration: BoxDecoration(
                                color: const Color(0xFF4CAF50),
                                borderRadius: BorderRadius.circular(8),
                              ),
                              child: const Text(
                                '-40%',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 10,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ),
          // Plan cards
          Expanded(
            child: ListView.separated(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              itemCount: _plans.length,
              separatorBuilder: (_, __) => const SizedBox(height: 12),
              itemBuilder: (_, i) {
                final selected = _selected == i;
                final recommended = i == 1;
                return GestureDetector(
                  onTap: () => setState(() => _selected = i),
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    padding: const EdgeInsets.all(20),
                    decoration: BoxDecoration(
                      color: selected
                          ? Colors.white.withValues(alpha: 0.10)
                          : Colors.white.withValues(alpha: 0.05),
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: selected
                            ? _gold
                            : Colors.white.withValues(alpha: 0.12),
                        width: selected ? 2 : 1,
                      ),
                      boxShadow: selected
                          ? [
                              BoxShadow(
                                color: _gold.withValues(alpha: 0.2),
                                blurRadius: 16,
                              ),
                            ]
                          : null,
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            Text(
                              _plans[i].$1,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 18,
                                fontWeight: FontWeight.w700,
                              ),
                            ),
                            const Spacer(),
                            if (recommended)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 8,
                                  vertical: 3,
                                ),
                                decoration: BoxDecoration(
                                  color: _gold,
                                  borderRadius: BorderRadius.circular(8),
                                ),
                                child: const Text(
                                  'TAVSIYA',
                                  style: TextStyle(
                                    color: Color(0xFF1A1200),
                                    fontSize: 10,
                                    fontWeight: FontWeight.w800,
                                  ),
                                ),
                              ),
                          ],
                        ),
                        const SizedBox(height: 4),
                        Text(
                          i == 0
                              ? 'Bepul'
                              : "${_plans[i].$2} so'm/${_annual ? "yil" : "oy"}",
                          style: TextStyle(
                            color: i == 0
                                ? Colors.white.withValues(alpha: 0.5)
                                : _gold,
                            fontSize: 16,
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          _plans[i].$3,
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.65),
                            fontSize: 12,
                            height: 1.6,
                          ),
                        ),
                      ],
                    ),
                  ),
                );
              },
            ),
          ),
          // CTA
          Padding(
            padding: const EdgeInsets.all(16),
            child: GestureDetector(
              onTap: _selected == 0
                  ? null
                  : () => context.go('/billing/checkout'),
              child: Container(
                height: 54,
                width: double.infinity,
                decoration: BoxDecoration(
                  gradient: _selected == 0
                      ? null
                      : const LinearGradient(
                          colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                        ),
                  color: _selected == 0
                      ? Colors.white.withValues(alpha: 0.2)
                      : null,
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Center(
                  child: Text(
                    _selected == 0 ? 'Joriy reja' : '14 kun bepul sinov',
                    style: TextStyle(
                      color: _selected == 0
                          ? Colors.white.withValues(alpha: 0.5)
                          : const Color(0xFF1A1200),
                      fontSize: 16,
                      fontWeight: FontWeight.w700,
                    ),
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
