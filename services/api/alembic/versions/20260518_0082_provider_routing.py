"""Per-currency payment provider routing — seed system_settings rows.

WAVE-6 / FAZA 5 (multi-currency payments). Adds platform-default rows in
``system_settings`` so the billing factory can resolve a provider per
ISO-4217 currency without redeploying code:

  * ``billing.provider_by_currency.UZS``      → ``payme``
  * ``billing.provider_by_currency.USD``      → ``stripe``
  * ``billing.provider_by_currency.EUR``      → ``stripe``
  * ``billing.provider_by_currency.default``  → ``mock``

Admins flip these per-tenant via the admin UI. The system-tenant row acts as
the platform default for any tenant that hasn't overridden the slot.

The values use the existing ``value_type='string'`` and ``scope='global'``
slots from migration 0003 — no schema changes; only INSERTs.

Revision ID: 0082_provider_routing
Revises: 0071_compliance
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0082_provider_routing"
down_revision: str | Sequence[str] | None = "0071_compliance"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Seed data (currency_code, provider_slug, human description).
PROVIDER_ROUTING: tuple[tuple[str, str, str], ...] = (
    ("UZS", "payme", "Uzbek Sum → Payme (primary), Click fallback via admin override."),
    ("USD", "stripe", "US Dollar → Stripe."),
    ("EUR", "stripe", "Euro → Stripe."),
    ("GBP", "stripe", "British Pound → Stripe."),
    ("RUB", "stripe", "Russian Rouble → Stripe."),
    ("default", "mock", "Fallback provider for any currency without explicit routing."),
)


def upgrade() -> None:
    """Seed the per-currency routing rows scoped to the platform's default tenant.

    We resolve the default tenant by slug ``default`` (seeded in
    migration 0002 under id 00000000-0000-0000-0000-000000000001). The
    (tenant_id, key) UNIQUE index in 0003 keeps the seed idempotent under
    re-application.
    """
    op.execute(
        """
        INSERT INTO system_settings (tenant_id, key, value, value_type, scope, description)
        SELECT
            t.id,
            'billing.provider_by_currency.' || row.currency,
            to_jsonb(row.provider),
            'string',
            'global',
            row.description
        FROM tenants t
        CROSS JOIN LATERAL (VALUES
            ('UZS',     'payme',  'Uzbek Sum → Payme (primary); Click as admin override.'),
            ('USD',     'stripe', 'US Dollar → Stripe.'),
            ('EUR',     'stripe', 'Euro → Stripe.'),
            ('GBP',     'stripe', 'British Pound → Stripe.'),
            ('RUB',     'stripe', 'Russian Rouble → Stripe.'),
            ('default', 'mock',   'Fallback provider for any currency without explicit routing.')
        ) AS row(currency, provider, description)
        WHERE t.slug = 'default'
        ON CONFLICT (tenant_id, key) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM system_settings
        WHERE key LIKE 'billing.provider_by_currency.%';
        """
    )
