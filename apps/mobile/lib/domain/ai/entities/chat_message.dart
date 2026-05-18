// Chat bubble entity. Telegram-style — author role + body + timestamp +
// optional TTS asset reference. `pending` is used while the round-trip is
// in-flight so the UI can render a typing indicator and disable the input.

import "package:freezed_annotation/freezed_annotation.dart";

part "chat_message.freezed.dart";

enum ChatRole { user, assistant, system }

@freezed
class ChatMessage with _$ChatMessage {
  const factory ChatMessage({
    required String id,
    required ChatRole role,
    required String content,
    required DateTime createdAt,
    @Default(false) bool pending,
    String? ttsMediaAssetId,
    String? ttsSignedUrl,
    String? heritagePubIdContext,
  }) = _ChatMessage;

  const ChatMessage._();

  bool get isUser => role == ChatRole.user;
  bool get isAssistant => role == ChatRole.assistant;
}

@freezed
class ChatConversation with _$ChatConversation {
  const factory ChatConversation({
    required String id,
    @Default(<ChatMessage>[]) List<ChatMessage> messages,
    String? heritagePubIdContext,
    String? language,
  }) = _ChatConversation;
}
