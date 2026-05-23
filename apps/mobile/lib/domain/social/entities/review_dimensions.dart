class ReviewDimensions {
  const ReviewDimensions(
      {this.history = 0,
      this.photos = 0,
      this.access = 0,
      this.value = 0,
      this.atmosphere = 0,
      this.familyFriendly = 0,});
  final double history;
  final double photos;
  final double access;
  final double value;
  final double atmosphere;
  final double familyFriendly;
  double get average =>
      [history, photos, access, value, atmosphere, familyFriendly]
          .fold<double>(0, (a, b) => a + b) /
      6;
}
