// Telegram-style AI chat page.
//
// Empty state shows prompt suggestions (localised). Each assistant bubble
// gets a TTS button (🔊) that fetches a signed mp3 URL via /v1/ai/tts and
// plays it through just_audio. When opened from a heritage detail page
// (route param `heritage_id`) the heritage context is attached to every
// outbound request.

import "package:flutter/material.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:just_audio/just_audio.dart";
import "package:silklens/core/logging/app_logger.dart";
import "package:silklens/domain/ai/entities/chat_message.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/providers/chat_provider.dart";

class ChatPage extends ConsumerStatefulWidget {
  const ChatPage({this.heritagePubIdContext, super.key});

  final String? heritagePubIdContext;

  @override
  ConsumerState<ChatPage> createState() => _ChatPageState();
}

class _ChatPageState extends ConsumerState<ChatPage> {
  final TextEditingController _input = TextEditingController();
  final ScrollController _scroll = ScrollController();
  final AudioPlayer _audio = AudioPlayer();

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      ref
          .read(chatControllerProvider.notifier)
          .setHeritageContext(widget.heritagePubIdContext);
    });
  }

  @override
  void dispose() {
    _input.dispose();
    _scroll.dispose();
    _audio.dispose();
    super.dispose();
  }

  Future<void> _send() async {
    final text = _input.text;
    if (text.trim().isEmpty) return;
    _input.clear();
    await ref.read(chatControllerProvider.notifier).send(text);
    if (_scroll.hasClients) {
      await _scroll.animateTo(
        _scroll.position.maxScrollExtent,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeOut,
      );
    }
  }

  Future<void> _play(ChatMessage message) async {
    final tts =
        await ref.read(chatControllerProvider.notifier).requestTts(message);
    if (tts == null) return;
    try {
      await _audio.setUrl(tts.signedUrl);
      await _audio.play();
    } on Exception catch (e, st) {
      AppLogger.instance.w("TTS playback failed", error: e, stackTrace: st);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final state = ref.watch(chatControllerProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n?.chatTitle ?? "Ask SilkLens")),
      body: Column(
        children: <Widget>[
          Expanded(
            child: state.messages.isEmpty
                ? _EmptyState(onSuggestionTap: (String s) {
                    _input.text = s;
                    _send();
                  })
                : ListView.builder(
                    key: const Key("chat.message_list"),
                    controller: _scroll,
                    padding: const EdgeInsets.all(12),
                    itemCount: state.messages.length,
                    itemBuilder: (BuildContext ctx, int i) {
                      final m = state.messages[i];
                      return _ChatBubble(
                        message: m,
                        onPlayTts: () => _play(m),
                      );
                    },
                  ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(8),
              child: Row(
                children: <Widget>[
                  Expanded(
                    child: TextField(
                      key: const Key("chat.input"),
                      controller: _input,
                      minLines: 1,
                      maxLines: 5,
                      decoration: InputDecoration(
                        hintText: l10n?.chatInputHint ?? "Type a message…",
                        border: const OutlineInputBorder(),
                      ),
                      onSubmitted: (_) => _send(),
                    ),
                  ),
                  const SizedBox(width: 8),
                  IconButton.filled(
                    key: const Key("chat.send"),
                    onPressed: state.isSending ? null : _send,
                    icon: state.isSending
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                        : const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptyState extends StatelessWidget {
  const _EmptyState({required this.onSuggestionTap});
  final ValueChanged<String> onSuggestionTap;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final suggestions = <String>[
      l10n?.chatSuggestionWhen ?? "When was this monument built?",
      l10n?.chatSuggestionHotels ?? "What are the best hotels nearby?",
      l10n?.chatSuggestionLegends ?? "Tell me a legend about this place.",
    ];
    return Center(
      key: const Key("chat.empty"),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: <Widget>[
            Icon(Icons.chat_bubble_outline,
                size: 64, color: Theme.of(context).colorScheme.primary),
            const SizedBox(height: 12),
            Text(
              l10n?.chatEmptyTitle ?? "Ask anything about the Silk Road",
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: suggestions
                  .map(
                    (String s) => ActionChip(
                      label: Text(s),
                      onPressed: () => onSuggestionTap(s),
                    ),
                  )
                  .toList(growable: false),
            ),
          ],
        ),
      ),
    );
  }
}

class _ChatBubble extends StatelessWidget {
  const _ChatBubble({required this.message, required this.onPlayTts});

  final ChatMessage message;
  final VoidCallback onPlayTts;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final isUser = message.isUser;
    final bg = isUser
        ? theme.colorScheme.primary
        : theme.colorScheme.surfaceContainerHighest;
    final fg = isUser ? theme.colorScheme.onPrimary : theme.colorScheme.onSurface;

    return Align(
      alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 4),
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
        constraints: BoxConstraints(
          maxWidth: MediaQuery.of(context).size.width * 0.75,
        ),
        decoration: BoxDecoration(
          color: bg,
          borderRadius: BorderRadius.only(
            topLeft: const Radius.circular(14),
            topRight: const Radius.circular(14),
            bottomLeft: Radius.circular(isUser ? 14 : 4),
            bottomRight: Radius.circular(isUser ? 4 : 14),
          ),
        ),
        child: message.pending
            ? const _TypingDots()
            : Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: <Widget>[
                  Text(message.content, style: TextStyle(color: fg)),
                  if (message.isAssistant && message.content.isNotEmpty)
                    Align(
                      alignment: Alignment.centerRight,
                      child: IconButton(
                        key: Key("chat.tts.${message.id}"),
                        iconSize: 18,
                        padding: EdgeInsets.zero,
                        constraints: const BoxConstraints(),
                        onPressed: onPlayTts,
                        icon: Icon(Icons.volume_up, color: fg),
                        tooltip:
                            AppLocalizations.of(context)?.chatTtsHint ?? "Play",
                      ),
                    ),
                ],
              ),
      ),
    );
  }
}

class _TypingDots extends StatefulWidget {
  const _TypingDots();
  @override
  State<_TypingDots> createState() => _TypingDotsState();
}

class _TypingDotsState extends State<_TypingDots>
    with SingleTickerProviderStateMixin {
  late final AnimationController _ctrl = AnimationController(
    vsync: this,
    duration: const Duration(milliseconds: 900),
  )..repeat();

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: 36,
      child: AnimatedBuilder(
        animation: _ctrl,
        builder: (BuildContext ctx, _) => Row(
          mainAxisSize: MainAxisSize.min,
          children: List<Widget>.generate(3, (int i) {
            final double t = ((_ctrl.value + i / 3) % 1);
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 2),
              child: Opacity(
                opacity: 0.3 + 0.7 * (1 - (t - 0.5).abs() * 2).clamp(0, 1),
                child: Container(
                  width: 6,
                  height: 6,
                  decoration: const BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.grey,
                  ),
                ),
              ),
            );
          }),
        ),
      ),
    );
  }
}
