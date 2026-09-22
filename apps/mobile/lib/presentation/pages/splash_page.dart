import 'package:flutter/material.dart';
import 'package:silklens/l10n/app_localizations.dart';

class SplashPage extends StatelessWidget {
  const SplashPage({super.key});

  @override
  Widget build(BuildContext context) {
    final appName = AppLocalizations.of(context).appName;
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.auto_awesome_rounded,
              key: Key('splash.logo'),
              size: 80,
              color: Color(0xFFB78628),
            ),
            const SizedBox(height: 24),
            Text(
              appName,
              key: const Key('splash.app_name'),
              style: const TextStyle(
                color: Colors.white,
                fontSize: 32,
                fontWeight: FontWeight.w800,
                letterSpacing: 1.2,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
