import 'package:flutter/material.dart';

/// Placeholder logo. FAZA 2 swaps this for an asset pulled from the
/// tenant_branding endpoint.
class SilkLensLogo extends StatelessWidget {
  const SilkLensLogo({this.size = 64, super.key});

  final double size;

  @override
  Widget build(BuildContext context) =>
      Icon(Icons.travel_explore, size: size, color: Theme.of(context).colorScheme.primary);
}
