"""Smart ticketing + QR access system. SILK-0065.

GET  /v1/ticket-types              — list ticket types for a heritage site (public)
POST /v1/tickets/purchase          — purchase a ticket, returns QR payload (auth required)
GET  /v1/tickets/me                — list authenticated user's tickets
GET  /v1/tickets/{ticket_id}/qr   — get QR payload for a specific ticket (ownership verified)
POST /v1/tickets/{ticket_id}/scan  — operator: mark ticket as used (auth required)
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_session
from src.core.settings import get_settings
from src.middleware.auth import CurrentUserDep
from src.middleware.ratelimit import rate_limit

router = APIRouter(tags=["tickets"])

SessionDep = Annotated[AsyncSession, Depends(get_session)]


# --- DTOs ---


class TicketPurchase(BaseModel):
    ticket_type_id: UUID
    visit_date: str | None = Field(
        None,
        description="ISO date YYYY-MM-DD. Leave null for open-dated tickets.",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    )


class TicketTypeOut(BaseModel):
    id: UUID
    kind: str
    price_usd: float
    valid_days: int
    max_per_booking: int
    available_from: str | None
    available_until: str | None
    name: str
    description_md: str | None


class TicketOut(BaseModel):
    id: str
    status: str
    visit_date: str | None
    price_paid_usd: float | None
    created_at: str
    ticket_kind: str
    ticket_name: str | None
    heritage_pub_id: str


class PurchaseResponse(BaseModel):
    id: str
    status: str
    visit_date: str | None
    created_at: str
    ticket_type_id: str
    heritage_pub_id: str
    price_usd: float
    qr_payload: str
    qr_instructions: str


class QrResponse(BaseModel):
    ticket_id: str
    status: str
    qr_payload: str
    visit_date: str | None


class ScanResponse(BaseModel):
    ticket_id: str
    status: str
    scanned_at: str


# --- Helpers ---


def _generate_qr_secret() -> str:
    """Generate a cryptographically random 64-character QR secret."""
    return secrets.token_urlsafe(48)[:64]


def _build_qr_payload(ticket_id: str, visit_date: str | None, qr_secret: str) -> str:
    """Build the QR code payload — HMAC-SHA256 signed to prevent forgery.

    Signs with the audit HMAC key (already stored in prod KMS) so no new
    secret material is needed. The payload is compact enough to render as a
    dense QR code at moderate error-correction level.
    """
    settings = get_settings()
    hmac_key = settings.audit_hmac_key.get_secret_value().encode()
    message = f"{ticket_id}:{visit_date or 'any'}:{qr_secret}"
    sig = hmac.new(hmac_key, message.encode(), hashlib.sha256).hexdigest()[:16]
    return f"SL:{ticket_id[:8]}:{sig}"


# --- Routes ---


@router.get(
    "/v1/ticket-types",
    response_model=list[TicketTypeOut],
    summary="List ticket types for a heritage site",
)
async def list_ticket_types(
    session: SessionDep,
    heritage_pub_id: UUID = Query(..., description="Heritage site public UUID"),  # noqa: B008
    language: str = Query("en", min_length=2, max_length=10),
) -> list[TicketTypeOut]:
    """Return active ticket types for the given heritage site. No authentication required.

    The ``language`` query parameter selects the display language for ``name``
    and ``description_md``; falls back to English when the requested locale is
    not present in the JSONB column.
    """
    lang = language.split("-")[0].lower()

    rows = await session.execute(
        text("""
            SELECT
                tt.id,
                tt.kind,
                tt.price_usd,
                tt.valid_days,
                tt.max_per_booking,
                CAST(tt.available_from  AS text) AS available_from,
                CAST(tt.available_until AS text) AS available_until,
                COALESCE(tt.name ->> :lang, tt.name ->> 'en', '')           AS name,
                COALESCE(tt.description_md ->> :lang, tt.description_md ->> 'en') AS description_md
            FROM ticket_types tt
            WHERE tt.heritage_pub_id = :pub_id
              AND tt.is_active = true
            ORDER BY tt.sort_order, tt.price_usd
        """),
        {"pub_id": str(heritage_pub_id), "lang": lang},
    )
    return [
        TicketTypeOut(
            id=r["id"],
            kind=r["kind"],
            price_usd=float(r["price_usd"]),
            valid_days=r["valid_days"],
            max_per_booking=r["max_per_booking"],
            available_from=r["available_from"],
            available_until=r["available_until"],
            name=r["name"] or "",
            description_md=r["description_md"],
        )
        for r in rows.mappings().fetchall()
    ]


@router.post(
    "/v1/tickets/purchase",
    response_model=PurchaseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Purchase a ticket",
    dependencies=[
        Depends(rate_limit("10/minute", per="user", scope="tickets:purchase")),
    ],
)
async def purchase_ticket(
    body: TicketPurchase,
    ctx: CurrentUserDep,
    session: SessionDep,
) -> PurchaseResponse:
    """Purchase a ticket and receive the QR code payload.

    The returned ``qr_payload`` is an HMAC-signed string that the mobile app
    renders as a QR code for contactless entry scanning.  The secret is stored
    server-side and never re-issued; call ``GET /v1/tickets/{id}/qr`` to
    regenerate the payload at any time while the ticket is still valid.

    No payment gateway integration in this version — billing is handled
    separately via the ``/v1/billing`` endpoints.
    """
    # Verify ticket type exists and is active
    tt_row = await session.execute(
        text("""
            SELECT id, price_usd, heritage_pub_id
            FROM ticket_types
            WHERE id = :ttid AND is_active = true
        """),
        {"ttid": str(body.ticket_type_id)},
    )
    tt = tt_row.mappings().fetchone()
    if tt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "tickets.type_not_found",
                "message": "Ticket type not found or inactive",
            },
        )

    qr_secret = _generate_qr_secret()

    ticket_row = await session.execute(
        text("""
            INSERT INTO tickets
                (user_id, residency_region, ticket_type_id, qr_secret,
                 visit_date, price_paid_usd)
            VALUES (:uid, :region, :ttid, :qr_secret, :visit_date, :price)
            RETURNING id, status, visit_date, created_at
        """),
        {
            "uid": str(ctx.user_id),
            "region": ctx.residency_region.value,
            "ttid": str(body.ticket_type_id),
            "qr_secret": qr_secret,
            "visit_date": body.visit_date,
            "price": tt["price_usd"],
        },
    )
    await session.commit()
    _ticket_row = ticket_row.mappings().fetchone()
    assert _ticket_row is not None  # INSERT … RETURNING always yields one row
    ticket = dict(_ticket_row)

    qr_payload = _build_qr_payload(str(ticket["id"]), body.visit_date, qr_secret)

    return PurchaseResponse(
        id=str(ticket["id"]),
        status=ticket["status"],
        visit_date=str(ticket["visit_date"]) if ticket["visit_date"] else None,
        created_at=str(ticket["created_at"]),
        ticket_type_id=str(body.ticket_type_id),
        heritage_pub_id=str(tt["heritage_pub_id"]),
        price_usd=float(tt["price_usd"]),
        qr_payload=qr_payload,
        qr_instructions="Show this QR code at the entrance for contactless entry.",
    )


@router.get(
    "/v1/tickets/me",
    response_model=dict,
    summary="List authenticated user's tickets",
)
async def my_tickets(
    ctx: CurrentUserDep,
    session: SessionDep,
    limit: int = Query(20, ge=1, le=50),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Return a paginated list of tickets belonging to the authenticated user.

    Tickets are ordered newest-first.  The QR payload is NOT included here to
    keep the list response compact; call ``GET /v1/tickets/{id}/qr`` for the
    QR payload of a specific ticket.
    """
    rows = await session.execute(
        text("""
            SELECT
                t.id,
                t.status,
                t.visit_date,
                t.price_paid_usd,
                t.created_at,
                tt.kind                                  AS ticket_kind,
                COALESCE(tt.name ->> 'en', '')           AS ticket_name,
                tt.heritage_pub_id
            FROM tickets t
            JOIN ticket_types tt ON tt.id = t.ticket_type_id
            WHERE t.user_id = :uid
            ORDER BY t.created_at DESC
            LIMIT :limit OFFSET :offset
        """),
        {"uid": str(ctx.user_id), "limit": limit, "offset": offset},
    )
    items = [
        {
            **{k: (str(v) if v is not None else None) for k, v in dict(r).items()},
        }
        for r in rows.mappings().fetchall()
    ]
    return {"items": items, "limit": limit, "offset": offset}


