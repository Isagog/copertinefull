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
  optimizeFonts: true,
};

export default nextConfig;

