import type { NextConfig } from "next";

const securityHeaders = [
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Permitted-Cross-Domain-Policies", value: "none" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
  {
    key: "Permissions-Policy",
    value:
      "camera=(), microphone=(), geolocation=(), payment=(), usb=(), browsing-topics=()",
  },
  ...(process.env.NODE_ENV === "production"
    ? [
        {
          key: "Strict-Transport-Security",
          value: "max-age=63072000; includeSubDomains; preload",
        },
      ]
    : []),
];

const nextConfig: NextConfig = {
  /**
   * Ausgabeformat nach Zielplattform.
   *
   * Der Hetzner-Container kopiert `.next/standalone` (siehe `Dockerfile.hetzner`)
   * und braucht deshalb `standalone`. Auf Vercel verpackt der Plattform-Adapter
   * die Ausgabe selbst — und mit `standalone` bricht dessen `onBuildComplete` ab:
   * `ENOENT … .next/next-server.js.nft.json`. Reproduziert mit Vercel CLI 61.1.0
   * und `NEXT_ENABLE_ADAPTER=1`; ohne `standalone` baut derselbe Stand durch.
   *
   * Der Fehler kam mit PR #290, zusammen mit der Plattformsperre im Release-Gate,
   * und blieb hinter ihr verborgen: solange das Gate jeden Vercel-Build vorher
   * abbrach, kam kein Build bis zu dieser Stelle.
   *
   * `VERCEL` setzt ausschließlich die Plattform. Im Container verbieten Preflight
   * und Release-Gate die Variable, ein Container-Build entsteht also nie ohne
   * `standalone`.
   */
  output: process.env.VERCEL ? undefined : "standalone",
  poweredByHeader: false,
  reactStrictMode: true,
  turbopack: {
    root: __dirname,
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: securityHeaders,
      },
    ];
  },
};

export default nextConfig;
