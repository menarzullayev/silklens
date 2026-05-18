// Widget happy-paths for the auth screens. Each test pumps the page
// inside a minimal localized scaffold and asserts critical keys / strings.

import "package:flutter/material.dart";
import "package:flutter_localizations/flutter_localizations.dart";
import "package:flutter_test/flutter_test.dart";
import "package:hooks_riverpod/hooks_riverpod.dart";
import "package:mocktail/mocktail.dart";
import "package:silklens/core/utils/result.dart";
import "package:silklens/data/repositories/auth_repository_impl.dart"
    show authRepositoryProvider;
import "package:silklens/domain/branding/entities/branding.dart";
import "package:silklens/domain/identity/entities/auth_session.dart";
import "package:silklens/domain/identity/entities/auth_user.dart";
import "package:silklens/domain/identity/repositories/auth_repository.dart";
import "package:silklens/l10n/app_localizations.dart";
import "package:silklens/presentation/pages/auth/forgot_password_page.dart";
import "package:silklens/presentation/pages/auth/onboarding_page.dart";
import "package:silklens/presentation/pages/auth/sign_in_page.dart";
import "package:silklens/presentation/pages/auth/sign_up_page.dart";
import "package:silklens/presentation/providers/auth_provider.dart";
import "package:silklens/presentation/providers/branding_provider.dart";
import "package:silklens/presentation/widgets/heritage_card.dart";
import "package:silklens/domain/heritage/entities/heritage.dart";

class _MockAuthRepository extends Mock implements AuthRepository {}

Future<void> _pumpPage(
  WidgetTester tester,
  Widget child, {
  List<Override> overrides = const <Override>[],
}) async {
  await tester.pumpWidget(
    ProviderScope(
      overrides: overrides,
      child: MaterialApp(
        locale: const Locale("en"),
        supportedLocales: AppLocalizations.supportedLocales,
        localizationsDelegates: const <LocalizationsDelegate<Object?>>[
          AppLocalizations.delegate,
          GlobalMaterialLocalizations.delegate,
          GlobalCupertinoLocalizations.delegate,
          GlobalWidgetsLocalizations.delegate,
        ],
        home: child,
      ),
    ),
  );
  await tester.pump();
}

void main() {
  setUpAll(() {
    registerFallbackValue(
      AuthSession(
        user: const AuthUser(id: "x", pubId: "x", tenantId: "x"),
        accessToken: "x",
        refreshToken: "x",
        expiresAt: DateTime.utc(2099),
      ),
    );
  });

  testWidgets("SignInPage renders email + password + submit + providers",
      (WidgetTester tester) async {
    await _pumpPage(tester, const SignInPage());

    expect(find.byKey(const Key("auth.email_field")), findsOneWidget);
    expect(find.byKey(const Key("auth.password_field")), findsOneWidget);
    expect(find.byKey(const Key("sign_in.submit")), findsOneWidget);
    expect(find.byKey(const Key("sign_in.forgot_link")), findsOneWidget);
    expect(find.byKey(const Key("auth.provider_google")), findsOneWidget);
  });

  testWidgets("SignInPage shows validation error on empty submit",
      (WidgetTester tester) async {
    await _pumpPage(tester, const SignInPage());

    await tester.tap(find.byKey(const Key("sign_in.submit")));
    await tester.pump();

    // Required-field error is in the Form's validator output.
    expect(find.text("This field is required."), findsAtLeastNWidgets(1));
  });

  testWidgets("SignUpPage renders all four fields + submit",
      (WidgetTester tester) async {
    await _pumpPage(tester, const SignUpPage());

    expect(find.byKey(const Key("sign_up.display_name")), findsOneWidget);
    expect(find.byKey(const Key("auth.email_field")), findsOneWidget);
    expect(find.byKey(const Key("auth.password_field")), findsOneWidget);
    expect(find.byKey(const Key("sign_up.password_confirm")), findsOneWidget);
    expect(find.byKey(const Key("sign_up.submit")), findsOneWidget);
  });

  testWidgets("ForgotPasswordPage renders body + submit",
      (WidgetTester tester) async {
    await _pumpPage(tester, const ForgotPasswordPage());

    expect(find.byKey(const Key("forgot_password.submit")), findsOneWidget);
    expect(
      find.text(
        "Password recovery is coming soon — we will email you instructions.",
      ),
      findsOneWidget,
    );
  });

  testWidgets("OnboardingPage renders three slides + page-view + dots",
      (WidgetTester tester) async {
    await _pumpPage(tester, const OnboardingPage());

    expect(find.byKey(const Key("onboarding.page_view")), findsOneWidget);
    expect(find.byKey(const Key("onboarding.dot.0")), findsOneWidget);
    expect(find.byKey(const Key("onboarding.dot.1")), findsOneWidget);
    expect(find.byKey(const Key("onboarding.dot.2")), findsOneWidget);
    expect(find.byKey(const Key("onboarding.cta_primary")), findsOneWidget);
    expect(find.byKey(const Key("onboarding.cta_skip")), findsOneWidget);
  });

  testWidgets("SignInPage submit calls repo.signIn",
      (WidgetTester tester) async {
    final repo = _MockAuthRepository();
    when(() => repo.currentSession()).thenAnswer((_) async => null);
    when(
      () => repo.signIn(
        email: any(named: "email"),
        password: any(named: "password"),
      ),
    ).thenAnswer(
      (_) async => Success<AuthSession>(
        AuthSession(
          user: const AuthUser(id: "u", pubId: "u", tenantId: "t"),
          accessToken: "a",
          refreshToken: "r",
          expiresAt: DateTime.utc(2099),
        ),
      ),
    );

    await _pumpPage(
      tester,
      const SignInPage(),
      overrides: <Override>[
        authRepositoryProvider.overrideWithValue(repo),
      ],
    );
    await tester.enterText(
      find.byKey(const Key("auth.email_field")),
      "alice@example.com",
    );
    await tester.enterText(
      find.byKey(const Key("auth.password_field")),
      "SomePassword1",
    );
    await tester.tap(find.byKey(const Key("sign_in.submit")));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 50));

    verify(
      () => repo.signIn(
        email: "alice@example.com",
        password: "SomePassword1",
      ),
    ).called(1);
  });

  testWidgets("HeritageCard surfaces the localized name and period chip",
      (WidgetTester tester) async {
    const heritage = Heritage(
      id: "1",
      pubId: "registan",
      kindSlug: "monument",
      name: <String, String>{"en": "Registan Square"},
      periodStartYear: 1417,
      periodEndYear: 1420,
      countryCode: "UZ",
    );
    await _pumpPage(
      tester,
      Scaffold(body: HeritageCard(heritage: heritage, onTap: () {})),
    );

    expect(find.byKey(const Key("heritage_card.registan")), findsOneWidget);
    expect(find.text("Registan Square"), findsOneWidget);
    expect(find.textContaining("1417"), findsOneWidget);
    expect(find.text("UZ"), findsOneWidget);
  });

  testWidgets(
      "BrandingDefaults yield the SilkLens app name on the splash fallback",
      (WidgetTester tester) async {
    // Watch the synchronous selector — should fall back to defaults until
    // first fetch resolves.
    await _pumpPage(
      tester,
      Consumer(
        builder: (BuildContext context, WidgetRef ref, Widget? _) {
          final branding = ref.watch(brandingValueProvider);
          return Scaffold(
            body: Text(branding.localizedAppName("en")),
          );
        },
      ),
    );

    expect(find.text("SilkLens"), findsOneWidget);
  });
}
