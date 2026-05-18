// Chat state — list of messages + send orchestration.
//
// Streaming is not implemented yet (backend roadmap). We render an optimistic
// "pending" assistant bubble (typing indicator) until the round-trip
// completes, then replace it with the server response.

import "package:flutter/foundation.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/data/repositories/chat_repository_impl.dart";
import "package:silklens/domain/ai/entities/chat_message.dart";
import "package:silklens/domain/ai/repositories/chat_repository.dart";
import "package:silklens/presentation/providers/locale_provider.dart";
import "package:uuid/uuid.dart";

@immutable
class ChatState {
  const ChatState({
    required this.messages,
    this.conversationId,
    this.heritagePubIdContext,
    this.failure,
    this.isSending = false,
  });

  final List<ChatMessage> messages;
  final String? conversationId;
  final String? heritagePubIdContext;
  final Failure? failure;
  final bool isSending;

  ChatState copyWith({
    List<ChatMessage>? messages,
    String? conversationId,
    String? heritagePubIdContext,
    Failure? failure,
    bool clearFailure = false,
    bool? isSending,
  }) =>
      ChatState(
        messages: messages ?? this.messages,
        conversationId: conversationId ?? this.conversationId,
        heritagePubIdContext: heritagePubIdContext ?? this.heritagePubIdContext,
        failure: clearFailure ? null : failure ?? this.failure,
        isSending: isSending ?? this.isSending,
      );
}

class ChatController extends Notifier<ChatState> {
  static const Uuid _uuid = Uuid();

  @override
  ChatState build() => const ChatState(messages: <ChatMessage>[]);

  void setHeritageContext(String? pubId) {
    state = state.copyWith(heritagePubIdContext: pubId);
  }

  Future<void> send(String prompt) async {
    final trimmed = prompt.trim();
    if (trimmed.isEmpty || state.isSending) return;

    final language = ref.read(activeLocaleProvider).languageCode;
    final now = DateTime.now().toUtc();
    final userMsg = ChatMessage(
      id: _uuid.v4(),
      role: ChatRole.user,
      content: trimmed,
      createdAt: now,
      heritagePubIdContext: state.heritagePubIdContext,
    );
    final pendingAssistant = ChatMessage(
      id: _uuid.v4(),
      role: ChatRole.assistant,
      content: "",
      createdAt: now.add(const Duration(milliseconds: 1)),
      pending: true,
    );
    state = state.copyWith(
      messages: <ChatMessage>[...state.messages, userMsg, pendingAssistant],
      isSending: true,
      clearFailure: true,
    );

    final repo = ref.read(chatRepositoryProvider);
    final result = await repo.send(
      prompt: trimmed,
      conversationId: state.conversationId,
      language: language,
      heritagePubIdContext: state.heritagePubIdContext,
    );

    result.fold<void>(
      onSuccess: (ChatMessage assistant) {
        final replaced = <ChatMessage>[
          for (final ChatMessage m in state.messages)
            if (m.id == pendingAssistant.id) assistant else m,
        ];
        state = state.copyWith(
          messages: replaced,
          isSending: false,
        );
      },
      onFailure: (Failure f) {
        final cleaned = state.messages
            .where((ChatMessage m) => m.id != pendingAssistant.id)
            .toList(growable: false);
        state = state.copyWith(
          messages: cleaned,
          isSending: false,
          failure: f,
        );
      },
    );
  }

  Future<({String mediaAssetId, String signedUrl})?> requestTts(
    ChatMessage message,
  ) async {
    if (message.role != ChatRole.assistant || message.content.isEmpty) {
      return null;
    }
    final language = ref.read(activeLocaleProvider).languageCode;
    final repo = ref.read(chatRepositoryProvider);
    final result = await repo.tts(text: message.content, language: language);
    return result.successOrNull;
  }

  @visibleForTesting
  void seed(List<ChatMessage> seed) {
    state = state.copyWith(messages: seed);
  }
}

final NotifierProvider<ChatController, ChatState> chatControllerProvider =
    NotifierProvider<ChatController, ChatState>(
  ChatController.new,
  name: "chatControllerProvider",
);
