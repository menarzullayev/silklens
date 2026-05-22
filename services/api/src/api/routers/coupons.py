"""Coupon and promo code validation. SILK-0089."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.middleware.auth import CurrentUserDep
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["billing"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


class CouponValidateRequest(BaseModel):
    code: str = Field(..., min_length=3, max_length=50)
    order_value_usd: float = Field(..., gt=0)


@router.post(
    "/v1/billing/coupons/validate",
    dependencies=[Depends(rate_limit("10/minute", per="user", scope="billing:coupon_validate"))],
)
async def validate_coupon(
    body: CouponValidateRequest,
    ctx: CurrentUserDep,
    session: SessionDep,
) -> dict:
    """Validate a coupon code and return the discount amount.

    Checks:
    - coupon exists, is active, and has not expired
    - usage cap not exhausted
    - minimum order value satisfied
    - caller has not already redeemed this coupon
    """
    row = await session.execute(
        text("""
            SELECT id, code, kind, discount_value, min_order_usd,
                   max_uses, uses_count, valid_until, applicable_plans, description
            FROM coupons
            WHERE code = :code
              AND is_active = true
              AND (valid_until IS NULL OR valid_until > now())
        """),
        {"code": body.code.upper().strip()},
    )
    coupon = row.mappings().fetchone()

    if not coupon:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "billing.coupon_not_found",
                "message": "Coupon not found or expired",
            },
        )

    if coupon["max_uses"] and coupon["uses_count"] >= coupon["max_uses"]:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={
                "code": "billing.coupon_exhausted",
                "message": "Coupon usage limit reached",
            },
        )

    min_order = float(coupon["min_order_usd"] or 0)
    if body.order_value_usd < min_order:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "billing.coupon_min_order",
                "message": f"Minimum order ${min_order:.2f} required",
            },
        )

    already = await session.execute(
        text("""
            SELECT id FROM coupon_redemptions
            WHERE coupon_id = :cid AND user_id = :uid
        """),
        {"cid": str(coupon["id"]), "uid": str(ctx.user_id)},
    )
    if already.fetchone():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "billing.coupon_already_used",
                "message": "Coupon already redeemed by this account",
            },
        )

    if coupon["kind"] == "percent":
        discount = round(body.order_value_usd * float(coupon["discount_value"]) / 100, 2)
    else:
        discount = min(float(coupon["discount_value"]), body.order_value_usd)

    return {
        "valid": True,
        "code": coupon["code"],
        "kind": coupon["kind"],
        "discount_usd": discount,
        "final_price_usd": round(body.order_value_usd - discount, 2),
        "description": coupon["description"],
    }
