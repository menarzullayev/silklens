import 'package:flutter/material.dart';

class ProfilePage extends StatefulWidget {
  const ProfilePage({super.key});

  @override
  State<ProfilePage> createState() => _ProfilePageState();
}

class _ProfilePageState extends State<ProfilePage>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  static const _tabs = [
    Tab(text: 'Activity'),
    Tab(text: 'Saved'),
    Tab(text: 'Reviews'),
    Tab(text: 'Friends'),
    Tab(text: 'Settings'),
  ];

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: _tabs.length, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Profile'),
        bottom: TabBar(
          controller: _tabController,
          tabs: _tabs,
          isScrollable: true,
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          const Center(child: Text('Activity')),
          const Center(child: Text('Saved')),
          const Center(child: Text('Reviews')),
          const Center(child: Text('Friends')),
          ListView(
            key: const Key('profile.settings.list'),
            children: const [
              ListTile(
                leading: Icon(Icons.language),
                title: Text('Language'),
              ),
              ListTile(
                leading: Icon(Icons.notifications),
                title: Text('Notifications'),
              ),
              ListTile(
                leading: Icon(Icons.privacy_tip),
                title: Text('Privacy'),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
