import type { MetadataRoute } from "next";

const publicRoutes = ["", "/kontakt", "/trust-center", "/impressum", "/datenschutz"];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date("2026-07-14T00:00:00.000Z");
  return publicRoutes.map((route, index) => ({
    url: `https://complywithai.de${route}`,
    lastModified,
    changeFrequency: index === 0 ? "weekly" : "monthly",
    priority: index === 0 ? 1 : 0.6,
  }));
}
