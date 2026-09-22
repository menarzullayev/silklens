"""Investor data room, fundraising rounds, KPI snapshots.

FAZA 7 — IPO / Series A readiness. Introduces the investor-relations layer:
investor profiles and pipeline tracking, fundraising rounds (SAFE / priced /
grant), commitment ledger, a permissioned document data-room, access-grant
log, and periodic KPI snapshots that feed the public traction dashboard.

Tables introduced:

  investor_profiles        — CRM rows for angels, VCs, family offices, etc.
  fundraising_rounds       — one row per capital raise event.
  investor_commitments     — ledger linking investors → rounds (unique pair).
  data_room_documents      — versioned document catalogue with tiered access.
  data_room_access_grants  — audit log of which investor accessed which doc.
  kpi_snapshots            — monthly operating metrics snapshot (MAU, ARR …).

Seeds:

  • 1 Seed round ($2M target, planning status).
  • 1 pitch-deck teaser document (public_teaser access level).
  • 3 KPI snapshots (2026-03, 2026-04, 2026-05).

Revision ID: 0092_investor_dataroom
Revises: 0089_partnership_sla
Create Date: 2026-05-18
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0092_investor_dataroom"
down_revision = "0089_partnership_sla"
branch_labels = None
depends_on = None

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

DEFAULT_TENANT_ID = "00000000-0000-0000-0000-000000000001"
SYSTEM_ACTOR_ID = "00000000-0000-0000-0000-000000000002"


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # investor_profiles
    # -----------------------------------------------------------------------
    op.create_table(
        "investor_profiles",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_uuid_v7()")),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("firm_name", sa.Text(), nullable=False),
        sa.Column(
            "kind",
            sa.Text(),
            sa.CheckConstraint(
                "kind IN ('angel','vc','family_office','strategic','government_fund','accelerator')",
                name="ck_investor_profiles_kind",
            ),
            nullable=False,
        ),
        sa.Column("region", sa.Text(), nullable=False, server_default="global"),
        sa.Column("thesis_md", sa.Text(), nullable=True),
        sa.Column("min_check_size_usd", sa.Numeric(20, 4), nullable=True),
        sa.Column("max_check_size_usd", sa.Numeric(20, 4), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            sa.CheckConstraint(
                "status IN ('prospect','contacted','nda_signed','due_diligence','term_sheet','closed','passed')",
                name="ck_investor_profiles_status",
            ),
            nullable=False,
            server_default="prospect",
        ),
        sa.Column("contacted_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("nda_signed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_investor_profiles_tenant_id", "investor_profiles", ["tenant_id"])
    op.create_index("ix_investor_profiles_status", "investor_profiles", ["status"])

    # -----------------------------------------------------------------------
    # fundraising_rounds
    # -----------------------------------------------------------------------
    op.create_table(
        "fundraising_rounds",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_uuid_v7()")),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("round_name", sa.Text(), nullable=False),
        sa.Column("target_raise_usd", sa.Numeric(20, 4), nullable=False),
        sa.Column("valuation_cap_usd", sa.Numeric(20, 4), nullable=True),
        sa.Column("discount_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column(
            "round_kind",
            sa.Text(),
            sa.CheckConstraint(
                "round_kind IN ('safe','convertible_note','priced','grant')",
                name="ck_fundraising_rounds_kind",
            ),
            nullable=False,
            server_default="safe",
        ),
        sa.Column(
            "status",
            sa.Text(),
            sa.CheckConstraint(
                "status IN ('planning','open','closing','closed')",
                name="ck_fundraising_rounds_status",
            ),
            nullable=False,
            server_default="planning",
        ),
        sa.Column("opened_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("closed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("raised_usd", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_fundraising_rounds_tenant_id", "fundraising_rounds", ["tenant_id"])

    # -----------------------------------------------------------------------
    # investor_commitments
    # -----------------------------------------------------------------------
    op.create_table(
        "investor_commitments",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_uuid_v7()")),
        sa.Column(
            "investor_id",
            sa.UUID(),
            sa.ForeignKey("investor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "round_id",
            sa.UUID(),
            sa.ForeignKey("fundraising_rounds.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("committed_usd", sa.Numeric(20, 4), nullable=False),
        sa.Column("actual_usd", sa.Numeric(20, 4), nullable=True),
        sa.Column("signed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("wired_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column(
            "status",
            sa.Text(),
            sa.CheckConstraint(
                "status IN ('verbal','signed','wired','returned')",
                name="ck_investor_commitments_status",
            ),
            nullable=False,
            server_default="verbal",
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint("investor_id", "round_id", name="uq_commitment_investor_round"),
    )
    op.create_index("ix_investor_commitments_round_id", "investor_commitments", ["round_id"])

    # -----------------------------------------------------------------------
    # data_room_documents
    # -----------------------------------------------------------------------
    op.create_table(
        "data_room_documents",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_uuid_v7()")),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("description_md", sa.Text(), nullable=True),
        sa.Column(
            "category",
            sa.Text(),
            sa.CheckConstraint(
                "category IN ('financials','legal','product','team','market','technical','ip','compliance')",
                name="ck_data_room_documents_category",
            ),
            nullable=False,
        ),
        sa.Column("version", sa.Text(), nullable=False, server_default="1.0"),
        sa.Column(
            "doc_url",
            sa.Text(),
            sa.CheckConstraint("doc_url LIKE 'https://%'", name="ck_data_room_documents_url_https"),
            nullable=False,
        ),
        sa.Column(
            "access_level",
            sa.Text(),
            sa.CheckConstraint(
                "access_level IN ('public_teaser','nda_required','dd_only','investor_only')",
                name="ck_data_room_documents_access_level",
            ),
            nullable=False,
            server_default="nda_required",
        ),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "uploaded_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_data_room_documents_tenant_access",
        "data_room_documents",
        ["tenant_id", "access_level", "is_current"],
    )

    # -----------------------------------------------------------------------
    # data_room_access_grants
    # -----------------------------------------------------------------------
    op.create_table(
        "data_room_access_grants",
        sa.Column(
            "investor_id",
            sa.UUID(),
            sa.ForeignKey("investor_profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.UUID(),
            sa.ForeignKey("data_room_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("granted_by", sa.UUID(), nullable=False),
        sa.Column(
            "granted_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("accessed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("investor_id", "document_id", name="pk_data_room_access_grants"),
    )
    op.create_index(
        "ix_data_room_access_grants_document_id",
        "data_room_access_grants",
        ["document_id"],
    )

    # -----------------------------------------------------------------------
    # kpi_snapshots
    # -----------------------------------------------------------------------
    op.create_table(
        "kpi_snapshots",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_uuid_v7()")),
        sa.Column(
            "tenant_id",
            sa.UUID(),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("snapshot_date", sa.Date(), nullable=False, unique=True),
        sa.Column("mau", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("dau", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("paying_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mrr_usd", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("arr_usd", sa.Numeric(20, 4), nullable=False, server_default="0"),
        sa.Column("heritage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("countries_count", sa.SmallInteger(), nullable=False, server_default="0"),
        sa.Column("nps_score", sa.Numeric(4, 1), nullable=True),
        sa.Column("churn_rate_pct", sa.Numeric(5, 2), nullable=True),
        sa.Column("ltv_usd", sa.Numeric(10, 2), nullable=True),
        sa.Column("cac_usd", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_kpi_snapshots_tenant_date", "kpi_snapshots", ["tenant_id", "snapshot_date"])

    # -----------------------------------------------------------------------
    # Seeds
    # -----------------------------------------------------------------------
    op.execute(
        f"""
        INSERT INTO fundraising_rounds (
            id, tenant_id, round_name, target_raise_usd, valuation_cap_usd,
            discount_pct, round_kind, status, raised_usd
        ) VALUES (
            gen_uuid_v7(),
            '{DEFAULT_TENANT_ID}'::uuid,
            'Seed',
            2000000.0000,
            8000000.0000,
            20.00,
            'safe',
            'planning',
            0.0000
        )
        """
    )

    op.execute(
        f"""
        INSERT INTO data_room_documents (
            id, tenant_id, name, description_md, category, version,
            doc_url, access_level, is_current
        ) VALUES (
            gen_uuid_v7(),
            '{DEFAULT_TENANT_ID}'::uuid,
            'SilkLens Pitch Deck — Teaser',
            'High-level investor teaser covering problem, solution, traction, and team.',
            'product',
            '1.0',
            'https://silklens.com/investor/pitch-deck-teaser-v1.pdf',
            'public_teaser',
            true
        )
        """
    )

    # 3 monthly KPI snapshots
    op.execute(
        f"""
        INSERT INTO kpi_snapshots (
            id, tenant_id, snapshot_date,
            mau, dau, paying_users,
            mrr_usd, arr_usd,
            heritage_count, countries_count,
            nps_score, churn_rate_pct, ltv_usd, cac_usd
        ) VALUES
        (gen_uuid_v7(), '{DEFAULT_TENANT_ID}'::uuid, '2026-03-01', 1200, 310, 48,  2400.0000,  28800.0000, 340, 12, 62.0, 3.20,  480.00,  35.00),
        (gen_uuid_v7(), '{DEFAULT_TENANT_ID}'::uuid, '2026-04-01', 2100, 540, 97,  4850.0000,  58200.0000, 520, 16, 67.5, 2.80,  510.00,  31.00),
        (gen_uuid_v7(), '{DEFAULT_TENANT_ID}'::uuid, '2026-05-01', 3800, 920, 174, 8700.0000, 104400.0000, 780, 19, 71.0, 2.10,  540.00,  27.00)
        """
    )


def downgrade() -> None:
    op.drop_table("data_room_access_grants")
    op.drop_table("kpi_snapshots")
    op.drop_table("data_room_documents")
    op.drop_table("investor_commitments")
    op.drop_table("fundraising_rounds")
    op.drop_table("investor_profiles")
