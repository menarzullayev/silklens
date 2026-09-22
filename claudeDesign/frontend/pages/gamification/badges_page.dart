import 'package:flutter/material.dart';
class BadgesPage extends StatelessWidget {
  const BadgesPage({super.key});
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Badges')),
      body: const Center(child: Text('Coming soon', style: TextStyle(color: Colors.grey))),
    );
  }
}
