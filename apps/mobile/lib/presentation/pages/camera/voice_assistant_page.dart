// SILK-0101 — VoiceAssistantPage
//
// Hold-to-listen mic button. Transcribes via /v1/ai/asr → resolves intent
// via /v1/ai/voice-intent. State lives in VoiceNotifier (recognition_provider).
// Audio recording is done with the `record` package when available; the page
// degrades gracefully with a "recording not available" message when the
// permission or platform binding is absent so the UI is always usable.

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/presentation/providers/recognition_provider.dart';

class VoiceAssistantPage extends ConsumerStatefulWidget {
  const VoiceAssistantPage({super.key});

  @override
  ConsumerState<VoiceAssistantPage> createState() => _VoiceAssistantPageState();
}

class _VoiceAssistantPageState extends ConsumerState<VoiceAssistantPage>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulseCtrl;
  late final Animation<double> _pulse;

  // ---- helpers ----

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  // ---- lifecycle ----

  @override
  void initState() {
    super.initState();
    SystemChrome.setSystemUIOverlayStyle(
      const SystemUiOverlayStyle(
        statusBarColor: Colors.transparent,
        statusBarIconBrightness: Brightness.light,
        systemNavigationBarColor: Color(0xFF0D2337),
        systemNavigationBarIconBrightness: Brightness.light,
      ),
    );

    _pulseCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    )..repeat(reverse: true);

    _pulse = Tween<double>(begin: 0.95, end: 1.08).animate(
      CurvedAnimation(parent: _pulseCtrl, curve: Curves.easeInOut),
    );
  }

  @override
  void dispose() {
    _pulseCtrl.dispose();
    super.dispose();
  }

  // ---- actions ----

  void _onMicDown() {
    ref.read(voiceProvider.notifier).startListening();
    _pulseCtrl.repeat(reverse: true);
  }

  Future<void> _onMicUp() async {
    ref.read(voiceProvider.notifier).stopListening();
    _pulseCtrl.stop();

    // Audio recording integration point: when a `record` / `flutter_sound`
    // binding lands (SILK-0105), swap the stub bytes below for the real
    // captured audio file bytes.
    //
    // For now we show a friendly "feature coming" state so the page is
    // visually complete and fully i18n'd today.
    setState(() {}); // trigger rebuild to show feedback
    _showComingSoon();
  }

  void _showComingSoon() {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(_s('voice_recording_soon')),
        backgroundColor: const Color(0xFF1A3A5C),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        duration: const Duration(seconds: 3),
      ),
    );
  }

  void _onReset() {
    ref.read(voiceProvider.notifier).reset();
    _pulseCtrl.repeat(reverse: true);
  }

  // ---- build ----

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(voiceProvider);
    final isListening = state is VoiceListening;
    final isProcessing = state is VoiceProcessing;

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFF0D2337), Color(0xFF1A3A5C), Color(0xFF0D2337)],
            stops: [0.0, 0.5, 1.0],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Top bar
              _buildTopBar(),
              const SizedBox(height: 32),

              // Status label
              AnimatedSwitcher(
                duration: const Duration(milliseconds: 250),
                child: Text(
                  key: ValueKey(state.runtimeType),
                  _statusLabel(state),
                  style: TextStyle(
                    color: isListening ? Colors.redAccent : Colors.white60,
                    fontSize: 15,
                    letterSpacing: 0.2,
                  ),
                ),
              ),
              const SizedBox(height: 40),

              // Mic button
              _buildMicButton(
                isListening: isListening,
                isProcessing: isProcessing,
              ),
              const SizedBox(height: 40),

              // Result card
              if (state is VoiceResult) _buildResultCard(state),

              // Error card
              if (state is VoiceError) _buildErrorCard(state),

              const Spacer(),

              // Example commands
              _buildExampleCommands(),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }

  // ---- sub-widgets ----

  Widget _buildTopBar() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      child: Row(
        children: [
          Material(
            color: Colors.white.withAlpha(20),
            borderRadius: BorderRadius.circular(24),
            child: InkWell(
              borderRadius: BorderRadius.circular(24),
              onTap: () => context.pop(),
              child: const Padding(
                padding: EdgeInsets.all(10),
                child: Icon(
                  Icons.arrow_back_ios_new,
                  color: Colors.white,
                  size: 20,
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Text(
            _s('voice_title'),
            style: const TextStyle(
              color: Colors.white,
              fontSize: 18,
              fontWeight: FontWeight.w600,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMicButton({
    required bool isListening,
    required bool isProcessing,
  }) {
    final color = isListening ? Colors.redAccent : const Color(0xFFB78628);

    return GestureDetector(
      onTapDown: (_) => _onMicDown(),
      onTapUp: (_) => _onMicUp(),
      onTapCancel: () => ref.read(voiceProvider.notifier).stopListening(),
      child: ScaleTransition(
        scale: isListening ? _pulse : const AlwaysStoppedAnimation(1),
        child: Container(
          width: 120,
          height: 120,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: color.withAlpha(30),
            border: Border.all(color: color, width: 3),
            boxShadow: [
              BoxShadow(
                color: color.withAlpha(isListening ? 80 : 40),
                blurRadius: isListening ? 32 : 16,
                spreadRadius: isListening ? 8 : 2,
              ),
            ],
          ),
          child: isProcessing
              ? const Center(
                  child: SizedBox(
                    width: 36,
                    height: 36,
                    child: CircularProgressIndicator(
                      color: Color(0xFFB78628),
                      strokeWidth: 2.5,
                    ),
                  ),
                )
              : Icon(
                  isListening ? Icons.mic : Icons.mic_none,
                  size: 52,
                  color: color,
                ),
        ),
      ),
    );
  }

  Widget _buildResultCard(VoiceResult result) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 28),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(15),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: const Color(0xFFB78628).withAlpha(80),
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _s('voice_you_said'),
            style: const TextStyle(color: Colors.white38, fontSize: 11),
          ),
          const SizedBox(height: 6),
          Text(
            result.transcript,
            style: const TextStyle(
              color: Colors.white,
              fontSize: 15,
              height: 1.4,
            ),
          ),
          if (result.intent != null && result.intent!.isNotEmpty) ...[
            const SizedBox(height: 10),
            Row(
              children: [
                const Icon(
                  Icons.bolt,
                  color: Color(0xFFB78628),
                  size: 14,
                ),
                const SizedBox(width: 4),
                Text(
                  '${_s('voice_intent')}: ${result.intent!}',
                  style: const TextStyle(
                    color: Color(0xFFB78628),
                    fontSize: 12,
                  ),
                ),
              ],
            ),
          ],
          const SizedBox(height: 12),
          GestureDetector(
            onTap: _onReset,
            child: Text(
              _s('voice_try_again'),
              style: const TextStyle(
                color: Colors.white38,
                fontSize: 13,
                decoration: TextDecoration.underline,
                decorationColor: Colors.white38,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildErrorCard(VoiceError err) {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 28),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: Colors.redAccent.withAlpha(20),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: Colors.redAccent.withAlpha(80)),
      ),
      child: Row(
        children: [
          const Icon(Icons.error_outline, color: Colors.redAccent, size: 18),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              _s('voice_error'),
              style: const TextStyle(color: Colors.redAccent, fontSize: 13),
            ),
          ),
          GestureDetector(
            onTap: _onReset,
            child: const Icon(Icons.refresh, color: Colors.redAccent, size: 20),
          ),
        ],
      ),
    );
  }

  Widget _buildExampleCommands() {
    final commands = [
      _s('voice_example_1'),
      _s('voice_example_2'),
      _s('voice_example_3'),
      _s('voice_example_4'),
    ];

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 28),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            _s('voice_examples_header'),
            style: const TextStyle(
              color: Colors.white54,
              fontSize: 12,
              letterSpacing: 0.5,
            ),
          ),
          const SizedBox(height: 10),
          ...commands.map(
            (cmd) => Padding(
              padding: const EdgeInsets.symmetric(vertical: 3),
              child: Row(
                children: [
                  const Icon(
                    Icons.chevron_right,
                    size: 14,
                    color: Color(0xFFB78628),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    cmd,
                    style: const TextStyle(
                      color: Colors.white38,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _statusLabel(VoiceState state) => switch (state) {
        VoiceListening() => _s('voice_listening'),
        VoiceProcessing() => _s('voice_processing'),
        VoiceResult() => _s('voice_done'),
        VoiceError() => _s('voice_error_label'),
        VoiceIdle() => _s('voice_idle'),
      };
}
