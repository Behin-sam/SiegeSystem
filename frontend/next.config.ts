import type { NextConfig } from "next";

/**
 * Next.js configuration.
 * `output: "standalone"` produces a minimal server bundle for the Docker image.
 * Rewrites proxy `/api/*` to the FastAPI backend so the browser only ever
 * talks to a single origin in development.
 */
const nextConfig: NextConfig = {
  output: "standalone",
  reactStrictMode: true,
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
