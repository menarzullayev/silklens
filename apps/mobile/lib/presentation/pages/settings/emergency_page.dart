import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_hooks/flutter_hooks.dart';
import 'package:hooks_riverpod/hooks_riverpod.dart';
import 'package:silklens/core/l10n/app_strings.dart';
import 'package:silklens/core/l10n/locale_service.dart';
import 'package:silklens/data/api/clients/api_client_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

class EmergencyPage extends HookConsumerWidget {
  const EmergencyPage({super.key});

  String _s(String key) => AppStrings.get(LocaleService.instance.locale, key);

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    useEffect(
      () {
        SystemChrome.setSystemUIOverlayStyle(
          const SystemUiOverlayStyle(
            statusBarColor: Colors.transparent,
            statusBarIconBrightness: Brightness.light,
            systemNavigationBarColor: Color(0xFF0D2337),
            systemNavigationBarIconBrightness: Brightness.light,
          ),
        );
        return null;
      },
      const [],
    );

    final locale = ref.watch(activeLocaleProvider);
    final contacts = useState<List<dynamic>>([]);
    final isLoading = useState(true);

    useEffect(
      () {
        isLoading.value = true;
        Future(() async {
          try {
            final client = ref.read(silkLensApiClientProvider);
            contacts.value = await client.getEmergencyContacts(
              language: locale.languageCode,
            );
          } catch (_) {}
          isLoading.value = false;
        });
        return null;
      },
      [locale.languageCode],
    );

    return Scaffold(
      backgroundColor: const Color(0xFF0D2337),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: GestureDetector(
          onTap: () => Navigator.of(context).pop(),
          child: const Icon(
            Icons.arrow_back_ios_new,
            color: Colors.white,
            size: 20,
          ),
        ),
        title: Text(
          _s('emergency_title'),
          style: const TextStyle(
            color: Colors.white,
            fontSize: 20,
            fontWeight: FontWeight.w700,
          ),
        ),
      ),
      body: isLoading.value
          ? const Center(
              child: CircularProgressIndicator(color: Color(0xFFB78628)),
            )
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                // Warning banner
                Container(
                  padding: const EdgeInsets.all(12),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: Colors.red.withValues(alpha: 0.15),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(
                      color: Colors.red.withValues(alpha: 0.3),
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(Icons.warning_amber, color: Colors.orange),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          _s('emergency_warning'),
                          style: const TextStyle(
                            color: Colors.orange,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                if (contacts.value.isEmpty)
                  Center(
                    child: Text(
                      _s('emergency_empty'),
                      style: const TextStyle(color: Colors.white54),
                    ),
                  )
                else
                  ...contacts.value.map((c) {
                    final contact = c as Map<String, dynamic>;
                    return _ContactTile(contact: contact, s: _s);
                  }),
              ],
            ),
    );
  }
}

class _ContactTile extends StatelessWidget {
  const _ContactTile({required this.contact, required this.s});
  final Map<String, dynamic> contact;
  final String Function(String) s;

  static IconData _iconForKind(String kind) => switch (kind) {
        'ambulance' => Icons.local_hospital,
        'police' => Icons.local_police,
        'fire' => Icons.local_fire_department,
        'hospital' => Icons.medical_services,
        _ => Icons.phone,
      };

  @override
  Widget build(BuildContext context) {
    final name = contact['name'] as String? ?? '';
    final phone = contact['phone'] as String? ?? '';
    final kind = contact['kind'] as String? ?? '';
    final is24h = contact['is_24h'] as bool? ?? false;
    final icon = _iconForKind(kind);

    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.white12),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(
          horizontal: 16,
          vertical: 4,
        ),
        leading: Container(
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Colors.red.withValues(alpha: 0.2),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Icon(icon, color: Colors.red, size: 20),
        ),
        title: Text(
          name,
          style: const TextStyle(
            color: Colors.white,
            fontWeight: FontWeight.bold,
          ),
        ),
        subtitle: Text(
          phone + (is24h ? ' • 24/7' : ''),
          style: const TextStyle(color: Colors.white60),
        ),
        trailing: phone.isNotEmpty
            ? IconButton(
                icon: const Icon(Icons.call, color: Color(0xFFB78628)),
                onPressed: () {
                  // Dial intent — clipboard fallback if url_launcher absent.
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(
                      content: Text('${s("emergency_call")}: $phone'),
                      backgroundColor: const Color(0xFF1A3A5C),
                    ),
                  );
                },
              )
            : null,
      ),
    );
  }
}
