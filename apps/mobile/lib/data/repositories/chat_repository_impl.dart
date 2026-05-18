// HTTP-backed implementation of [ChatRepository].

import "package:dio/dio.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/api/dio_client.dart";
import "package:silklens/domain/ai/entities/chat_message.dart";
import "package:silklens/domain/ai/repositories/chat_repository.dart";

class ChatRepositoryImpl implements ChatRepository {
  ChatRepositoryImpl({required Dio dio}) : _dio = dio;

  final Dio _dio;

  @override
  Future<Result<ChatMessage>> send({
    required String prompt,
    String? conversationId,
    required String language,
    String? heritagePubIdContext,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/v1/ai/chat",
        data: <String, dynamic>{
          "prompt": prompt,
          if (conversationId != null) "conversation_id": conversationId,
          "language": language,
          if (heritagePubIdContext != null)
            "heritage_pub_id": heritagePubIdContext,
        },
      );
      final body = response.data ?? const <String, dynamic>{};
      final id = body["message_id"] as String? ?? body["id"] as String? ?? "";
      final content = body["content"] as String? ?? "";
      final createdAtStr = body["created_at"] as String?;
      final createdAt = createdAtStr != null
          ? DateTime.tryParse(createdAtStr) ?? DateTime.now().toUtc()
          : DateTime.now().toUtc();
      return Success<ChatMessage>(
        ChatMessage(
          id: id.isEmpty ? "srv-${createdAt.millisecondsSinceEpoch}" : id,
          role: ChatRole.assistant,
          content: content,
          createdAt: createdAt,
          heritagePubIdContext: heritagePubIdContext,
        ),
      );
    } on DioException catch (e, st) {
      return FailureResult<ChatMessage>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }

  @override
  Future<Result<({String mediaAssetId, String signedUrl})>> tts({
    required String text,
    required String language,
  }) async {
    try {
      final response = await _dio.post<Map<String, dynamic>>(
        "/v1/ai/tts",
        data: <String, dynamic>{
          "text": text,
          "language": language,
        },
      );
      final body = response.data ?? const <String, dynamic>{};
      final assetId = body["media_asset_id"] as String? ?? "";
      final url = body["signed_url"] as String? ?? "";
      if (assetId.isEmpty || url.isEmpty) {
        return const FailureResult<({String mediaAssetId, String signedUrl})>(
          ServerFailure("TTS response missing media_asset_id or signed_url"),
        );
      }
      return Success<({String mediaAssetId, String signedUrl})>(
        (mediaAssetId: assetId, signedUrl: url),
      );
    } on DioException catch (e, st) {
      return FailureResult<({String mediaAssetId, String signedUrl})>(
        NetworkFailure(e.message ?? "Dio error", cause: e, stackTrace: st),
      );
    }
  }
}

final Provider<ChatRepository> chatRepositoryProvider =
    Provider<ChatRepository>(
  (Ref ref) => ChatRepositoryImpl(dio: ref.watch(dioProvider)),
  name: "chatRepositoryProvider",
);