@router.get(
    "/v1/tickets/{ticket_id}/qr",
    response_model=QrResponse,
    summary="Get QR payload for a ticket (ownership verified)",
)
async def get_ticket_qr(
    ticket_id: UUID,
    ctx: CurrentUserDep,
    session: SessionDep,
) -> QrResponse:
    """Return the HMAC-signed QR payload for the specified ticket.

    The endpoint verifies that the authenticated user owns the ticket before
    returning the payload.  Returns 410 Gone for already-used or expired
    tickets so the mobile app can surface a clear error rather than showing a
    QR code that will never scan successfully.
    """
    row = await session.execute(
        text("""
            SELECT t.id, t.status, t.qr_secret, t.visit_date, t.scanned_at
            FROM tickets t
            WHERE t.id = :tid AND t.user_id = :uid
        """),
        {"tid": str(ticket_id), "uid": str(ctx.user_id)},
    )
    ticket = row.mappings().fetchone()
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "tickets.not_found", "message": "Ticket not found"},
        )

    if ticket["status"] == "used":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "tickets.already_used", "message": "This ticket has already been used"},
        )

    if ticket["status"] == "expired":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "tickets.expired", "message": "This ticket has expired"},
        )

    visit_date_str = str(ticket["visit_date"]) if ticket["visit_date"] else None
    qr_payload = _build_qr_payload(str(ticket["id"]), visit_date_str, ticket["qr_secret"])

    return QrResponse(
        ticket_id=str(ticket_id),
        status=ticket["status"],
        qr_payload=qr_payload,
        visit_date=visit_date_str,
    )


