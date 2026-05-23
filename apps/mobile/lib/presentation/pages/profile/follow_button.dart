import 'package:flutter/material.dart';

class FollowButton extends StatelessWidget {
  const FollowButton({required this.pubId, super.key, this.isFollowing = false});
  final String pubId;
  final bool isFollowing;
  @override
  Widget build(BuildContext context) =>
      ElevatedButton(onPressed: () {}, child: Text(isFollowing ? 'Unfollow' : 'Follow'));
}
