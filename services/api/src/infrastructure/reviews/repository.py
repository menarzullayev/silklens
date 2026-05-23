"""SQL implementation of the review/UGC repository.

Hand-written SQL — see infrastructure/heritage/repository.py for the rationale
(migrations own the canonical schema; we avoid duplicating truth in ORM models).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.reviews.entities import (
    Comment,
    CommentParentKind,
    Reaction,
    ReactionTargetKind,
    ReportReason,
    ReportTargetKind,
    Review,
    ReviewDraft,
    ReviewPage,
    ReviewRating,
    ReviewSort,
    UgcStatus,
    UgcSubmission,
)
from src.domain.reviews.errors import (
    CommentDepthExceeded,
    CommentParentNotFound,
    DuplicateReview,
    InvalidRating,
)
from src.infrastructure._events import emit_event_if_registered, jdump

_REVIEW_COLS = """
    id, tenant_id, heritage_id, user_id, residency_region,
    language_tag, title, body_md, average_rating, visited_at,
    is_published, machine_translated_from,
    helpful_count, unhelpful_count, report_count, edited_count,
    quality_score, created_at, updated_at
"""


def _to_review(row: Any) -> Review:
    m = row._mapping
    return Review(
        id=m["id"],
        tenant_id=m["tenant_id"],
        heritage_id=m["heritage_id"],
        user_id=m["user_id"],
        residency_region=m["residency_region"],
        language_tag=m["language_tag"],
        body_md=m["body_md"],
        is_published=m["is_published"],
        helpful_count=m["helpful_count"],
        unhelpful_count=m["unhelpful_count"],
        report_count=m["report_count"],
        edited_count=m["edited_count"],
        title=m["title"],
        average_rating=m["average_rating"],
        visited_at=m["visited_at"],
        quality_score=m["quality_score"],
        machine_translated_from=m["machine_translated_from"],
        created_at=m["created_at"],
        updated_at=m["updated_at"],
    )


class SqlReviewRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- heritage lookup -------------------------------------------------

    async def heritage_pub_id_to_id(self, pub_id: str) -> UUID | None:
        row = await self._session.execute(
            text(
                """
                SELECT id FROM heritage_objects
                WHERE pub_id = :p AND deleted_at IS NULL
                LIMIT 1
                """
            ),
            {"p": pub_id},
        )
        return row.scalar_one_or_none()

    async def get_by_id(self, review_id: UUID) -> Review | None:
        row = await self._session.execute(
            text(f"SELECT {_REVIEW_COLS} FROM reviews WHERE id = :id LIMIT 1"),  # noqa: S608
            {"id": review_id},
        )
        r = row.one_or_none()
        if r is None:
            return None
        return _to_review(r)

    async def list_for_heritage(
        self,
        *,
        heritage_id: UUID,
        sort: ReviewSort,
        limit: int,
        offset: int,
    ) -> ReviewPage:
        order_by = {
            ReviewSort.HELPFUL: "helpful_count DESC, created_at DESC",
            ReviewSort.RECENT: "created_at DESC",
            ReviewSort.RATING: "average_rating DESC NULLS LAST, created_at DESC",
        }[sort]
        total = (
            await self._session.execute(
                text(
                    """
                    SELECT count(*) FROM reviews
                    WHERE heritage_id = :h AND is_published AND deleted_at IS NULL
                    """
                ),
                {"h": heritage_id},
            )
        ).scalar_one()
        result = await self._session.execute(
            text(
                f"""
                SELECT {_REVIEW_COLS}
                FROM reviews
                WHERE heritage_id = :h
                  AND is_published
                  AND deleted_at IS NULL
                ORDER BY {order_by}
                LIMIT :limit OFFSET :offset
                """  # noqa: S608 -- order_by is from a closed enum
            ),
            {"h": heritage_id, "limit": limit, "offset": offset},
        )
        items = tuple(_to_review(r) for r in result.all())
        return ReviewPage(items=items, total=int(total), limit=limit, offset=offset)

    # --- create review ---------------------------------------------------

    async def create_review(self, *, draft: ReviewDraft, auto_publish: bool) -> Review:
        # First make sure the dimension slugs exist + values fit the scale.
        if draft.ratings:
            await self._validate_ratings(draft.ratings)
        avg = self._compute_average(draft.ratings)

        try:
            row = await self._session.execute(
                text(
                    f"""
                    INSERT INTO reviews (
                        tenant_id, heritage_id, user_id, residency_region,
                        language_tag, title, body_md, visited_at,
                        is_published, average_rating
                    )
                    VALUES (
                        :tenant, :hid, :uid, :res,
                        :lang, :title, :body, :visited,
                        :pub, :avg
                    )
                    RETURNING {_REVIEW_COLS}
                    """  # noqa: S608
                ),
                {
                    "tenant": draft.tenant_id,
                    "hid": draft.heritage_id,
                    "uid": draft.user_id,
                    "res": draft.residency_region,
                    "lang": draft.language_tag,
                    "title": draft.title,
                    "body": draft.body_md,
                    "visited": draft.visited_at,
                    "pub": auto_publish,
                    "avg": avg,
                },
            )
        except IntegrityError as exc:
            await self._session.rollback()
            raise DuplicateReview() from exc

        review = _to_review(row.one())

        # Insert per-dimension ratings.
        for rating in draft.ratings:
            await self._session.execute(
                text(
                    """
                    INSERT INTO review_ratings (review_id, dimension_slug, value)
                    VALUES (:r, :d, :v)
                    """
                ),
                {"r": review.id, "d": rating.dimension_slug, "v": rating.value},
            )

        # Emit registered event.
        await emit_event_if_registered(
            self._session,
            tenant_id=draft.tenant_id,
            event_name="review.created.v1",
            aggregate_type="review",
            aggregate_id=review.id,
            payload={
                "heritage_id": str(draft.heritage_id),
                "user_id": str(draft.user_id),
                "language_tag": draft.language_tag,
                "auto_publish": auto_publish,
            },
        )
        return review

    async def _validate_ratings(self, ratings: tuple[ReviewRating, ...]) -> None:
        slugs = list({r.dimension_slug for r in ratings})
        rows = (
            await self._session.execute(
                text(
                    """
                    SELECT slug, scale_min, scale_max
                    FROM review_dimensions
                    WHERE slug = ANY(:slugs) AND is_active
                    """
                ),
                {"slugs": slugs},
            )
        ).all()
        known = {r._mapping["slug"]: r._mapping for r in rows}
        for rating in ratings:
            if rating.dimension_slug not in known:
                raise InvalidRating(f"unknown rating dimension '{rating.dimension_slug}'")
            mn = known[rating.dimension_slug]["scale_min"]
            mx = known[rating.dimension_slug]["scale_max"]
            if not (mn <= rating.value <= mx):
                raise InvalidRating(
                    f"value {rating.value} for '{rating.dimension_slug}' is outside [{mn}, {mx}]"
                )

    @staticmethod
    def _compute_average(ratings: tuple[ReviewRating, ...]) -> float | None:
        if not ratings:
            return None
        total = sum(r.value for r in ratings)
        return round(total / len(ratings), 2)

    # --- helpful votes ---------------------------------------------------

    async def upsert_helpful_vote(
        self, *, review_id: UUID, voter_id: UUID, voter_residency: str, vote: int
    ) -> Review:
        await self._session.execute(
            text(
                """
                INSERT INTO review_helpful_votes (
                    review_id, voter_user_id, voter_residency, vote
                )
                VALUES (:r, :v, :vres, :vote)
                ON CONFLICT (review_id, voter_user_id) DO UPDATE
                    SET vote = EXCLUDED.vote, voted_at = now()
                """
            ),
            {"r": review_id, "v": voter_id, "vres": voter_residency, "vote": vote},
        )
        # Recompute counters from votes table (cheap on a single review).
        await self._session.execute(
            text(
                """
                UPDATE reviews r
                SET helpful_count =
                        (SELECT count(*) FROM review_helpful_votes
                         WHERE review_id = r.id AND vote = 1),
                    unhelpful_count =
                        (SELECT count(*) FROM review_helpful_votes
                         WHERE review_id = r.id AND vote = -1)
                WHERE id = :r
                """
            ),
            {"r": review_id},
        )
        row = await self._session.execute(
            text(f"SELECT {_REVIEW_COLS} FROM reviews WHERE id = :id"),  # noqa: S608
            {"id": review_id},
        )
        return _to_review(row.one())

    # --- reactions -------------------------------------------------------

    async def reaction_type_exists(self, slug: str) -> bool:
        row = await self._session.execute(
            text("SELECT 1 FROM reaction_types WHERE slug = :s AND is_active LIMIT 1"),
            {"s": slug},
        )
        return row.one_or_none() is not None

    async def add_reaction(
        self,
        *,
        reactor_id: UUID,
        reactor_residency: str,
        target_kind: ReactionTargetKind,
        target_id: UUID,
        reaction_slug: str,
    ) -> Reaction:
        row = await self._session.execute(
            text(
                """
                INSERT INTO reactions (
                    reactor_user_id, reactor_residency,
                    target_kind, target_id, reaction_type_slug
                )
                VALUES (:rid, :rres, :tk, :tid, :slug)
                ON CONFLICT (reactor_user_id, target_kind, target_id, reaction_type_slug)
                    DO UPDATE SET created_at = reactions.created_at
                RETURNING id, reactor_user_id, target_kind, target_id,
                          reaction_type_slug, created_at
                """
            ),
            {
                "rid": reactor_id,
                "rres": reactor_residency,
                "tk": target_kind.value,
                "tid": target_id,
                "slug": reaction_slug,
            },
        )
        m = row.one()._mapping
        return Reaction(
            id=m["id"],
            reactor_user_id=m["reactor_user_id"],
            target_kind=ReactionTargetKind(m["target_kind"]),
            target_id=m["target_id"],
            reaction_type_slug=m["reaction_type_slug"],
            created_at=m["created_at"],
        )

    async def remove_reaction(
        self,
        *,
        reactor_id: UUID,
        target_kind: ReactionTargetKind,
        target_id: UUID,
        reaction_slug: str,
    ) -> bool:
        row = await self._session.execute(
            text(
                """
                DELETE FROM reactions
                WHERE reactor_user_id = :rid
                  AND target_kind = :tk
                  AND target_id = :tid
                  AND reaction_type_slug = :slug
                RETURNING id
                """
            ),
            {
                "rid": reactor_id,
                "tk": target_kind.value,
                "tid": target_id,
                "slug": reaction_slug,
            },
        )
        return row.one_or_none() is not None

    # --- comments --------------------------------------------------------

    async def add_comment(
        self,
        *,
        tenant_id: UUID,
        author_id: UUID,
        author_residency: str,
        parent_kind: CommentParentKind,
        parent_id: UUID,
        body_md: str,
        language_tag: str,
    ) -> Comment:
        # Compute depth + ltree path from the parent.
        parent_depth = 0
        parent_path: str | None = None
        if parent_kind == CommentParentKind.COMMENT:
            row = await self._session.execute(
                text(
                    """
                    SELECT depth, path::text AS path
                    FROM comments
                    WHERE id = :id AND deleted_at IS NULL
                    """
                ),
                {"id": parent_id},
            )
            parent_row = row.one_or_none()
            if parent_row is None:
                raise CommentParentNotFound()
            parent_depth = int(parent_row._mapping["depth"])
            parent_path = parent_row._mapping["path"]
            if parent_depth >= 6:
                raise CommentDepthExceeded()
        new_depth = parent_depth + 1 if parent_kind == CommentParentKind.COMMENT else 0

        # First insert with a temporary placeholder path; then update with the
        # actual ltree path using the freshly-allocated id.
        insert_row = await self._session.execute(
            text(
                """
                INSERT INTO comments (
                    tenant_id, parent_kind, parent_id,
                    author_user_id, author_residency,
                    body_md, language_tag, depth, path
                )
                VALUES (
                    :tenant, :pkind, :pid, :auth, :ares,
                    :body, :lang, :depth, text2ltree('placeholder')
                )
                RETURNING id, created_at
                """
            ),
            {
                "tenant": tenant_id,
                "pkind": parent_kind.value,
                "pid": parent_id,
                "auth": author_id,
                "ares": author_residency,
                "body": body_md,
                "lang": language_tag,
                "depth": new_depth,
            },
        )
        new_id = insert_row.one()._mapping["id"]

        # Build the actual ltree path. ltree labels are restricted to
        # ``[A-Za-z0-9_]``; UUIDs need their dashes stripped. We hex-encode
        # the parent_id + new id for stable, dedup-friendly labels.
        new_label = str(new_id).replace("-", "")
        if parent_kind == CommentParentKind.COMMENT and parent_path:
            new_path_text = f"{parent_path}.{new_label}"
        else:
            new_path_text = f"{str(parent_id).replace('-', '')}.{new_label}"
        await self._session.execute(
            text("UPDATE comments SET path = text2ltree(:p) WHERE id = :id"),
            {"p": new_path_text, "id": new_id},
        )

        # If we threaded under another comment, bump its reply_count.
        if parent_kind == CommentParentKind.COMMENT:
            await self._session.execute(
                text("UPDATE comments SET reply_count = reply_count + 1 WHERE id = :id"),
                {"id": parent_id},
            )

        row = await self._session.execute(
            text(
                """
                SELECT id, tenant_id, parent_kind, parent_id,
                       author_user_id, author_residency, body_md, language_tag,
                       depth, path::text AS path, status, reply_count, reaction_count,
                       created_at, updated_at
                FROM comments WHERE id = :id
                """
            ),
            {"id": new_id},
        )
        m = row.one()._mapping
        return Comment(
            id=m["id"],
            tenant_id=m["tenant_id"],
            parent_kind=CommentParentKind(m["parent_kind"]),
            parent_id=m["parent_id"],
            author_user_id=m["author_user_id"],
            author_residency=m["author_residency"],
            body_md=m["body_md"],
            language_tag=m["language_tag"],
            depth=m["depth"],
            path=m["path"],
            status=m["status"],
            reply_count=m["reply_count"],
            reaction_count=m["reaction_count"],
            created_at=m["created_at"],
            updated_at=m["updated_at"],
        )

    # --- UGC submissions -------------------------------------------------

    async def submit_ugc(
        self,
        *,
        tenant_id: UUID,
        kind: str,
        target_id: UUID,
        author_id: UUID,
        author_residency: str,
        payload: dict[str, Any],
        status: UgcStatus,
        trust_tier: str,
    ) -> UgcSubmission:
        row = await self._session.execute(
            text(
                """
                INSERT INTO ugc_submissions (
                    tenant_id, kind, target_id,
                    author_user_id, author_residency,
                    payload, status, user_trust_tier_snapshot
                )
                VALUES (
                    :tenant, :kind, :tid, :uid, :ures,
                    CAST(:payload AS jsonb), :status, :tier
                )
                RETURNING id, tenant_id, kind, target_id,
                          author_user_id, author_residency,
                          payload, status, user_trust_tier_snapshot,
                          auto_moderation_score, ai_decision, submitted_at
                """
            ),
            {
                "tenant": tenant_id,
                "kind": kind,
                "tid": target_id,
                "uid": author_id,
                "ures": author_residency,
                "payload": jdump(payload),
                "status": status.value,
                "tier": trust_tier,
            },
        )
        m = row.one()._mapping
        return UgcSubmission(
            id=m["id"],
            tenant_id=m["tenant_id"],
            kind=m["kind"],
            target_id=m["target_id"],
            author_user_id=m["author_user_id"],
            author_residency=m["author_residency"],
            status=UgcStatus(m["status"]),
            payload=dict(m["payload"]) if m["payload"] else {},
            submitted_at=m["submitted_at"],
            user_trust_tier_snapshot=m["user_trust_tier_snapshot"],
            auto_moderation_score=m["auto_moderation_score"],
            ai_decision=m["ai_decision"],
        )

    # --- reports ---------------------------------------------------------

    async def create_report(
        self,
        *,
        reporter_id: UUID,
        reporter_residency: str,
        target_kind: ReportTargetKind,
        target_id: UUID,
        reason: ReportReason,
        details: str | None,
    ) -> UUID:
        row = await self._session.execute(
            text(
                """
                INSERT INTO reports (
                    reporter_user_id, reporter_residency,
                    target_kind, target_id, reason_slug, details
                )
                VALUES (:rid, :rres, :tk, :tid, :reason, :details)
                ON CONFLICT (reporter_user_id, target_kind, target_id, reason_slug)
                    DO UPDATE SET details = COALESCE(EXCLUDED.details, reports.details)
                RETURNING id
                """
            ),
            {
                "rid": reporter_id,
                "rres": reporter_residency,
                "tk": target_kind.value,
                "tid": target_id,
                "reason": reason.value,
                "details": details,
            },
        )
        return row.scalar_one()
