import 'package:flutter/material.dart';
class SavedHeritagePage extends StatelessWidget {
  const SavedHeritagePage({super.key});
  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Saved')),
    body: const Center(child: Text('No saved items yet')),
  );
}
