// Unit tests for [ChatController].

import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/error/failures.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/chat_repository_impl.dart";
import "package:silklens/domain/ai/entities/chat_message.dart";
import "package:silklens/domain/ai/repositories/chat_repository.dart";
import "package:silklens/presentation/providers/chat_provider.dart";

class _MockChatRepo extends Mock implements ChatRepository {}

void main() {
  test("send appends user + assistant messages on success", () async {
    final repo = _MockChatRepo();
    when(() => repo.send(
          prompt: any(named: "prompt"),
          conversationId: any(named: "conversationId"),
          language: any(named: "language"),
          heritagePubIdContext: any(named: "heritagePubIdContext"),
        )).thenAnswer(
      (_) async => Success<ChatMessage>(
        ChatMessage(
          id: "srv-1",
          role: ChatRole.assistant,
          content: "Built in 15th century.",
          createdAt: DateTime.utc(2026),
        ),
      ),
    );

    final container = ProviderContainer(
      overrides: <Override>[
        chatRepositoryProvider.overrideWithValue(repo),
      ],
    );
    final notifier = container.read(chatControllerProvider.notifier);
    await notifier.send("When was this built?");

    final state = container.read(chatControllerProvider);
    expect(state.messages, hasLength(2));
    expect(state.messages[0].role, ChatRole.user);
    expect(state.messages[1].role, ChatRole.assistant);
    expect(state.messages[1].content, contains("15th century"));
    expect(state.isSending, isFalse);
  });

  test("send removes optimistic pending bubble on failure", () async {
    final repo = _MockChatRepo();
    when(() => repo.send(
          prompt: any(named: "prompt"),
          conversationId: any(named: "conversationId"),
          language: any(named: "language"),
          heritagePubIdContext: any(named: "heritagePubIdContext"),
        )).thenAnswer((_) async =>
        const FailureResult<ChatMessage>(NetworkFailure("offline")));

    final container = ProviderContainer(
      overrides: <Override>[
        chatRepositoryProvider.overrideWithValue(repo),
      ],
    );
    final notifier = container.read(chatControllerProvider.notifier);
    await notifier.send("hello");

    final state = container.read(chatControllerProvider);
    expect(state.failure, isA<NetworkFailure>());
    expect(state.messages.any((ChatMessage m) => m.pending), isFalse);
    // Only the user message remains.
    expect(state.messages, hasLength(1));
    expect(state.messages.single.role, ChatRole.user);
  });

  test("empty prompt is ignored", () async {
    final repo = _MockChatRepo();
    final container = ProviderContainer(
      overrides: <Override>[chatRepositoryProvider.overrideWithValue(repo)],
    );
    final notifier = container.read(chatControllerProvider.notifier);
    await notifier.send("   ");
    expect(container.read(chatControllerProvider).messages, isEmpty);
    verifyNever(() => repo.send(
          prompt: any(named: "prompt"),
          conversationId: any(named: "conversationId"),
          language: any(named: "language"),
          heritagePubIdContext: any(named: "heritagePubIdContext"),
        ));
  });

  test("heritage context is forwarded into send", () async {
    final repo = _MockChatRepo();
    when(() => repo.send(
          prompt: any(named: "prompt"),
          conversationId: any(named: "conversationId"),
          language: any(named: "language"),
          heritagePubIdContext: any(named: "heritagePubIdContext"),
        )).thenAnswer(
      (_) async => Success<ChatMessage>(
        ChatMessage(
          id: "srv-2",
          role: ChatRole.assistant,
          content: "ok",
          createdAt: DateTime.utc(2026),
        ),
      ),
    );

    final container = ProviderContainer(
      overrides: <Override>[chatRepositoryProvider.overrideWithValue(repo)],
    );
    final notifier = container.read(chatControllerProvider.notifier);
    notifier.setHeritageContext("heritage-xyz");
    await notifier.send("Tell me about this place");

    verify(() => repo.send(
          prompt: "Tell me about this place",
          conversationId: null,
          language: any(named: "language"),
          heritagePubIdContext: "heritage-xyz",
        )).called(1);
  });
}
