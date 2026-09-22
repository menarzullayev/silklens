import { redirect } from 'next/navigation';

import { auth } from '@/lib/auth/auth';

/**
 * Bare-root landing — redirects to the dashboard when authenticated, or to
 * the login page otherwise. `middleware.ts` provides the same redirect at the
 * edge, but this is a defensive second gate for direct hits to `/`.
 */
export default async function RootIndex(): Promise<never> {
  const session = await auth();
  redirect(session ? '/dashboard' : '/login');
}
