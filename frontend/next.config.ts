// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone", // Enables standalone output
  basePath: '/copertine', // Add basePath inside the nextConfig object
  images: {
    unoptimized: true,
    domains: ['localhost'],
  },
  // Add static directory configuration for images
  async rewrites() {
    return [
      {
        source: '/copertine/images/:path*',
        destination: '/images/:path*',
      },
      {
        source: '/copertine/api/:path*',
        destination: '/api/:path*', // Rewrite API routes to handle basePath
      },
    ];
  },
  env: {
    COP_BACKEND_URL: process.env.COP_BACKEND_URL || 'http://localhost:8000',
  },
};

export default nextConfig;
