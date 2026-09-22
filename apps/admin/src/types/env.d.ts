/**
 * Typed `process.env` surface for the admin panel.
 *
 * NEVER read `process.env.SOMETHING` directly; everything that crosses the
 * boundary into the app must be declared here so missing or mistyped names
 * become a compile-time error.
 */
declare namespace NodeJS {
  interface ProcessEnv {
    readonly NODE_ENV: 'development' | 'production' | 'test';
    readonly AUTH_SECRET: string;
    readonly AUTH_URL?: string;
    readonly AUTH_TRUST_HOST?: string;
    readonly NEXT_PUBLIC_API_URL: string;
    readonly API_INTERNAL_URL?: string;
    readonly NEXT_PUBLIC_DEFAULT_TENANT_ID: string;
    readonly AUTH_GOOGLE_ID?: string;
    readonly AUTH_GOOGLE_SECRET?: string;
    readonly AUTH_APPLE_ID?: string;
    readonly AUTH_APPLE_SECRET?: string;
  }
}
