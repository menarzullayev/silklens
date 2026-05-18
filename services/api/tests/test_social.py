"""Social-graph integration tests.

Covers follow/unfollow round-trip, self-follow rejection, feed visibility for
followees, blocking visibility, follower/following listings.
"""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"social-{uuid.uuid4().hex[:10]}@silklens-test.com"


def _password() -> str:
    return "SocialDemoPassword12345"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _unique_email(), "password": _password()},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _headers(auth: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth['tokens']['access_token']}"}


@pytest.mark.asyncio
async def test_follow_round_trip(http: AsyncClient) -> None:
    a = await _register(http)
    b = await _register(http)

    create = await http.post(f"/v1/social/follow/{b['user']['pub_id']}", headers=_headers(a))
    assert create.status_code == 201, create.text
    assert create.json()["target_pub_id"] == b["user"]["pub_id"]

    delete = await http.delete(f"/v1/social/follow/{b['user']['pub_id']}", headers=_headers(a))
    assert delete.status_code == 200


@pytest.mark.asyncio
async def test_cannot_follow_self(http: AsyncClient) -> None:
    a = await _register(http)
    response = await http.post(f"/v1/social/follow/{a['user']['pub_id']}", headers=_headers(a))
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "social.cannot_follow_self"


@pytest.mark.asyncio
async def test_follow_unknown_user_returns_404(http: AsyncClient) -> None:
    a = await _register(http)
    response = await http.post("/v1/social/follow/does_not_exist", headers=_headers(a))
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "social.user_not_found"


@pytest.mark.asyncio
async def test_double_follow_is_409(http: AsyncClient) -> None:
    a = await _register(http)
    b = await _register(http)
    first = await http.post(f"/v1/social/follow/{b['user']['pub_id']}", headers=_headers(a))
    assert first.status_code == 201
    second = await http.post(f"/v1/social/follow/{b['user']['pub_id']}", headers=_headers(a))
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_followers_and_following_listings(http: AsyncClient) -> None:
    a = await _register(http)
    b = await _register(http)
    await http.post(f"/v1/social/follow/{b['user']['pub_id']}", headers=_headers(a))

    followers = await http.get(f"/v1/social/followers/{b['user']['pub_id']}")
    assert followers.status_code == 200
    body = followers.json()
    assert body["total"] >= 1
    pub_ids = {item["pub_id"] for item in body["items"]}
    assert a["user"]["pub_id"] in pub_ids

    following = await http.get(f"/v1/social/following/{a['user']['pub_id']}")
    assert following.status_code == 200
    body = following.json()
    pub_ids = {item["pub_id"] for item in body["items"]}
    assert b["user"]["pub_id"] in pub_ids


@pytest.mark.asyncio
async def test_feed_shows_followees_activity(http: AsyncClient) -> None:
    a = await _register(http)
    b = await _register(http)
    c = await _register(http)
    # a follows b, b follows c → b's "followed c" event must appear in a's feed.
    follow_ab = await http.post(f"/v1/social/follow/{b['user']['pub_id']}", headers=_headers(a))
    assert follow_ab.status_code == 201
    follow_bc = await http.post(f"/v1/social/follow/{c['user']['pub_id']}", headers=_headers(b))
    assert follow_bc.status_code == 201

    feed = await http.get("/v1/social/feed?limit=20", headers=_headers(a))
    assert feed.status_code == 200
    items = feed.json()["items"]
    # at least one item is b's followed-c activity
    assert any(item["verb"] == "followed" for item in items)


@pytest.mark.asyncio
async def test_block_cascades_unfollow(http: AsyncClient) -> None:
    a = await _register(http)
    b = await _register(http)
    await http.post(f"/v1/social/follow/{b['user']['pub_id']}", headers=_headers(a))
    await http.post(f"/v1/social/follow/{a['user']['pub_id']}", headers=_headers(b))

    block = await http.post(
        f"/v1/social/block/{b['user']['pub_id']}",
        headers=_headers(a),
        json={"reason": "test"},
    )
    assert block.status_code == 201

    # Both follow rows must be gone
    followers = await http.get(f"/v1/social/followers/{a['user']['pub_id']}")
    pub_ids = {item["pub_id"] for item in followers.json()["items"]}
    assert b["user"]["pub_id"] not in pub_ids


@pytest.mark.asyncio
async def test_blocked_actor_excluded_from_feed(http: AsyncClient) -> None:
    a = await _register(http)
    b = await _register(http)
    c = await _register(http)
    await http.post(f"/v1/social/follow/{b['user']['pub_id']}", headers=_headers(a))
    await http.post(f"/v1/social/follow/{c['user']['pub_id']}", headers=_headers(b))

    # Now a blocks b — feed query must drop b's activity rows.
    await http.post(f"/v1/social/block/{b['user']['pub_id']}", headers=_headers(a))

    feed = await http.get("/v1/social/feed", headers=_headers(a))
    assert feed.status_code == 200
    actor_ids = {item["actor_user_id"] for item in feed.json()["items"]}
    assert b["user"]["id"] not in actor_ids


@pytest.mark.asyncio
async def test_friend_invitation_round_trip(http: AsyncClient) -> None:
    a = await _register(http)
    b = await _register(http)
    invite = await http.post(
        "/v1/social/friends/invite",
        headers=_headers(a),
        json={"target_pub_id": b["user"]["pub_id"]},
    )
    assert invite.status_code == 200, invite.text
    token = invite.json()["token"]
    assert invite.json()["status"] == "pending"
    # SEC-021: the inviter (creation point) receives the raw token.
    assert token != "***"
    assert len(token) >= 16

    accept = await http.post(
        "/v1/social/friends/accept",
        headers=_headers(b),
        json={"token": token},
    )
    assert accept.status_code == 200
    assert accept.json()["status"] == "accepted"
    # SEC-021: the accept response is a "subsequent read" — token must be
    # masked so it doesn't leak via response logs or session replay.
    assert accept.json()["token"] == "***"


@pytest.mark.asyncio
async def test_follow_persists_event_outbox(http: AsyncClient, db_session: AsyncSession) -> None:
    a = await _register(http)
    b = await _register(http)
    response = await http.post(f"/v1/social/follow/{b['user']['pub_id']}", headers=_headers(a))
    assert response.status_code == 201
    event = (
        await db_session.execute(
            text(
                """
                SELECT event_name FROM event_outbox
                WHERE event_name = 'follow.created.v1'
                  AND aggregate_id = :uid
                LIMIT 1
                """
            ),
            {"uid": a["user"]["id"]},
        )
    ).scalar_one_or_none()
    assert event == "follow.created.v1"
