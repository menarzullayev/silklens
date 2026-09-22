import 'package:flutter/material.dart';

class SilkAppBar extends StatelessWidget implements PreferredSizeWidget {
  const SilkAppBar({
    super.key,
    this.title,
    this.leading,
    this.actions,
    this.blurFraction = 0.0,
    this.centerTitle = false,
  });

  final String? title;
  final Widget? leading;
  final List<Widget>? actions;
  final double blurFraction; // 0.0 transparent → 1.0 full glass
  final bool centerTitle;

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08 * blurFraction),
        border: Border(
          bottom: BorderSide(
            color: Colors.white.withValues(alpha: 0.10 * blurFraction),
          ),
        ),
      ),
      child: SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 8),
          child: Row(
            children: [
              if (leading != null) leading! else const SizedBox(width: 48),
              if (centerTitle)
                Expanded(
                  child: Center(child: _titleWidget()),
                )
              else
                Expanded(child: _titleWidget()),
              if (actions != null) ...actions! else const SizedBox(width: 48),
            ],
          ),
        ),
      ),
    );
  }

  Widget _titleWidget() {
    if (title == null) return const SizedBox.shrink();
    return Text(
      title!,
      style: const TextStyle(
        color: Colors.white,
        fontSize: 17,
        fontWeight: FontWeight.w600,
      ),
      overflow: TextOverflow.ellipsis,
    );
  }
}
