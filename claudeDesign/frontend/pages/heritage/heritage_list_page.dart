import 'package:flutter/material.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:go_router/go_router.dart';
import 'package:silklens/presentation/widgets/shimmer_loading.dart';

class HeritageListPage extends HookWidget {
  const HeritageListPage({super.key});

  @override
  Widget build(BuildContext context) {
    // Simulate an async load — replace with real provider state in FAZA 6+.
    final isLoading = useState(true);

    useEffect(
      () {
        Future<void>.delayed(
          const Duration(seconds: 2),
          () => isLoading.value = false,
        ).ignore();
        return null;
      },
      const [],
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('SilkLens'),
        actions: [
          IconButton(
            icon: const Icon(Icons.search),
            onPressed: () {},
          ),
        ],
      ),
      body: isLoading.value
          ? const HeritageListSkeleton()
          : ListView(
              children: [
                _HeritageCard(
                  pubId: 'reg-samar-001',
                  name: 'Registon Square',
                  country: 'UZ',
                  period: '1417',
                  onTap: () => context.go('/home/heritage/reg-samar-001'),
                ),
                _HeritageCard(
                  pubId: 'itchan-khiva',
                  name: 'Itchan Kala',
                  country: 'UZ',
                  period: '1389',
                  onTap: () => context.go('/home/heritage/itchan-khiva'),
                ),
              ],
            ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.go('/camera'),
        child: const Icon(Icons.camera_alt),
      ),
      bottomNavigationBar: NavigationBar(
        destinations: const [
          NavigationDestination(icon: Icon(Icons.explore), label: 'Discover'),
          NavigationDestination(icon: Icon(Icons.map), label: 'Map'),
          NavigationDestination(icon: Icon(Icons.camera), label: 'Camera'),
          NavigationDestination(icon: Icon(Icons.bookmark), label: 'Saved'),
          NavigationDestination(icon: Icon(Icons.person), label: 'Profile'),
        ],
        onDestinationSelected: (i) {
          if (i == 1) context.go('/map');
          if (i == 2) context.go('/camera');
        },
      ),
    );
  }
}

class _HeritageCard extends StatelessWidget {
  const _HeritageCard({
    required this.pubId,
    required this.name,
    required this.country,
    required this.period,
    required this.onTap,
  });
  final String pubId;
  final String name;
  final String country;
  final String period;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: ListTile(
        leading: Container(
          width: 56,
          height: 56,
          decoration: BoxDecoration(
            color: Colors.blue.shade100,
            borderRadius: BorderRadius.circular(8),
          ),
          child: const Icon(Icons.account_balance, color: Colors.blue),
        ),
        title: Text(name, style: const TextStyle(fontWeight: FontWeight.bold)),
        subtitle: Text('$country • $period'),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
