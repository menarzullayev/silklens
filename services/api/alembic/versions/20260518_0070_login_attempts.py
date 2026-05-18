"""login_attempts (daily RANGE partitions) — brute-force defence

Per Agent 2 §4. Captures every login attempt (successful or not) so the
auth service can detect brute-force patterns from a single IP+identifier
combination and lock the account for a cool-down window (currently 15min
after 5 failures inside 10min).

Append-only table, daily RANGE partitions on ``attempted_at``. Index on
``(identifier, attempted_at DESC)`` makes the lookback query (last 10min
for an identifier+IP) cheap on the current-day partition.

Revision ID: 0070_login_attempts
Revises: 0062_security_patches
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta

from alembic import op

revision: str = "0070_login_attempts"
down_revision: str | Sequence[str] | None = "0062_security_patches"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- login_attempts (parent; partitioned daily on attempted_at) -----
    op.execute(
        """
        CREATE TABLE login_attempts (
            id              uuid NOT NULL DEFAULT gen_uuid_v7(),
            identifier      text NOT NULL,
            succeeded       boolean NOT NULL,
            ip_address      inet,
            user_agent      text,
            failure_reason  text,
            attempted_at    timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (id, attempted_at)
        ) PARTITION BY RANGE (attempted_at);

        COMMENT ON TABLE login_attempts IS
            'Append-only brute-force-defence ledger. Daily RANGE partitions; '
            'auth service queries the last 10min for (identifier, ip) to '
            'enforce lockout. Per Agent 2 §4.';
        COMMENT ON COLUMN login_attempts.identifier IS
            'Normalized identity the caller offered (email lowercased, or phone, '
            'or "ip:<hash>" for fully anonymous brute-force).';
        """
    )

    op.execute(
        """
        CREATE INDEX idx_login_attempts_identifier_at
            ON login_attempts (identifier, attempted_at DESC);
        CREATE INDEX idx_login_attempts_ip_at
            ON login_attempts (ip_address, attempted_at DESC)
            WHERE ip_address IS NOT NULL;
        """
    )

    # Provision daily partitions ±7 days. pg_partman extends in production.
    today = date.today()
    for offset in range(-1, 8):
        d = today + timedelta(days=offset)
        d_next = d + timedelta(days=1)
        part_name = f"login_attempts_{d.strftime('%Y%m%d')}"
        op.execute(
            f"""
            CREATE TABLE {part_name}
                PARTITION OF login_attempts
                FOR VALUES FROM ('{d.isoformat()}') TO ('{d_next.isoformat()}');
            """
        )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS login_attempts CASCADE;")
