// Reads the runtime app name. Per Project-Decisions §1 we never hard-code
// `"SilkLens"` in user-visible widgets. Always go through this widget (or
// `AppLocalizations.of(context).appName`) so the admin panel's tenant
// branding can override it in a future build.

import 'package:flutter/widgets.dart';
import 'package:silklens/l10n/app_localizations.dart';

class BrandedAppName extends StatelessWidget {
  const BrandedAppName({this.style, super.key});

  final TextStyle? style;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return Text(l10n.appName ?? 'SilkLens', style: style);
  }
}
