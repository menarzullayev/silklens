// SILK-0096 — AudioGuidePage wired to real just_audio + /v1/ai/tts.
// Replaces mock _progress state with live AudioPlayer from just_audio.
// Accepts optional heritagePubId + heritageText via route query params.

import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:go_router/go_router.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:just_audio/just_audio.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';

// Language code → flag emoji mapping kept in sync with app locales.
const _langFlags = {
  'uz': '🇺🇿',
  'en': '🇬🇧',
  'ru': '🇷🇺',
  'zh': '🇨🇳',
};

const _gold = Color(0xFFB78628);

class AudioGuidePage extends HookConsumerWidget {
  const AudioGuidePage({
    super.key,
    this.heritagePubId,
    this.heritageText,
  });

  final String? heritagePubId;
  final String? heritageText;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final locale = LocaleService.instance.locale;
    String s(String key) => AppStrings.get(locale, key);

    // Create & memoize AudioPlayer for this widget lifetime.
    final player = useMemoized(AudioPlayer.new);

    // Dispose player when widget is removed.
    useEffect(() => player.dispose, [player]);

    final isPlaying = useState(false);
    final isLoading = useState(true);
    final hasError = useState(false);
    final position = useState(Duration.zero);
    final duration = useState(Duration.zero);
    final speed = useState<double>(1);
    final selectedLang = useState(locale);

    // Wire player streams to local state.
    useEffect(
      () {
        final subs = [
          player.positionStream.listen((p) => position.value = p),
          player.durationStream.listen((d) {
            if (d != null) duration.value = d;
          }),
          player.playingStream.listen((p) => isPlaying.value = p),
        ];
        return () {
          for (final s in subs) {
            s.cancel();
          }
        };
      },
      [player],
    );

    // Load (or reload) audio whenever selected language changes.
    Future<void> loadAudio(String lang) async {
      isLoading.value = true;
      hasError.value = false;
      position.value = Duration.zero;
      duration.value = Duration.zero;
      try {
        await player.stop();
        final client = ref.read(silkLensApiClientProvider);
        final text = (heritageText?.isNotEmpty ?? false)
            ? heritageText!
            // Fallback placeholder when no text is injected.
            : "Bu tarixiy obida haqida audio yo'riqnoma yuklanmoqda...";
        final ttsResponse = await client.generateTts(
          text: text,
          language: lang,
        );
        final url = ttsResponse['signed_url'] as String? ?? ttsResponse['url'] as String?;
        if (url != null && url.isNotEmpty) {
          await player.setUrl(url);
        }
      } catch (_) {
        hasError.value = true;
      } finally {
        isLoading.value = false;
      }
    }

    // Initial load.
    useEffect(
      () {
        loadAudio(selectedLang.value);
        return null;
      },
      const [],
    );

    // Reload when language chip is tapped.
    // (handled inline in the chip tap callback below)

    String formatDuration(Duration d) {
      final m = d.inMinutes.remainder(60).toString().padLeft(2, '0');
      final sec = d.inSeconds.remainder(60).toString().padLeft(2, '0');
      return '$m:$sec';
    }

