// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone", // Enables standalone output
  images: {
    unoptimized: true,
    domains: ['localhost'],
  },
};

export default nextConfig;

