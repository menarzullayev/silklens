"""Review / reaction / comment / report integration tests."""

from __future__ import annotations

import uuid
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.integration


def _email() -> str:
    return f"reviews-{uuid.uuid4().hex[:10]}@silklens-test.com"


def _password() -> str:
    return "ReviewsDemoPass12345"


async def _register(http: AsyncClient) -> dict[str, Any]:
    response = await http.post(
        "/v1/auth/register",
        json={"email": _email(), "password": _password()},
    )
    assert response.status_code == 201, response.text
    return response.json()


def _h(auth: dict[str, Any]) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth['tokens']['access_token']}"}


async def _grant_super_admin(db_session: AsyncSession, pub_id: str) -> None:
    await db_session.execute(
        text(
            """
            INSERT INTO user_roles (
                user_id, residency_region, role_id, scope_tenant_id, granted_by
            )
            SELECT u.id, u.residency_region, r.id, NULL,
                   '00000000-0000-0000-0000-000000000002'::uuid
            FROM users u, roles r
            WHERE u.pub_id = :pub_id AND r.slug = 'super_admin'
            """
        ),
        {"pub_id": pub_id},
    )
    await db_session.commit()


async def _make_heritage(http: AsyncClient, db_session: AsyncSession) -> tuple[str, dict[str, Any]]:
    """Create a heritage object and return (heritage_pub_id, auth_payload)."""
    admin_auth = await _register(http)
    await _grant_super_admin(db_session, admin_auth["user"]["pub_id"])
    response = await http.post(
        "/v1/heritage",
        json={"kind_slug": "madrasa", "name": {"en": "Test Madrasa"}},
        headers=_h(admin_auth),
    )
    assert response.status_code == 201, response.text
    return response.json()["pub_id"], admin_auth


