import type { MetadataRoute } from "next";

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: ["/", "/kontakt", "/trust-center", "/impressum", "/datenschutz"],
      disallow: ["/admin/", "/advisor/", "/api/", "/auth/", "/board/", "/settings", "/tenant/"],
    },
    sitemap: "https://complywithai.de/sitemap.xml",
    host: "https://complywithai.de",
  };
}
