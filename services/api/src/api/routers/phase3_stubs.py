"""Phase 3 stub endpoints — features pending external dependencies.

These endpoints are fully routed, documented, and auth-gated but return a
"coming_soon" payload (HTTP 200) until the required external infrastructure is
available.  Returning 200 (not 501) lets the mobile client detect the feature
gate without treating it as a server error.

Blocked features
----------------
SILK-0082  NFT / Digital Souvenir      — Polygon/Solana wallet + gas treasury
SILK-0083  Historical Figures AR       — 3D character assets (Amir Temur, Ulugbek, Babur, Navoi)
SILK-0084  Wearable Integration        — WearOS/watchOS SDK + BLE beacon hardware
SILK-0087  Video Memory Book           — FFmpeg rendering pipeline + video hosting
SILK-0088  Tax Engine                  — jurisdiction rules data + accountant review
SILK-0090  Local GPU Pipeline          — GPU server SSH access + deployment pipeline
SILK-0091  Revenue Recognition         — accountant review for GDPR/GAAP compliance
SILK-0092  Heritage Extensions         — schema designed, migration pending art direction
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from src.middleware.auth import CurrentUserDep

router = APIRouter(tags=["phase3"])


# --- Shared response schema -------------------------------------------------


class ComingSoonOut(BaseModel):
    status: str = "coming_soon"
    phase: int = 3
    ticket: str
    blocked_by: str
    eta: str | None = None
    note: str | None = None


class HistoricalFiguresOut(BaseModel):
    status: str = "coming_soon"
    phase: int = 3
    ticket: str
    blocked_by: str
    planned_figures: list[str]
    eta: str | None = None


class SouvenirListOut(BaseModel):
    status: str = "coming_soon"
    phase: int = 3
    ticket: str
    blocked_by: str
    items: list[str] = []


# --- SILK-0082: NFT / Digital Souvenir -------------------------------------


@router.post("/v1/souvenirs/mint", response_model=ComingSoonOut)
async def mint_digital_souvenir(ctx: CurrentUserDep) -> ComingSoonOut:
    """SILK-0082: Mint a digital souvenir / NFT for a heritage visit.

    Blocked on Polygon/Solana wallet integration and gas fee treasury setup.
    When unblocked this endpoint will accept a ``heritage_pub_id``, verify a
    completed check-in, and call the on-chain minting contract.
    """
    return ComingSoonOut(
        ticket="SILK-0082",
        blocked_by="blockchain_integration",
        eta="Phase 3 — 6-12 months",
    )


@router.get("/v1/me/souvenirs", response_model=SouvenirListOut)
async def list_souvenirs(ctx: CurrentUserDep) -> SouvenirListOut:
    """SILK-0082: List the authenticated user's digital souvenir collection.

    Blocked on Polygon/Solana wallet integration.
    """
    return SouvenirListOut(
        ticket="SILK-0082",
        blocked_by="blockchain_integration",
    )


# --- SILK-0083: AR Historical Figures --------------------------------------


@router.get("/v1/ar/historical-figures", response_model=HistoricalFiguresOut)
async def list_historical_figures() -> HistoricalFiguresOut:
    """SILK-0083: List AR-compositable historical figures for photo sessions.

    Public — no auth required for the catalogue.  Blocked on 3D character
    asset creation (Amir Temur, Ulugbek, Babur, Navoi) and AR SDK integration.
    """
    return HistoricalFiguresOut(
        ticket="SILK-0083",
        blocked_by="3d_character_assets",
        planned_figures=["amir-temur", "mirzo-ulugbek", "zahiriddin-babur", "alisher-navoi"],
        eta="Phase 3 — requires 3D artist collaboration",
    )


@router.post(
    "/v1/ar/historical-figures/{slug}/photo-session",
    response_model=ComingSoonOut,
)
async def historical_figure_photo(slug: str, ctx: CurrentUserDep) -> ComingSoonOut:
    """SILK-0083: Start an AR photo compositing session with a historical figure.

    ``slug`` identifies the character (e.g. ``amir-temur``).  Blocked on 3D
    character assets and on-device AR compositing SDK.
    """
    return ComingSoonOut(
        ticket="SILK-0083",
        blocked_by="3d_character_assets",
        note=f"Requested figure: {slug}",
    )


# --- SILK-0084: Wearable Integration ---------------------------------------


@router.get("/v1/wearable/current-context", response_model=ComingSoonOut)
async def wearable_context(ctx: CurrentUserDep) -> ComingSoonOut:
    """SILK-0084: Fetch the wearable device's current heritage context.

    Returns proximity to heritage objects using BLE beacons and step/health
    data from WearOS / watchOS.  Blocked on SDK integration and beacon hardware
    procurement.
    """
    return ComingSoonOut(
        ticket="SILK-0084",
        blocked_by="wearable_sdk_and_ble_beacons",
    )


@router.post("/v1/wearable/heartbeat", response_model=ComingSoonOut)
async def wearable_heartbeat(ctx: CurrentUserDep) -> ComingSoonOut:
    """SILK-0084: Ingest step / health data from a paired wearable device.

    Blocked on WearOS / watchOS SDK and BLE beacon hardware.
    """
    return ComingSoonOut(
        ticket="SILK-0084",
        blocked_by="wearable_sdk_and_ble_beacons",
    )


# --- SILK-0087: Video Memory Book ------------------------------------------


@router.post("/v1/me/memory-book/generate-video", response_model=ComingSoonOut)
async def generate_video_memory_book(ctx: CurrentUserDep) -> ComingSoonOut:
    """SILK-0087: Render a video memory book from photos and check-in history.

    Blocked on FFmpeg rendering pipeline and video hosting infrastructure.
    The JSON / PDF memory book is available immediately at
    ``POST /v1/me/memory-book/generate``.
    """
    return ComingSoonOut(
        ticket="SILK-0087",
        blocked_by="ffmpeg_video_rendering_pipeline",
        note="JSON/PDF memory book available at POST /v1/me/memory-book/generate",
    )


# --- SILK-0088: Tax Engine --------------------------------------------------


@router.get("/v1/enterprise/tax-rates", response_model=ComingSoonOut)
async def tax_rates(ctx: CurrentUserDep) -> ComingSoonOut:
    """SILK-0088: Retrieve jurisdiction-specific tax rates for billing.

    Blocked on tax jurisdiction data ingestion and accountant review for
    GDPR / GAAP compliance.
    """
    return ComingSoonOut(
        ticket="SILK-0088",
        blocked_by="tax_jurisdiction_data_and_legal_review",
    )
