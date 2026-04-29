import { resolve } from 'path';

/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@workspace/ui'],
  output: 'standalone', // still supports SSR and API routes
  // Let the client-proxy handler forward trailing-slash URLs verbatim to FastAPI
  // instead of Next.js 308-redirecting them away before the handler runs.
  skipTrailingSlashRedirect: true,
  turbopack: {
    root: resolve(import.meta.dirname, '../../'), // anchor to frontend/ monorepo root
  },
  async redirects() {
    return [
      {
        source: '/',
        destination: '/agents',
        permanent: false,
      },
      {
        source: '/agents/:agentId/evals',
        destination: '/agents/:agentId/evals/test-cases',
        permanent: false,
      },
    ];
  },
};

export default nextConfig;