    final maxMs = math.max(duration.value.inMilliseconds, 1);
    final progress = (position.value.inMilliseconds / maxMs).clamp(0.0, 1.0);

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Stack(
        children: [
          // Background gradient.
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFF8B3A2A), Color(0xFF0D2337)],
              ),
            ),
          ),

          // Player UI.
          SafeArea(
            child: Column(
              children: [
                // --- Top bar ---
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      GestureDetector(
                        onTap: () => context.pop(),
                        child: const Icon(
                          Icons.keyboard_arrow_down_rounded,
                          color: Colors.white,
                          size: 32,
                        ),
                      ),
                      const Spacer(),
                      Text(
                        s('audio_guide_title'),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      const Spacer(),
                      const SizedBox(width: 32),
                    ],
                  ),
                ),

                const Spacer(),

                // --- Glass player card ---
                Container(
                  margin: const EdgeInsets.all(16),
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: Colors.white.withValues(alpha: 0.10),
                    borderRadius: BorderRadius.circular(28),
                    border: Border.all(
                      color: Colors.white.withValues(alpha: 0.20),
                    ),
                  ),
                  child: Column(
                    children: [
                      Text(
                        s('audio_guide_section'),
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 4),
                      if (heritagePubId != null)
                        Text(
                          heritagePubId!,
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.6),
                            fontSize: 13,
                          ),
                        ),
                      const SizedBox(height: 24),

                      // --- Loading / error state ---
                      if (isLoading.value)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          child: Column(
                            children: [
                              const CircularProgressIndicator(
                                color: _gold,
                                strokeWidth: 2,
                              ),
                              const SizedBox(height: 10),
                              Text(
                                s('audio_guide_loading'),
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.6),
                                  fontSize: 13,
                                ),
                              ),
                            ],
                          ),
                        )
                      else if (hasError.value)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 12),
                          child: Column(
                            children: [
                              Text(
                                s('audio_guide_error'),
                                style: const TextStyle(
                                  color: Color(0xFFE57373),
                                  fontSize: 13,
                                ),
                              ),
                              const SizedBox(height: 8),
                              GestureDetector(
                                onTap: () => loadAudio(selectedLang.value),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 16,
                                    vertical: 8,
                                  ),
                                  decoration: BoxDecoration(
                                    border: Border.all(color: _gold),
                                    borderRadius: BorderRadius.circular(12),
                                  ),
                                  child: Text(
                                    s('audio_guide_retry'),
                                    style: const TextStyle(
                                      color: _gold,
                                      fontSize: 13,
                                    ),
                                  ),
                                ),
                              ),
                            ],
                          ),
                        )
                      else ...[
                        // --- Scrubber ---
                        SliderTheme(
                          data: SliderThemeData(
                            activeTrackColor: _gold,
                            inactiveTrackColor: Colors.white.withValues(alpha: 0.2),
                            thumbColor: _gold,
                            overlayColor: _gold.withValues(alpha: 0.2),
                            trackHeight: 3,
                          ),
                          child: Slider(
                            value: progress,
                            onChanged: (v) {
                              final seekMs = (v * duration.value.inMilliseconds).toInt();
                              player.seek(Duration(milliseconds: seekMs));
                            },
                          ),
                        ),
                        Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 4),
                          child: Row(
                            mainAxisAlignment: MainAxisAlignment.spaceBetween,
                            children: [
                              Text(
                                formatDuration(position.value),
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.6),
                                  fontSize: 11,
                                ),
                              ),
                              Text(
                                formatDuration(duration.value),
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.6),
                                  fontSize: 11,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],

                      const SizedBox(height: 16),

                      // --- Playback controls ---
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          IconButton(
                            icon: const Icon(
                              Icons.skip_previous_rounded,
                              color: Colors.white,
                            ),
                            onPressed: isLoading.value ? null : () => player.seek(Duration.zero),
                          ),
                          IconButton(
                            icon: const Icon(
                              Icons.replay_10_rounded,
                              color: Colors.white,
                              size: 28,
                            ),
                            onPressed: isLoading.value
                                ? null
                                : () => player.seek(
                                      Duration(
                                        milliseconds: math.max(
                                          0,
                                          position.value.inMilliseconds - 10000,
                                        ),
                                      ),
                                    ),
                          ),
                          const SizedBox(width: 8),
                          GestureDetector(
                            onTap: isLoading.value
                                ? null
                                : () {
                                    if (isPlaying.value) {
                                      player.pause();
                                    } else {
                                      player.play();
                                    }
                                  },
                            child: Container(
                              width: 64,
                              height: 64,
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [
                                    Color(0xFFB78628),
                                    Color(0xFFE5C97A),
                                  ],
                                ),
                                shape: BoxShape.circle,
                                boxShadow: [
                                  BoxShadow(
                                    color: _gold.withValues(alpha: 0.4),
                                    blurRadius: 16,
                                  ),
                                ],
                              ),
                              child: Icon(
                                isPlaying.value ? Icons.pause_rounded : Icons.play_arrow_rounded,
                                color: const Color(0xFF1A1200),
                                size: 36,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          IconButton(
                            icon: const Icon(
                              Icons.forward_10_rounded,
                              color: Colors.white,
                              size: 28,
                            ),
                            onPressed: isLoading.value
                                ? null
                                : () => player.seek(
                                      Duration(
                                        milliseconds: math.min(
                                          duration.value.inMilliseconds,
                                          position.value.inMilliseconds + 10000,
                                        ),
                                      ),
                                    ),
                          ),
                          IconButton(
                            icon: const Icon(
                              Icons.skip_next_rounded,
                              color: Colors.white,
                            ),
                            onPressed: isLoading.value ? null : () => player.seek(duration.value),
                          ),
                        ],
                      ),

                      const SizedBox(height: 16),

                      // --- Speed + language ---
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          // Speed chips
                          Row(
                            children: [0.75, 1.0, 1.5, 2.0]
                                .map(
                                  (sp) => GestureDetector(
                                    onTap: () {
                                      speed.value = sp;
                                      player.setSpeed(sp);
                                    },
                                    child: Container(
                                      margin: const EdgeInsets.only(right: 6),
                                      padding: const EdgeInsets.symmetric(
                                        horizontal: 8,
                                        vertical: 4,
                                      ),
                                      decoration: BoxDecoration(
                                        color: speed.value == sp
                                            ? _gold
                                            : Colors.white.withValues(
                                                alpha: 0.08,
                                              ),
                                        borderRadius: BorderRadius.circular(8),
                                      ),
                                      child: Text(
                                        '${sp}x',
                                        style: TextStyle(
                                          color: speed.value == sp
                                              ? const Color(0xFF1A1200)
                                              : Colors.white,
                                          fontSize: 11,
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ),
                                  ),
                                )
                                .toList(),
                          ),
                          // Language flag chips
                          Row(
                            children: _langFlags.entries
                                .map(
                                  (e) => GestureDetector(
                                    onTap: () {
                                      if (selectedLang.value != e.key) {
                                        selectedLang.value = e.key;
                                        loadAudio(e.key);
                                      }
                                    },
                                    child: Container(
                                      margin: const EdgeInsets.only(left: 4),
                                      padding: const EdgeInsets.all(4),
                                      decoration: BoxDecoration(
                                        border: selectedLang.value == e.key
                                            ? Border.all(
                                                color: _gold,
                                                width: 2,
                                              )
                                            : null,
                                        borderRadius: BorderRadius.circular(6),
                                      ),
                                      child: Text(
                                        e.value,
                                        style: const TextStyle(fontSize: 18),
                                      ),
                                    ),
                                  ),
                                )
                                .toList(),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 16),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
