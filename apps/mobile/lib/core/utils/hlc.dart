// Hybrid Logical Clock for offline-first writes.
//
// Master Architecture §8 mandates HLC for ordering client edits across
// disconnected devices. The server validates and overrides if drift is
// larger than N minutes. Keep this lib pure-Dart — no Flutter imports.

import "dart:math";

class HybridLogicalClock {
  HybridLogicalClock({
    int? physical,
    this.counter = 0,
    String? nodeId,
  })  : physical = physical ?? DateTime.now().toUtc().millisecondsSinceEpoch,
        nodeId = nodeId ?? _generateNodeId();

  factory HybridLogicalClock.parse(String packed) {
    final parts = packed.split(":");
    if (parts.length != 3) {
      throw const FormatException("HLC must be physical:counter:nodeId");
    }
    return HybridLogicalClock(
      physical: int.parse(parts[0]),
      counter: int.parse(parts[1]),
      nodeId: parts[2],
    );
  }

  final int physical;
  final int counter;
  final String nodeId;

  HybridLogicalClock tick() {
    final now = DateTime.now().toUtc().millisecondsSinceEpoch;
    if (now > physical) {
      return HybridLogicalClock(physical: now, nodeId: nodeId);
    }
    return HybridLogicalClock(
      physical: physical,
      counter: counter + 1,
      nodeId: nodeId,
    );
  }

  HybridLogicalClock receive(HybridLogicalClock remote) {
    final now = DateTime.now().toUtc().millisecondsSinceEpoch;
    final maxPhysical = [now, physical, remote.physical].reduce(max);
    int newCounter;
    if (maxPhysical == physical && maxPhysical == remote.physical) {
      newCounter = max(counter, remote.counter) + 1;
    } else if (maxPhysical == physical) {
      newCounter = counter + 1;
    } else if (maxPhysical == remote.physical) {
      newCounter = remote.counter + 1;
    } else {
      newCounter = 0;
    }
    return HybridLogicalClock(
      physical: maxPhysical,
      counter: newCounter,
      nodeId: nodeId,
    );
  }

  String pack() => "$physical:$counter:$nodeId";

  static String _generateNodeId() {
    final rng = Random.secure();
    final bytes = List<int>.generate(6, (_) => rng.nextInt(256));
    return bytes
        .map((int b) => b.toRadixString(16).padLeft(2, "0"))
        .join();
  }

  @override
  String toString() => pack();
}
