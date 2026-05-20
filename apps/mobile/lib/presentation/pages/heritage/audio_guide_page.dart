import 'package:flutter/material.dart';

class AudioGuidePage extends StatefulWidget {
  const AudioGuidePage({super.key});
  @override
  State<AudioGuidePage> createState() => _AudioGuidePageState();
}

class _AudioGuidePageState extends State<AudioGuidePage> {
  bool _playing = false;
  double _progress = 0.32;
  double _speed = 1;
  int _langIdx = 0;
  static const _langs = ['🇺🇿', '🇬🇧', '🇷🇺', '🇨🇳'];
  static const _gold = Color(0xFFB78628);

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      body: Stack(
        children: [
          // Blurred heritage bg
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFF8B3A2A), Color(0xFF0D2337)],
              ),
            ),
          ),
          // Player card
          SafeArea(
            child: Column(
              children: [
                Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      GestureDetector(
                        onTap: () => Navigator.pop(context),
                        child: const Icon(
                          Icons.keyboard_arrow_down_rounded,
                          color: Colors.white,
                          size: 32,
                        ),
                      ),
                      const Spacer(),
                      const Text(
                        "Audio Yo'riqnoma",
                        style: TextStyle(
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
                // Player glass card
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
                      const Text(
                        "1-bo'lim: Kirish",
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        'Registon tarixi',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.6),
                          fontSize: 13,
                        ),
                      ),
                      const SizedBox(height: 24),
                      // Scrubber
                      SliderTheme(
                        data: SliderThemeData(
                          activeTrackColor: _gold,
                          inactiveTrackColor:
                              Colors.white.withValues(alpha: 0.2),
                          thumbColor: _gold,
                          overlayColor: _gold.withValues(alpha: 0.2),
                          trackHeight: 3,
                        ),
                        child: Slider(
                          value: _progress,
                          onChanged: (v) => setState(() => _progress = v),
                        ),
                      ),
                      Padding(
                        padding: const EdgeInsets.symmetric(horizontal: 4),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              '2:34',
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.6),
                                fontSize: 11,
                              ),
                            ),
                            Text(
                              '8:47',
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.6),
                                fontSize: 11,
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 16),
                      // Controls
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          IconButton(
                            icon: const Icon(
                              Icons.skip_previous_rounded,
                              color: Colors.white,
                            ),
                            onPressed: () {},
                          ),
                          IconButton(
                            icon: const Icon(
                              Icons.replay_10_rounded,
                              color: Colors.white,
                              size: 28,
                            ),
                            onPressed: () {},
                          ),
                          const SizedBox(width: 8),
                          GestureDetector(
                            onTap: () =>
                                setState(() => _playing = !_playing),
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
                                _playing
                                    ? Icons.pause_rounded
                                    : Icons.play_arrow_rounded,
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
                            onPressed: () {},
                          ),
                          IconButton(
                            icon: const Icon(
                              Icons.skip_next_rounded,
                              color: Colors.white,
                            ),
                            onPressed: () {},
                          ),
                        ],
                      ),
                      const SizedBox(height: 16),
                      // Speed + language
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          // Speed
                          Row(
                            children: [0.75, 1.0, 1.5, 2.0]
                                .map(
                                  (s) => GestureDetector(
                                    onTap: () =>
                                        setState(() => _speed = s),
                                    child: Container(
                                      margin: const EdgeInsets.only(right: 6),
                                      padding:
                                          const EdgeInsets.symmetric(
                                        horizontal: 8,
                                        vertical: 4,
                                      ),
                                      decoration: BoxDecoration(
                                        color: _speed == s
                                            ? _gold
                                            : Colors.white.withValues(
                                                alpha: 0.08,
                                              ),
                                        borderRadius:
                                            BorderRadius.circular(8),
                                      ),
                                      child: Text(
                                        '${s}x',
                                        style: TextStyle(
                                          color: _speed == s
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
                          // Language flags
                          Row(
                            children: List.generate(
                              4,
                              (i) => GestureDetector(
                                onTap: () =>
                                    setState(() => _langIdx = i),
                                child: Container(
                                  margin: const EdgeInsets.only(left: 4),
                                  padding: const EdgeInsets.all(4),
                                  decoration: BoxDecoration(
                                    border: _langIdx == i
                                        ? Border.all(
                                            color: _gold,
                                            width: 2,
                                          )
                                        : null,
                                    borderRadius: BorderRadius.circular(6),
                                  ),
                                  child: Text(
                                    _langs[i],
                                    style: const TextStyle(fontSize: 18),
                                  ),
                                ),
                              ),
                            ),
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
