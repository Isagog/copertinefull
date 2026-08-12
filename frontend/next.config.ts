// next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  output: "standalone", // Enables standalone output
  images: {
    unoptimized: true,
    domains: ['localhost'],
  },
  async redirects() {
    return [
      // The archive lived at /copertine for years — as a subpath of the shared
      // mema3 vhost, and then briefly on its own host, where `/` merely
      // redirected here. Now that it owns `/` the prefix is redundant with the
      // domain name, but externally held links still carry it. Redirect the
      // other way so those keep working. Permanent: the old path is not coming
      // back. /api/copertine is a different route and is untouched.
      { source: "/copertine", destination: "/", permanent: true },
    ];
  },
};

export default nextConfig;

