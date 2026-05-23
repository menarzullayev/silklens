import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/presentation/pages/heritage/heritage_list_page.dart';
import 'package:silklens/presentation/providers/heritage_list_provider.dart';
import 'package:silklens/presentation/providers/locale_provider.dart';

import 'test_helpers.dart';

void main() {
  testWidgets('HeritageListPage renders without error when list is empty',
      (tester) async {
    await tester.pumpWidget(
      wrapForWidgetTest(
        const HeritageListPage(),
        overrides: [
          heritageListProvider.overrideWith(_StubHeritageListNotifier.new),
          activeLocaleProvider.overrideWith(_StubLocaleController.new),
        ],
      ),
    );
    await tester.pump();
    expect(tester.takeException(), isNull);
  });
}

class _StubHeritageListNotifier extends HeritageListNotifier {
  @override
  HeritageListState build() => const HeritageListState();
}

class _StubLocaleController extends LocaleController {
  @override
  Locale build() => const Locale('en');
}
