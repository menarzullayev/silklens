"""roles, permissions, RBAC + scoped role assignments

Per Agent 2 §4 the RBAC model is:
  permissions   (atomic strings like 'heritage:create')
  roles         (named bags of permissions)
  role_permissions (M:N)
  user_roles    (M:N + optional scope: tenant_id, region, etc.)

ABAC overlay (``attribute_policies``) is left for a later migration once the
moderation pipeline (Agent 5) starts emitting attribute keys.

Revision ID: 0006_rbac
Revises: 0005_oauth_identities
Create Date: 2026-05-18
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0006_rbac"
down_revision: str | Sequence[str] | None = "0005_oauth_identities"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEED_PERMISSIONS: tuple[tuple[str, str], ...] = (
    # heritage
    ("heritage:read", "Read heritage objects"),
    ("heritage:create", "Create new heritage entries"),
    ("heritage:update", "Edit heritage entries"),
    ("heritage:delete", "Soft-delete heritage entries"),
    ("heritage:moderate", "Approve / reject contributor edits"),
    # identity / users
    ("user:read", "Read user profiles"),
    ("user:update", "Edit user profiles"),
    ("user:ban", "Ban / unban users"),
    ("user:impersonate", "Sign in as another user (audit-heavy)"),
    # moderation
    ("moderation:read", "View moderation queue"),
    ("moderation:act", "Approve / reject UGC"),
    # billing
    ("billing:read", "View billing data"),
    ("billing:refund", "Issue refunds"),
    ("billing:configure_plans", "Edit plans / prices"),
    # tenants
    ("tenant:read", "List tenants"),
    ("tenant:create", "Create new tenants"),
    ("tenant:manage", "Edit tenant settings"),
    ("tenant:branding", "Edit tenant branding"),
    # AI
    ("ai:configure", "Edit AI model registry / fallback chains"),
    ("ai:invoke_unrestricted", "Invoke AI without per-user quota limits"),
    # admin / system
    ("system:settings", "Edit system_settings"),
    ("system:feature_flags", "Edit feature_flags"),
    ("audit:read", "Read the audit log"),
)


SEED_ROLES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    (
        "viewer",
        '{"en":"Viewer","uz":"Ko''ruvchi"}',
        ("heritage:read", "user:read"),
    ),
    (
        "contributor",
        '{"en":"Contributor","uz":"Yordamchi"}',
        ("heritage:read", "heritage:create", "heritage:update", "user:read"),
    ),
    (
        "moderator",
        '{"en":"Moderator","uz":"Moderator"}',
        (
            "heritage:read",
            "heritage:update",
            "heritage:moderate",
            "user:read",
            "user:ban",
            "moderation:read",
            "moderation:act",
        ),
    ),
    (
        "tenant_admin",
        '{"en":"Tenant admin","uz":"Tenant administratori"}',
        (
            "heritage:read",
            "heritage:create",
            "heritage:update",
            "heritage:delete",
            "heritage:moderate",
            "user:read",
            "user:update",
            "user:ban",
            "moderation:read",
            "moderation:act",
            "billing:read",
            "billing:configure_plans",
            "tenant:manage",
            "tenant:branding",
            "ai:configure",
            "system:settings",
            "system:feature_flags",
            "audit:read",
        ),
    ),
    (
        "super_admin",
        '{"en":"Super admin","uz":"Bosh administrator"}',
        tuple(p for p, _ in SEED_PERMISSIONS),  # all
    ),
)


def upgrade() -> None:
    # --- permissions catalog ----------------------------------------------
    op.execute(
        """
        CREATE TABLE permissions (
            id          uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug        text NOT NULL UNIQUE,
            description text,
            created_at  timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*:[a-z][a-z0-9_]*$')
        );

        COMMENT ON TABLE permissions IS
            'Atomic permission strings. Format: ''<resource>:<action>''. '
            'Per Agent 2 §4.';
        """
    )

    # --- roles ------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE roles (
            id              uuid PRIMARY KEY DEFAULT gen_uuid_v7(),
            slug            text NOT NULL UNIQUE,
            display_name    jsonb NOT NULL DEFAULT '{}'::jsonb,
            description     text,
            is_system       boolean NOT NULL DEFAULT false,
            tenant_id       uuid REFERENCES tenants(id) ON DELETE CASCADE,
            created_at      timestamptz NOT NULL DEFAULT now(),
            updated_at      timestamptz NOT NULL DEFAULT now(),
            CHECK (slug ~ '^[a-z][a-z0-9_]*$')
        );

        CREATE INDEX idx_roles_tenant ON roles(tenant_id) WHERE tenant_id IS NOT NULL;

        CREATE TRIGGER tg_roles_updated_at
            BEFORE UPDATE ON roles
            FOR EACH ROW EXECUTE FUNCTION app.tg_set_updated_at();

        COMMENT ON COLUMN roles.tenant_id IS
            'NULL = platform-wide role; otherwise scoped to a single tenant';
        COMMENT ON COLUMN roles.is_system IS
            'true = locked, cannot be deleted, predicates referenced from app code';
        """
    )

    # --- role_permissions (M:N) -------------------------------------------
    op.execute(
        """
        CREATE TABLE role_permissions (
            role_id        uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_id  uuid NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
            created_at     timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (role_id, permission_id)
        );

        CREATE INDEX idx_role_permissions_permission ON role_permissions(permission_id);
        """
    )

    # --- user_roles (with optional scope, partitioned by residency) ------
    op.execute(
        """
        CREATE TABLE user_roles (
            id                  uuid NOT NULL DEFAULT gen_uuid_v7(),
            user_id             uuid NOT NULL,
            residency_region    text NOT NULL,
            role_id             uuid NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            scope_tenant_id     uuid REFERENCES tenants(id) ON DELETE CASCADE,
            scope_region        text,
            granted_by          uuid,
            granted_at          timestamptz NOT NULL DEFAULT now(),
            expires_at          timestamptz,
            revoked_at          timestamptz,
            revoke_reason       text,

            PRIMARY KEY (id, residency_region),
            FOREIGN KEY (user_id, residency_region)
                REFERENCES users(id, residency_region) ON DELETE CASCADE,
            CHECK (residency_region IN ('uz','eu','us','global'))
        ) PARTITION BY LIST (residency_region);
        """
    )
    for region in ("uz", "eu", "us", "global"):
        op.execute(
            f"CREATE TABLE user_roles_{region} "
            f"PARTITION OF user_roles FOR VALUES IN ('{region}');"
        )

    op.execute(
        """
        CREATE INDEX idx_user_roles_user
            ON user_roles(user_id) WHERE revoked_at IS NULL;
        CREATE INDEX idx_user_roles_role
            ON user_roles(role_id) WHERE revoked_at IS NULL;
        CREATE INDEX idx_user_roles_scope_tenant
            ON user_roles(scope_tenant_id)
            WHERE scope_tenant_id IS NOT NULL AND revoked_at IS NULL;

        COMMENT ON TABLE user_roles IS
            'Scoped role assignments. scope_tenant_id NULL = platform-wide; '
            'scope_region NULL = global; expires_at NULL = permanent.';
        """
    )

    # --- has_permission helper -------------------------------------------
    # Used by RLS policies, FastAPI guard middleware, and admin SQL audits.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION app.has_permission(
            p_user_id uuid,
            p_residency_region text,
            p_permission_slug text,
            p_tenant_id uuid DEFAULT NULL
        ) RETURNS boolean
        LANGUAGE sql STABLE PARALLEL SAFE AS $$
            SELECT EXISTS (
                SELECT 1
                FROM user_roles ur
                JOIN role_permissions rp ON rp.role_id = ur.role_id
                JOIN permissions p       ON p.id = rp.permission_id
                WHERE ur.user_id = p_user_id
                  AND ur.residency_region = p_residency_region
                  AND p.slug = p_permission_slug
                  AND ur.revoked_at IS NULL
                  AND (ur.expires_at IS NULL OR ur.expires_at > now())
                  AND (
                    ur.scope_tenant_id IS NULL
                    OR p_tenant_id IS NULL
                    OR ur.scope_tenant_id = p_tenant_id
                  )
            );
        $$;

        COMMENT ON FUNCTION app.has_permission IS
            'Single source of truth for permission checks. Per Agent 2 cross-agent contract.';
        """
    )

    # --- Seed permissions + roles ----------------------------------------
    perm_values = ",\n            ".join(
        f"('{slug}', '{desc}')" for slug, desc in SEED_PERMISSIONS
    )
    op.execute(
        f"""
        INSERT INTO permissions (slug, description) VALUES
            {perm_values};
        """
    )

    for role_slug, display, role_perms in SEED_ROLES:
        op.execute(
            f"""
            INSERT INTO roles (slug, display_name, is_system)
            VALUES ('{role_slug}', '{display}'::jsonb, true);

            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.slug = '{role_slug}'
              AND p.slug = ANY(ARRAY[{','.join(f"'{p}'" for p in role_perms)}]);
            """
        )

    # System actor is the super_admin (so AI-driven writes have full authority)
    op.execute(
        """
        INSERT INTO user_roles (user_id, residency_region, role_id, scope_tenant_id, granted_by)
        SELECT
            '00000000-0000-0000-0000-000000000002'::uuid,
            'global',
            r.id,
            NULL,
            '00000000-0000-0000-0000-000000000002'::uuid
        FROM roles r
        WHERE r.slug = 'super_admin';
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS app.has_permission(uuid, text, text, uuid);")
    op.execute("DROP TABLE IF EXISTS user_roles CASCADE;")
    op.execute("DROP TABLE IF EXISTS role_permissions CASCADE;")
    op.execute("DROP TABLE IF EXISTS roles CASCADE;")
    op.execute("DROP TABLE IF EXISTS permissions CASCADE;")
