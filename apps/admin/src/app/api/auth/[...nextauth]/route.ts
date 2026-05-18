/**
 * NextAuth v5 catch-all route — `/api/auth/{signin,signout,session,callback/*}`.
 * Handler instances come from `@/lib/auth/auth` so the config lives in one
 * place (and is reachable from Server Components / Server Actions).
 */
export { GET, POST } from '@/lib/auth/handlers';