@pytest.mark.asyncio
async def test_create_review_and_list(http: AsyncClient, db_session: AsyncSession) -> None:
    pub_id, admin_auth = await _make_heritage(http, db_session)

    create = await http.post(
        f"/v1/heritage/{pub_id}/reviews",
        headers=_h(admin_auth),
        json={
            "body_md": "Beautiful place, lots of history here.",
            "language_tag": "en",
            "ratings": [
                {"dimension_slug": "history_accuracy", "value": 4},
                {"dimension_slug": "atmosphere", "value": 5},
            ],
        },
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["body_md"].startswith("Beautiful")
    # Newly-registered users have trust_tier='new' so reviews require human
    # moderation before becoming visible to public listings.
    assert body["is_published"] is False

    # Without admin auto-publish, listing should not include the unpublished row.
    listing = await http.get(f"/v1/heritage/{pub_id}/reviews")
    assert listing.status_code == 200
    page = listing.json()
    assert page["total"] == 0

    # But a UGC submission row must have been created for moderation.
    submission = (
        await db_session.execute(
            text(
                """
                SELECT status FROM ugc_submissions
                WHERE target_id = :rid AND kind = 'review'
                """
            ),
            {"rid": body["id"]},
        )
    ).scalar_one()
    assert submission == "pending"


@pytest.mark.asyncio
async def test_cannot_create_two_reviews_same_heritage(
    http: AsyncClient, db_session: AsyncSession
) -> None:
    pub_id, admin_auth = await _make_heritage(http, db_session)
    payload = {
        "body_md": "First review — lots of text.",
        "language_tag": "en",
    }
    first = await http.post(f"/v1/heritage/{pub_id}/reviews", headers=_h(admin_auth), json=payload)
    assert first.status_code == 201
    second = await http.post(
        f"/v1/heritage/{pub_id}/reviews",
        headers=_h(admin_auth),
        json={**payload, "body_md": "Second review attempt should fail."},
    )
    assert second.status_code == 409
    assert second.json()["detail"]["code"] == "review.duplicate"


@pytest.mark.asyncio
async def test_review_for_unknown_heritage_returns_404(http: AsyncClient) -> None:
    auth = await _register(http)
    response = await http.post(
        "/v1/heritage/does-not-exist/reviews",
        headers=_h(auth),
        json={"body_md": "content content content content"},
    )
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "review.heritage_not_found"


@pytest.mark.asyncio
async def test_review_invalid_rating_dimension(http: AsyncClient, db_session: AsyncSession) -> None:
    pub_id, admin_auth = await _make_heritage(http, db_session)
    response = await http.post(
        f"/v1/heritage/{pub_id}/reviews",
        headers=_h(admin_auth),
        json={
            "body_md": "Content content content content content",
            "ratings": [{"dimension_slug": "not_a_dim", "value": 3}],
        },
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "review.invalid_rating"


@pytest.mark.asyncio
async def test_vote_helpful(http: AsyncClient, db_session: AsyncSession) -> None:
    pub_id, admin_auth = await _make_heritage(http, db_session)
    create = await http.post(
        f"/v1/heritage/{pub_id}/reviews",
        headers=_h(admin_auth),
        json={"body_md": "Worth a visit, very informative tour."},
    )
    review_id = create.json()["id"]

    voter = await _register(http)
    vote = await http.patch(
        f"/v1/reviews/{review_id}/helpful",
        headers=_h(voter),
        json={"vote": 1},
    )
    assert vote.status_code == 200, vote.text
    assert vote.json()["helpful_count"] == 1


@pytest.mark.asyncio
async def test_add_reaction(http: AsyncClient, db_session: AsyncSession) -> None:
    pub_id, admin_auth = await _make_heritage(http, db_session)
    create = await http.post(
        f"/v1/heritage/{pub_id}/reviews",
        headers=_h(admin_auth),
        json={"body_md": "Reaction-eligible review body here."},
    )
    review_id = create.json()["id"]
    reactor = await _register(http)

    add = await http.post(
        f"/v1/reviews/{review_id}/reactions",
        headers=_h(reactor),
        json={"reaction_slug": "love"},
    )
    assert add.status_code == 201
    assert add.json()["reaction_type_slug"] == "love"

    # Unknown reaction is rejected.
    bad = await http.post(
        f"/v1/reviews/{review_id}/reactions",
        headers=_h(reactor),
        json={"reaction_slug": "not_a_thing"},
    )
    assert bad.status_code == 422


@pytest.mark.asyncio
async def test_add_comment_threaded(http: AsyncClient, db_session: AsyncSession) -> None:
    pub_id, admin_auth = await _make_heritage(http, db_session)
    create = await http.post(
        f"/v1/heritage/{pub_id}/reviews",
        headers=_h(admin_auth),
        json={"body_md": "Open for community discussion right here."},
    )
    review_id = create.json()["id"]
    commenter = await _register(http)

    top = await http.post(
        "/v1/comments",
        headers=_h(commenter),
        json={
            "parent_kind": "review",
            "parent_id": review_id,
            "body_md": "Great review!",
            "language_tag": "en",
        },
    )
    assert top.status_code == 201, top.text
    parent_id = top.json()["id"]

    # Nested reply
    reply = await http.post(
        "/v1/comments",
        headers=_h(commenter),
        json={
            "parent_kind": "comment",
            "parent_id": parent_id,
            "body_md": "Thanks, that's kind of you.",
            "language_tag": "en",
        },
    )
    assert reply.status_code == 201, reply.text
    # Top-level comments are depth 0; this reply (child of a comment) is 1.
    assert top.json()["depth"] == 0
    assert reply.json()["depth"] == 1


@pytest.mark.asyncio
async def test_report_creates_row(http: AsyncClient, db_session: AsyncSession) -> None:
    pub_id, admin_auth = await _make_heritage(http, db_session)
    create = await http.post(
        f"/v1/heritage/{pub_id}/reviews",
        headers=_h(admin_auth),
        json={"body_md": "Some content content content content content."},
    )
    review_id = create.json()["id"]

    reporter = await _register(http)
    report = await http.post(
        "/v1/reports",
        headers=_h(reporter),
        json={
            "target_kind": "review",
            "target_id": review_id,
            "reason_slug": "spam",
            "details": "looks like spam to me",
        },
    )
    assert report.status_code == 201
    row = (
        await db_session.execute(
            text("SELECT status FROM reports WHERE id = :rid"),
            {"rid": report.json()["report_id"]},
        )
    ).scalar_one()
    assert row == "open"


@pytest.mark.asyncio
async def test_review_create_requires_auth(http: AsyncClient) -> None:
    response = await http.post(
        "/v1/heritage/anything/reviews",
        json={"body_md": "content content content content"},
    )
    assert response.status_code == 401
