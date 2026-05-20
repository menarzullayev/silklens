import 'package:flutter/material.dart';

class ReviewComposerSheet extends StatefulWidget {
  const ReviewComposerSheet({super.key});

  @override
  State<ReviewComposerSheet> createState() => _ReviewComposerSheetState();
}

class _ReviewComposerSheetState extends State<ReviewComposerSheet> {
  static const _gold = Color(0xFFB78628);
  static const _bg = Color(0xFF0D2337);

  int _starRating = 0;
  bool _hasPhoto = false;
  final _textController = TextEditingController();

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: _bg,
        borderRadius: const BorderRadius.vertical(top: Radius.circular(28)),
        border: Border.all(color: Colors.white.withValues(alpha: 0.10)),
      ),
      padding: EdgeInsets.only(
        left: 20,
        right: 20,
        top: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 20,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Handle bar
          Center(
            child: Container(
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.2),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          const SizedBox(height: 20),
          const Text(
            'Sharh yozing',
            style: TextStyle(
              color: Colors.white,
              fontSize: 20,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 20),

          // Star rating row
          Row(
            children: List.generate(5, (i) {
              final filled = i < _starRating;
              return GestureDetector(
                onTap: () => setState(() => _starRating = i + 1),
                child: Padding(
                  padding: const EdgeInsets.only(right: 8),
                  child: Icon(
                    filled ? Icons.star_rounded : Icons.star_outline_rounded,
                    color: filled ? _gold : Colors.white.withValues(alpha: 0.3),
                    size: 36,
                  ),
                ),
              );
            }),
          ),
          const SizedBox(height: 6),
          Text(
            _starRating == 0
                ? 'Yulduz tanlang'
                : ['', 'Yomon', 'Qoniqarli', 'Yaxshi', 'Ajoyib', "Zo'r!"][_starRating],
            style: TextStyle(
              color: _starRating == 0
                  ? Colors.white.withValues(alpha: 0.35)
                  : _gold,
              fontSize: 13,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 16),

          // Text area
          Container(
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.white.withValues(alpha: 0.12)),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
            child: TextField(
              controller: _textController,
              maxLines: 4,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                hintText: "Taassurotlaringizni baham ko'ring...",
                hintStyle: TextStyle(
                  color: Colors.white.withValues(alpha: 0.35),
                  fontSize: 14,
                ),
                border: InputBorder.none,
              ),
            ),
          ),
          const SizedBox(height: 14),

          // Photo picker row
          GestureDetector(
            onTap: () => setState(() => _hasPhoto = !_hasPhoto),
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: _hasPhoto
                      ? _gold.withValues(alpha: 0.5)
                      : Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Row(children: [
                Icon(
                  _hasPhoto
                      ? Icons.check_circle_rounded
                      : Icons.add_photo_alternate_outlined,
                  color: _hasPhoto ? _gold : Colors.white.withValues(alpha: 0.5),
                  size: 22,
                ),
                const SizedBox(width: 10),
                Text(
                  _hasPhoto ? "Foto qo'shildi" : "Foto qo'shish (ixtiyoriy)",
                  style: TextStyle(
                    color: _hasPhoto
                        ? _gold
                        : Colors.white.withValues(alpha: 0.6),
                    fontSize: 14,
                  ),
                ),
              ],),
            ),
          ),
          const SizedBox(height: 20),

          // Submit button
          GestureDetector(
            onTap: _starRating > 0 ? () => Navigator.pop(context) : null,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: double.infinity,
              height: 52,
              decoration: BoxDecoration(
                gradient: _starRating > 0
                    ? const LinearGradient(
                        colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                      )
                    : null,
                color: _starRating == 0
                    ? Colors.white.withValues(alpha: 0.08)
                    : null,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Center(
                child: Text(
                  'Sharh yuborish',
                  style: TextStyle(
                    color: _starRating > 0
                        ? const Color(0xFF1A1200)
                        : Colors.white.withValues(alpha: 0.35),
                    fontSize: 16,
                    fontWeight: FontWeight.w700,
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
