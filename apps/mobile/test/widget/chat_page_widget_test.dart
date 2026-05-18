import "package:flutter/material.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/chat_repository_impl.dart";
import "package:silklens/domain/ai/entities/chat_message.dart";
import "package:silklens/domain/ai/repositories/chat_repository.dart";
import "package:silklens/presentation/pages/chat/chat_page.dart";

import "test_helpers.dart";

class _Repo extends Mock implements ChatRepository {}

void main() {
  testWidgets("ChatPage shows empty state with prompt chips",
      (WidgetTester tester) async {
    final repo = _Repo();
    await tester.pumpWidget(
      wrapForWidgetTest(
        const ChatPage(),
        overrides: <Override>[
          chatRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );

    expect(find.byKey(const Key("chat.empty")), findsOneWidget);
    expect(find.byType(ActionChip), findsWidgets);
  });

  testWidgets("Typing into input + tapping send dispatches to repo",
      (WidgetTester tester) async {
    final repo = _Repo();
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
          content: "Hi there!",
          createdAt: DateTime.utc(2026),
        ),
      ),
    );

    await tester.pumpWidget(
      wrapForWidgetTest(
        const ChatPage(),
        overrides: <Override>[
          chatRepositoryProvider.overrideWithValue(repo),
        ],
      ),
    );
    await tester.enterText(find.byKey(const Key("chat.input")), "hello");
    await tester.tap(find.byKey(const Key("chat.send")));
    await tester.pumpAndSettle();

    expect(find.text("Hi there!"), findsOneWidget);
  });
}
