"""Row-Level Security for tenant-bearing tables + app.set_tenant_context helper

Per master architecture §4 (cross-agent contracts) + Agent 6 §4 (multi-tenancy
strategy = row-level, NOT schema-per-tenant):

  - Every table that carries a ``tenant_id uuid`` column gets RLS enabled.
  - A single policy ``<table>_tenant_isolation`` enforces
        tenant_id = current_setting('app.tenant_id')::uuid
    OR  current_setting('app.bypass_rls') = 'on'   (system_actor / migrations)
  - The API sets ``SET LOCAL app.tenant_id = '…'`` per request (lands in a
    follow-up middleware migration after auth-middleware ships) — until then
    the policy is inert (current_setting with missing_ok=true returns NULL,
    which fails the predicate, so no rows are visible by default → safe).

Discovery is dynamic. Instead of hard-coding the table list (which would
break when parallel agents add more), we enumerate from information_schema
at migration time and apply ENABLE ROW LEVEL SECURITY + CREATE POLICY to
every public-schema table that has a ``tenant_id`` column.

Tables to be EXCLUDED:
  - ``tenants`` itself — it IS the tenant directory; tenant scoping makes no
    sense (you'd need the tenant row to discover yourself). Manage via RBAC.

Helper function ``app.set_tenant_context(uuid)`` ships for the future
middleware to call. ``app.clear_tenant_context()`` is its inverse.

Revision ID: 0054_rls_tenancy
Revises: 0053_b2b_enterprise
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0054_rls_tenancy"
down_revision: str | Sequence[str] | None = "0053_b2b_enterprise"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tables that have a tenant_id column but are RLS-exempt by design.
_RLS_EXEMPT_TABLES = (
    "tenants",  # the tenant directory itself
)


def upgrade() -> None:
    # --- helper functions for setting/clearing the tenant context --------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.set_tenant_context(p_tenant_id uuid)
        RETURNS void
        LANGUAGE plpgsql AS $$
        BEGIN
            -- SET LOCAL only lives for the current transaction; the API MUST
            -- call this once per request inside its DB transaction.
            PERFORM set_config('app.tenant_id', p_tenant_id::text, true);
        END;
        $$;

        CREATE OR REPLACE FUNCTION app.clear_tenant_context()
        RETURNS void
        LANGUAGE plpgsql AS $$
        BEGIN
            PERFORM set_config('app.tenant_id', '', true);
        END;
        $$;

        CREATE OR REPLACE FUNCTION app.set_bypass_rls(p_on boolean DEFAULT true)
        RETURNS void
        LANGUAGE plpgsql AS $$
        BEGIN
            -- Used by privileged jobs (entitlement resolver, dunning worker,
            -- analytics ETL) that legitimately span tenants. The bypass is
            -- transaction-local; callers should set it explicitly per job.
            PERFORM set_config('app.bypass_rls', CASE WHEN p_on THEN 'on' ELSE 'off' END, true);
        END;
        $$;

        COMMENT ON FUNCTION app.set_tenant_context IS
            'Called by API middleware per request inside the DB transaction. '
            'Pairs with the <table>_tenant_isolation RLS policy.';
        """
    )

    # --- enable RLS + attach the isolation policy to every tenant table --
    # Done dynamically so parallel agents adding new tenant_id-bearing tables
    # later don''t need to re-edit this migration. Exempt list = the tenants
    # table itself.
    exempt_list = ", ".join(f"'{t}'" for t in _RLS_EXEMPT_TABLES)
    op.execute(
        f"""
        DO $do$
        DECLARE
            r record;
            v_policy_name text;
        BEGIN
            FOR r IN
                SELECT c.table_schema, c.table_name
                FROM information_schema.columns c
                JOIN information_schema.tables t
                  ON  t.table_schema = c.table_schema
                  AND t.table_name   = c.table_name
                WHERE c.column_name  = 'tenant_id'
                  AND c.table_schema = 'public'
                  AND t.table_type   = 'BASE TABLE'
                  AND c.table_name NOT IN ({exempt_list})
                ORDER BY c.table_name
            LOOP
                EXECUTE format('ALTER TABLE %I.%I ENABLE ROW LEVEL SECURITY',
                               r.table_schema, r.table_name);

                v_policy_name := r.table_name || '_tenant_isolation';

                -- Drop-and-create so re-running this migration in dev is safe.
                EXECUTE format(
                    'DROP POLICY IF EXISTS %I ON %I.%I',
                    v_policy_name, r.table_schema, r.table_name
                );

                EXECUTE format($f$
                    CREATE POLICY %I ON %I.%I
                    USING (
                        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
                        OR current_setting('app.bypass_rls', true) = 'on'
                    )
                    WITH CHECK (
                        tenant_id = NULLIF(current_setting('app.tenant_id', true), '')::uuid
                        OR current_setting('app.bypass_rls', true) = 'on'
                    )
                $f$,
                    v_policy_name, r.table_schema, r.table_name
                );
            END LOOP;
        END
        $do$;
        """
    )

    # Note: this won''t actually enforce anything until the API sets
    # ``SET LOCAL app.tenant_id = ...`` per request. The bypass is left on
    # for the system role to keep migrations and offline jobs working.
    op.execute(
        """
        COMMENT ON FUNCTION app.set_bypass_rls(boolean) IS
            'Transaction-local RLS bypass. Used by privileged cross-tenant '
            'workers (entitlement resolver, dunning, analytics ETL).';
        """
    )


def downgrade() -> None:
    # Drop every <table>_tenant_isolation policy and disable RLS on those
    # tables. Same dynamic discovery so we mirror upgrade() exactly.
    exempt_list = ", ".join(f"'{t}'" for t in _RLS_EXEMPT_TABLES)
    op.execute(
        f"""
        DO $do$
        DECLARE
            r record;
            v_policy_name text;
        BEGIN
            FOR r IN
                SELECT c.table_schema, c.table_name
                FROM information_schema.columns c
                JOIN information_schema.tables t
                  ON  t.table_schema = c.table_schema
                  AND t.table_name   = c.table_name
                WHERE c.column_name  = 'tenant_id'
                  AND c.table_schema = 'public'
                  AND t.table_type   = 'BASE TABLE'
                  AND c.table_name NOT IN ({exempt_list})
            LOOP
                v_policy_name := r.table_name || '_tenant_isolation';
                EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I',
                               v_policy_name, r.table_schema, r.table_name);
                EXECUTE format('ALTER TABLE %I.%I DISABLE ROW LEVEL SECURITY',
                               r.table_schema, r.table_name);
            END LOOP;
        END
        $do$;
        """
    )

    op.execute("DROP FUNCTION IF EXISTS app.set_bypass_rls(boolean);")
    op.execute("DROP FUNCTION IF EXISTS app.clear_tenant_context();")
    op.execute("DROP FUNCTION IF EXISTS app.set_tenant_context(uuid);")
