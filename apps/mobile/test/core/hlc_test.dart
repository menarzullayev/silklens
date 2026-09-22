import 'package:flutter_test/flutter_test.dart';
import 'package:silklens/core/utils/hlc.dart';

void main() {
  group('HybridLogicalClock', () {
    test('tick monotonically advances', () {
      final a = HybridLogicalClock(physical: 1000);
      final b = a.tick();
      expect(b.physical >= a.physical, isTrue);
    });

    test('receive merges remote correctly', () {
      final local =
          HybridLogicalClock(physical: 1000, counter: 1, nodeId: 'aaaa');
      final remote =
          HybridLogicalClock(physical: 2000, counter: 3, nodeId: 'bbbb');
      final merged = local.receive(remote);
      expect(merged.physical >= 2000, isTrue);
    });

    test('pack/parse round-trip preserves fields', () {
      final hlc =
          HybridLogicalClock(physical: 123, counter: 4, nodeId: 'deadbeef');
      final parsed = HybridLogicalClock.parse(hlc.pack());
      expect(parsed.physical, equals(hlc.physical));
      expect(parsed.counter, equals(hlc.counter));
      expect(parsed.nodeId, equals(hlc.nodeId));
    });
  });
}
