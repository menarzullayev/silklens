// Social feed item — a heterogeneous entry that wraps the underlying actor +
// the action (review / check-in / badge unlock / follow). The presentation
// layer renders different cards per [kind].



enum FeedItemKind {
  review,
  checkIn,
  badgeUnlock,
  follow,
  comment,
}

class FeedItem {
  // STUB: FeedItem factory (codegen pending)
}
