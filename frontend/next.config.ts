// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone", // Enables standalone output
  basePath: '/copertine', // Add basePath inside the nextConfig object
};

export default nextConfig;

