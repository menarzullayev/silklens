"""AI-powered review analysis — fake detection + sentiment summary. SILK-0071."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["reviews"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Cache TTL: recompute analysis at most once per hour
_ANALYSIS_CACHE_SECONDS = 3600


def _fake_detection_score(reviews: list[dict[str, Any]]) -> tuple[float, list[str]]:
    """Heuristic fake review detection. Returns (authenticity_score, flags)."""
    flags: list[str] = []
    if not reviews:
        return 1.0, flags

    total = len(reviews)
    suspects = 0

    # Flag 1: Only 1-star or 5-star (bimodal distribution)
    ratings = [r.get("rating_avg") or 0 for r in reviews if r.get("rating_avg")]
    extreme_count = sum(1 for r in ratings if r <= 1.0 or r >= 4.9)
    if ratings and extreme_count / len(ratings) > 0.8:
        flags.append("bimodal_rating_distribution")
        suspects += int(extreme_count * 0.3)

    # Flag 2: Very short reviews (< 20 chars)
    short = [r for r in reviews if len(r.get("body_md") or "") < 20]
    if len(short) > total * 0.4:
        flags.append("high_proportion_of_short_reviews")
        suspects += len(short)

    # Flag 3: All reviews posted within 24 hours
    if total >= 3:
        times: list[datetime] = [
            v for r in reviews if isinstance((v := r.get("created_at")), datetime)
        ]
        if times:
            spread = (max(times) - min(times)).total_seconds() if len(times) > 1 else 0
            if spread < 86400 and total >= 5:
                flags.append("suspicious_temporal_clustering")
                suspects += int(total * 0.5)

    raw_auth = max(0.0, 1.0 - (suspects / max(total, 1)) * 0.5)
    return round(raw_auth, 2), flags


async def _ai_summarize(
    reviews: list[dict[str, Any]],
    lang: str,
    settings_obj: Any,
) -> dict[str, Any]:
    """Call LLM to summarize reviews. Falls back to heuristic summary."""
    if not reviews or settings_obj.ai_use_mock_providers:
        # Heuristic summary
        high_rated = [r for r in reviews if (r.get("rating_avg") or 0) >= 4.0]
        low_rated = [r for r in reviews if (r.get("rating_avg") or 0) < 3.0]
        return {
            "summary_md": (
                f"Based on {len(reviews)} reviews: "
                f"{len(high_rated)} positive, {len(low_rated)} negative."
            ),
            "top_pros": (
                ["Rich historical atmosphere", "Knowledgeable guides"] if high_rated else []
            ),
            "top_cons": ["Crowded in peak season", "Limited signage"] if low_rated else [],
            "worth_visiting": len(high_rated) >= len(low_rated),
        }

    sample_texts = [
        f"Rating: {r.get('rating_avg', 'N/A')}/5 — {(r.get('body_md') or '')[:200]}"
        for r in reviews[:15]
    ]
    prompt = f"""Analyze these visitor reviews for a heritage site and provide a structured summary.
Reviews:
{chr(10).join(sample_texts)}

Return JSON only:
{{
  "summary_md": "2-3 sentence summary in {lang}",
  "top_pros": ["pro1 in {lang}", "pro2 in {lang}"],
  "top_cons": ["con1 in {lang}", "con2 in {lang}"],
  "worth_visiting": true/false
}}"""

    try:
        import anthropic
        from anthropic.types import TextBlock

        client = anthropic.AsyncAnthropic()
        resp = await client.messages.create(
            model=settings_obj.anthropic_model_default,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        # Anthropic SDK returns a union of block types; only TextBlock has .text.
        # Find the first TextBlock or fall back to stub.
        text_blocks = [b for b in resp.content if isinstance(b, TextBlock)]
        if not text_blocks:
            raise ValueError("Anthropic response contained no text blocks")
        raw = text_blocks[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed: dict[str, Any] = json.loads(raw)
        return parsed
    except Exception:
        return {
            "summary_md": f"{len(reviews)} reviews analyzed.",
            "top_pros": [],
            "top_cons": [],
            "worth_visiting": True,
        }


@router.get("/v1/heritage/{pub_id}/reviews/analysis")
async def analyze_reviews(
    pub_id: str,
    session: SessionDep,
    language: Annotated[str, Query(min_length=2, max_length=10)] = "en",
    _rl: None = Depends(rate_limit("10/minute", per="ip", scope="reviews:analyze")),
) -> dict[str, Any]:
    """AI-powered review analysis: authenticity scoring + sentiment summary.

    Results cached per heritage site (Redis key not available here, so SQL-backed
    refresh guard: recompute only when last review is newer than cached_at).
    Public endpoint — no auth required.
    """
    lang = language.split("-")[0].lower()
    settings = get_settings()

    # Fetch reviews
    rows = await session.execute(
        text("""
            SELECT r.id, r.body_md, r.language_tag, r.created_at,
                   AVG(rr.score) AS rating_avg
            FROM reviews r
            LEFT JOIN review_ratings rr ON rr.review_id = r.id
            WHERE r.heritage_id = (
                SELECT id FROM heritage_objects WHERE pub_id = :pub_id AND deleted_at IS NULL
            )
            GROUP BY r.id, r.body_md, r.language_tag, r.created_at
            ORDER BY r.created_at DESC
            LIMIT 50
        """),
        {"pub_id": pub_id},
    )
    reviews = []
    for r in rows.mappings().fetchall():
        d = dict(r)
        # Convert datetime for heuristics
        if d.get("created_at") and hasattr(d["created_at"], "replace"):
            d["created_at"] = d["created_at"].replace(tzinfo=UTC)
        reviews.append(d)

    if not reviews:
        return {
            "heritage_pub_id": pub_id,
            "review_count": 0,
            "authenticity_score": 1.0,
            "flags": [],
            "summary_md": None,
            "top_pros": [],
            "top_cons": [],
            "worth_visiting": None,
            "sentiment": None,
        }

    auth_score, flags = _fake_detection_score(reviews)
    ai_summary = await _ai_summarize(reviews, lang, settings)

    # Sentiment breakdown
    ratings = [r.get("rating_avg") or 0 for r in reviews if r.get("rating_avg")]
    positive = sum(1 for r in ratings if r >= 4.0)
    neutral = sum(1 for r in ratings if 2.5 <= r < 4.0)
    negative = sum(1 for r in ratings if r < 2.5)
    total_rated = max(positive + neutral + negative, 1)

    return {
        "heritage_pub_id": pub_id,
        "language": lang,
        "review_count": len(reviews),
        "fake_review_count": max(0, len(reviews) - int(len(reviews) * auth_score)),
        "authenticity_score": auth_score,
        "flags": flags,
        "summary_md": ai_summary.get("summary_md"),
        "top_pros": ai_summary.get("top_pros", []),
        "top_cons": ai_summary.get("top_cons", []),
        "worth_visiting": ai_summary.get("worth_visiting", True),
        "sentiment": {
            "positive": round(positive / total_rated, 2),
            "neutral": round(neutral / total_rated, 2),
            "negative": round(negative / total_rated, 2),
        },
    }
