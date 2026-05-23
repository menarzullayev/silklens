import 'package:flutter/material.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class ReviewComposerSheet extends ConsumerStatefulWidget {
  const ReviewComposerSheet({
    required this.heritagePubId,
    super.key,
  });

  final String heritagePubId;

  @override
  ConsumerState<ReviewComposerSheet> createState() => _ReviewComposerSheetState();
}

class _ReviewComposerSheetState extends ConsumerState<ReviewComposerSheet> {
  static const _gold = Color(0xFFB78628);
  static const _bg = Color(0xFF0D2337);

  int _starRating = 0;
  bool _hasPhoto = false;
  bool _isSubmitting = false;
  final _textController = TextEditingController();

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  String _s(String key) {
    final locale = ref.read(activeLocaleProvider).languageCode;
    return AppStrings.get(locale, key);
  }

  String get _starLabel {
    if (_starRating == 0) return _s('review_star_prompt');
    return [
      '',
      _s('review_star_1'),
      _s('review_star_2'),
      _s('review_star_3'),
      _s('review_star_4'),
      _s('review_star_5'),
    ][_starRating];
  }

  Future<void> _submitReview() async {
    final text = _textController.text.trim();
    if (text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_s('review_error_empty'))),
      );
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      final lang = ref.read(activeLocaleProvider).languageCode;
      await ref.read(silkLensApiClientProvider).createReview(
            heritagePubId: widget.heritagePubId,
            bodyMd: text,
            languageTag: lang,
            ratings: _starRating > 0
                ? [
                    {
                      'dimension_slug': 'overall',
                      'score': _starRating.toDouble(),
                    }
                  ]
                : null,
          );

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_s('review_success'))),
      );
      Navigator.pop(context, true);
    } catch (_) {
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(_s('review_error_submit'))),
      );
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
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
          Text(
            _s('review_title'),
            style: const TextStyle(
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
            _starLabel,
            style: TextStyle(
              color: _starRating == 0 ? Colors.white.withValues(alpha: 0.35) : _gold,
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
              border: Border.all(
                color: Colors.white.withValues(alpha: 0.12),
              ),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
            child: TextField(
              controller: _textController,
              maxLines: 4,
              style: const TextStyle(color: Colors.white, fontSize: 14),
              decoration: InputDecoration(
                hintText: _s('review_text_hint'),
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
              padding: const EdgeInsets.symmetric(
                horizontal: 14,
                vertical: 12,
              ),
              decoration: BoxDecoration(
                color: Colors.white.withValues(alpha: 0.06),
                borderRadius: BorderRadius.circular(14),
                border: Border.all(
                  color: _hasPhoto
                      ? _gold.withValues(alpha: 0.5)
                      : Colors.white.withValues(alpha: 0.12),
                ),
              ),
              child: Row(
                children: [
                  Icon(
                    _hasPhoto ? Icons.check_circle_rounded : Icons.add_photo_alternate_outlined,
                    color: _hasPhoto ? _gold : Colors.white.withValues(alpha: 0.5),
                    size: 22,
                  ),
                  const SizedBox(width: 10),
                  Text(
                    _hasPhoto ? _s('review_photo_added') : _s('review_photo_add'),
                    style: TextStyle(
                      color: _hasPhoto ? _gold : Colors.white.withValues(alpha: 0.6),
                      fontSize: 14,
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Submit button
          GestureDetector(
            onTap: _isSubmitting ? null : _submitReview,
            child: AnimatedContainer(
              duration: const Duration(milliseconds: 200),
              width: double.infinity,
              height: 52,
              decoration: BoxDecoration(
                gradient: (!_isSubmitting)
                    ? const LinearGradient(
                        colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
                      )
                    : null,
                color: _isSubmitting ? Colors.white.withValues(alpha: 0.08) : null,
                borderRadius: BorderRadius.circular(16),
              ),
              child: Center(
                child: _isSubmitting
                    ? const SizedBox(
                        width: 24,
                        height: 24,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : Text(
                        _s('review_submit'),
                        style: const TextStyle(
                          color: Color(0xFF1A1200),
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
