// AI chat + TTS contract. The data layer talks to /v1/ai/chat + /v1/ai/tts.

import 'package:silklens/core/utils/result.dart';
import 'package:silklens/domain/ai/entities/chat_message.dart';

abstract interface class ChatRepository {
  /// Posts a user turn to /v1/ai/chat and returns the assistant turn.
  Future<Result<ChatMessage>> send({
    required String prompt,
    required String language, String? conversationId,
    String? heritagePubIdContext,
  });

  /// Calls /v1/ai/tts; returns (media_asset_id, signed_url).
  Future<Result<({String mediaAssetId, String signedUrl})>> tts({
    required String text,
    required String language,
  });
}
