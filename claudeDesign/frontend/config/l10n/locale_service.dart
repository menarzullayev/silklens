import 'package:shared_preferences/shared_preferences.dart';

class LocaleService {
  LocaleService._();

  static final LocaleService instance = LocaleService._();

  String locale = 'en';

  Future<void> loadFromPrefs() async {
    final prefs = await SharedPreferences.getInstance();
    locale = prefs.getString('app_locale') ?? 'en';
  }
}
