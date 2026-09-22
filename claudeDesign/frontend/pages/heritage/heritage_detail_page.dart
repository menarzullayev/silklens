import 'package:flutter/material.dart';

class HeritageDetailPage extends StatelessWidget {
  const HeritageDetailPage({required this.pubId, super.key});
  final String pubId;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(pubId)),
      body: ListView(
        children: [
          Container(
            height: 200,
            color: Colors.blue.shade100,
            child: const Center(
              child: Icon(Icons.account_balance, size: 80, color: Colors.blue),
            ),
          ),
          const Padding(
            padding: EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Heritage Site', style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
                SizedBox(height: 8),
                Text('Detailed information loading from API...', style: TextStyle(color: Colors.grey)),
                SizedBox(height: 16),
                Row(
                  children: [
                    Icon(Icons.location_on, size: 16, color: Colors.blue),
                    SizedBox(width: 4),
                    Text('Uzbekistan'),
                    SizedBox(width: 16),
                    Icon(Icons.history, size: 16, color: Colors.blue),
                    SizedBox(width: 4),
                    Text('15th century'),
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
