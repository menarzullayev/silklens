import 'package:flutter/material.dart';
import 'package:local_auth/local_auth.dart';

class BiometricButton extends StatefulWidget {
  const BiometricButton({super.key, this.onSuccess});
  final VoidCallback? onSuccess;

  @override
  State<BiometricButton> createState() => _BiometricButtonState();
}

class _BiometricButtonState extends State<BiometricButton> {
  final _auth = LocalAuthentication();
  bool _available = false;

  @override
  void initState() {
    super.initState();
    _checkBiometrics();
  }

  Future<void> _checkBiometrics() async {
    try {
      final available = await _auth.canCheckBiometrics;
      if (mounted) setState(() => _available = available);
    } catch (_) {}
  }

  Future<void> _authenticate() async {
    try {
      final ok = await _auth.authenticate(
        localizedReason: 'SilkLens ga kirish uchun tasdiqlang',
        options: const AuthenticationOptions(
          stickyAuth: true,
        ),
      );
      if (ok && mounted) widget.onSuccess?.call();
    } catch (_) {}
  }

  @override
  Widget build(BuildContext context) {
    if (!_available) return const SizedBox.shrink();
    return GestureDetector(
      onTap: _authenticate,
      child: Container(
        height: 52,
        decoration: BoxDecoration(
          color: Colors.white.withValues(alpha: 0.10),
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.fingerprint,
              color: Colors.white.withValues(alpha: 0.8),
              size: 26,
            ),
            const SizedBox(width: 10),
            Text(
              'Biometrik kirish',
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.8),
                fontSize: 15,
                fontWeight: FontWeight.w500,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
