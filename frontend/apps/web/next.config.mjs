/** @type {import('next').NextConfig} */
const nextConfig = {
  transpilePackages: ['@workspace/ui'],
  output: 'standalone', // still supports SSR and API routes
};

export default nextConfig;
