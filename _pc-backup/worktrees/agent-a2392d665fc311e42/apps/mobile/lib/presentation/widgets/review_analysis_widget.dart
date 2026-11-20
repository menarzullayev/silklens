// SILK-0138 — ReviewAnalysisWidget
// Embeddable widget that shows AI-generated review analysis for a heritage
// site. Intended for use inside HeritageDetailPage below the reviews section.

import 'package:flutter/material.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/review_analysis_provider.dart';

class ReviewAnalysisWidget extends ConsumerWidget {
  const ReviewAnalysisWidget({
    required this.heritagePubId,
    super.key,
  });

  final String heritagePubId;

  static const _gold = Color(0xFFB78628);

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final analysisAsync = ref.watch(reviewAnalysisProvider(heritagePubId));

    return analysisAsync.when(
      loading: () => Padding(
        padding: const EdgeInsets.symmetric(vertical: 16),
        child: Row(
          children: [
            const SizedBox(
              width: 18,
              height: 18,
              child: CircularProgressIndicator(
                color: _gold,
                strokeWidth: 2,
              ),
            ),
            const SizedBox(width: 10),
            Text(
              _s('review_analysis_loading'),
              style: const TextStyle(color: Colors.white54, fontSize: 13),
            ),
          ],
        ),
      ),
      error: (_, __) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Text(
          _s('review_analysis_error'),
          style: const TextStyle(color: Colors.white38, fontSize: 13),
        ),
      ),
      data: (analysis) => _AnalysisCard(analysis: analysis, s: _s),
    );
  }
}

// ---------------------------------------------------------------------------

class _AnalysisCard extends StatelessWidget {
  const _AnalysisCard({required this.analysis, required this.s});

  final Map<String, dynamic> analysis;
  final String Function(String) s;

  static const _gold = Color(0xFFB78628);

  @override
  Widget build(BuildContext context) {
    final authenticity = (analysis['authenticity_score'] as num?)?.toDouble() ?? 0.0;
    final summaryMd = analysis['summary_md'] as String? ?? '';
    final pros = (analysis['top_pros'] as List?)?.cast<String>() ?? [];
    final cons = (analysis['top_cons'] as List?)?.cast<String>() ?? [];
    final worth = analysis['worth_visiting'] as bool? ?? true;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: _gold.withValues(alpha: 0.25),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header row
          Row(
            children: [
              const Icon(Icons.auto_awesome, color: _gold, size: 18),
              const SizedBox(width: 8),
              Text(
                s('review_analysis_title'),
                style: const TextStyle(
                  color: Colors.white,
                  fontWeight: FontWeight.w700,
                  fontSize: 15,
                ),
              ),
              const Spacer(),
              // Worth visiting badge
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 4,
                ),
                decoration: BoxDecoration(
                  color: worth
                      ? const Color(0xFF4CAF50).withValues(alpha: 0.2)
                      : Colors.red.withValues(alpha: 0.2),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  worth ? s('review_analysis_worth_yes') : s('review_analysis_worth_no'),
                  style: TextStyle(
                    color: worth ? const Color(0xFF4CAF50) : Colors.redAccent,
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Authenticity score bar
          Row(
            children: [
              Text(
                s('review_analysis_authenticity'),
                style: const TextStyle(
                  color: Colors.white60,
                  fontSize: 12,
                ),
              ),
              const Spacer(),
              Text(
                '${(authenticity * 100).round()}%',
                style: const TextStyle(
                  color: _gold,
                  fontWeight: FontWeight.w700,
                  fontSize: 13,
                ),
              ),
            ],
          ),
          const SizedBox(height: 6),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: authenticity.clamp(0.0, 1.0),
              backgroundColor: Colors.white.withValues(alpha: 0.1),
              valueColor: const AlwaysStoppedAnimation<Color>(_gold),
              minHeight: 6,
            ),
          ),

          // Summary
          if (summaryMd.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              s('review_analysis_summary'),
              style: const TextStyle(
                color: Colors.white60,
                fontSize: 11,
                letterSpacing: 1.1,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              summaryMd,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 13,
                height: 1.5,
              ),
            ),
          ],

          // Pros
          if (pros.isNotEmpty) ...[
            const SizedBox(height: 12),
            Text(
              s('review_analysis_pros'),
              style: const TextStyle(
                color: Colors.white60,
                fontSize: 11,
                letterSpacing: 1.1,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            ...pros.map(
              (p) => _BulletRow(
                text: p,
                color: const Color(0xFF4CAF50),
                icon: Icons.check_circle_outline,
              ),
            ),
          ],

          // Cons
          if (cons.isNotEmpty) ...[
            const SizedBox(height: 8),
            Text(
              s('review_analysis_cons'),
              style: const TextStyle(
                color: Colors.white60,
                fontSize: 11,
                letterSpacing: 1.1,
                fontWeight: FontWeight.w600,
              ),
            ),
            const SizedBox(height: 4),
            ...cons.map(
              (c) => _BulletRow(
                text: c,
                color: Colors.redAccent,
                icon: Icons.remove_circle_outline,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------

class _BulletRow extends StatelessWidget {
  const _BulletRow({
    required this.text,
    required this.color,
    required this.icon,
  });

  final String text;
  final Color color;
  final IconData icon;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, color: color, size: 14),
          const SizedBox(width: 6),
          Expanded(
            child: Text(
              text,
              style: const TextStyle(
                color: Colors.white70,
                fontSize: 13,
                height: 1.4,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