@router.post(
    "/v1/tickets/{ticket_id}/scan",
    response_model=ScanResponse,
    summary="Operator: mark a ticket as used",
    dependencies=[
        Depends(rate_limit("60/minute", per="user", scope="tickets:scan")),
    ],
)
async def scan_ticket(
    ticket_id: UUID,
    ctx: CurrentUserDep,
    session: SessionDep,
) -> ScanResponse:
    """Mark a ticket as used (scanned at entrance).

    Intended for staff / operator devices.  The caller must be authenticated;
    full RBAC enforcement (``heritage:moderate`` permission) is enforced at the
    network/API-gateway level for operator terminals.

    Uses ``FOR UPDATE SKIP LOCKED`` so concurrent scan attempts on the same
    ticket fail gracefully rather than producing a double-entry race.
    """
    row = await session.execute(
        text("""
            SELECT t.id, t.status
            FROM tickets t
            WHERE t.id = :tid
            FOR UPDATE SKIP LOCKED
        """),
        {"tid": str(ticket_id)},
    )
    ticket = row.mappings().fetchone()
    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "tickets.not_found", "message": "Ticket not found"},
        )

    if ticket["status"] != "valid":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "tickets.not_scannable",
                "message": f"Ticket status is '{ticket['status']}' — cannot scan",
            },
        )

    scanned_row = await session.execute(
        text("""
            UPDATE tickets
            SET status = 'used',
                scanned_at = now(),
                scanned_by_user_id = :scanner
            WHERE id = :tid
            RETURNING scanned_at
        """),
        {"tid": str(ticket_id), "scanner": str(ctx.user_id)},
    )
    await session.commit()
    _scan_row = scanned_row.mappings().fetchone()
    assert _scan_row is not None  # UPDATE … RETURNING always yields one row
    scanned_at = str(_scan_row["scanned_at"])

    return ScanResponse(ticket_id=str(ticket_id), status="used", scanned_at=scanned_at)
