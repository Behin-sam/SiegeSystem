import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "export",
  basePath: "/SiegeSystem",
  assetPrefix: "/SiegeSystem/",
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
