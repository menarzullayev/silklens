class ChatMessage {
  const ChatMessage(
      {required this.id, required this.role, required this.content, required this.createdAt,});
  final String id;
  final String role; // 'user' | 'assistant'
  final String content;
  final DateTime createdAt;
  bool get isUser => role == 'user';
}
