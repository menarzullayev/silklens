import { type ReactNode } from 'react';

import { auth } from '@/lib/auth/auth';
import {
  hasAnyPermission,
  hasPermission,
  type Permission,
} from '@/lib/rbac/permissions';

type GuardMode = 'all' | 'any';

interface PermissionGuardProps {
  /** Single permission (string) or list of permissions. */
  readonly permission: Permission | readonly Permission[];
  /** With multiple permissions, default `all` requires every entry; `any` is OR. */
  readonly mode?: GuardMode;
  /** What to render when the user is authorised. */
  readonly children: ReactNode;
  /** Optional fallback for the unauthorised case. */
  readonly fallback?: ReactNode;
}

/**
 * Server Component — reads the NextAuth session and only renders `children`
 * when the user's permission set satisfies `permission`.
 *
 * Intentionally a Server Component so no permission information leaks into
 * the client bundle. Pages requiring permission-conditional UI on the client
 * should hoist the check up here and pass already-checked data down.
 */
export async function PermissionGuard({
  permission,
  mode = 'all',
  children,
  fallback = null,
}: PermissionGuardProps): Promise<JSX.Element> {
  const session = await auth();
  const granted = session?.user?.permissions;

  const list = Array.isArray(permission) ? permission : [permission as Permission];
  const ok =
    mode === 'any' ? hasAnyPermission(granted, list) : hasPermission(granted, list);

  return <>{ok ? children : fallback}</>;
}
