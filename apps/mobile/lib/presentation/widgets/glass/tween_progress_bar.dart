import 'package:flutter/material.dart';

class TweenProgressBar extends StatefulWidget {
  const TweenProgressBar({
    required this.value,
    super.key,
    this.height = 8,
    this.borderRadius = 4,
    this.backgroundColor,
    this.delay = Duration.zero,
  });

  final double value; // 0.0 to 1.0
  final double height;
  final double borderRadius;
  final Color? backgroundColor;
  final Duration delay;

  @override
  State<TweenProgressBar> createState() => _TweenProgressBarState();
}

class _TweenProgressBarState extends State<TweenProgressBar>
    with SingleTickerProviderStateMixin {
  late AnimationController _ctrl;
  late Animation<double> _anim;
  double _target = 0;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1200),
    );
    _anim = CurvedAnimation(parent: _ctrl, curve: Curves.easeOut);
    Future.delayed(widget.delay, () {
      if (mounted) {
        _target = widget.value;
        _ctrl.forward();
      }
    });
  }

  @override
  void didUpdateWidget(TweenProgressBar old) {
    super.didUpdateWidget(old);
    if (old.value != widget.value) {
      _target = widget.value;
      _ctrl
        ..reset()
        ..forward();
    }
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _anim,
      builder: (_, __) => Container(
        height: widget.height,
        decoration: BoxDecoration(
          color: widget.backgroundColor ?? Colors.white.withValues(alpha: 0.12),
          borderRadius: BorderRadius.circular(widget.borderRadius),
        ),
        child: FractionallySizedBox(
          widthFactor: (_anim.value * _target).clamp(0.0, 1.0),
          alignment: Alignment.centerLeft,
          child: Container(
            decoration: BoxDecoration(
              gradient: const LinearGradient(
                colors: [Color(0xFFB78628), Color(0xFFE5C97A)],
              ),
              borderRadius: BorderRadius.circular(widget.borderRadius),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFFB78628).withValues(alpha: 0.4),
                  blurRadius: 6,
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
