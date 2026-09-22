import 'package:flutter/material.dart';

class StarRating extends StatelessWidget {
  const StarRating({
    required this.rating,
    super.key,
    this.onChanged,
    this.size = 28,
    this.count = 5,
  });

  final double rating;
  final ValueChanged<int>? onChanged;
  final double size;
  final int count;

  bool get _interactive => onChanged != null;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: List.generate(count, (i) {
        final filled = i < rating;
        final star = Icon(
          filled ? Icons.star_rounded : Icons.star_outline_rounded,
          size: size,
          color: const Color(0xFFB78628),
        );
        if (!_interactive) return star;
        return GestureDetector(
          onTap: () => onChanged!(i + 1),
          child: star,
        );
      }),
    );
  }
}
