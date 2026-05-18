import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/lib/i18n/request.ts');

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  reactStrictMode: true,
  poweredByHeader: false,
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
    typedRoutes: false,
  },
  images: {
    remotePatterns: [
      // Allowlist MinIO / CDN hosts here as they come online.
      { protocol: 'https', hostname: '**.silklens.app' },
      { protocol: 'http', hostname: 'localhost' },
    ],
  },
};

export default withNextIntl(nextConfig);
