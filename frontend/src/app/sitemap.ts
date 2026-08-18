import type { MetadataRoute } from "next";

import { MARKETING_ROUTES } from "@/lib/marketing/navigation";

const SITE_ORIGIN = "https://complywithai.de";

/** Priorität nach Rolle in der Conversion-Strecke, nicht nach Verzeichnistiefe. */
const ROUTES: { path: string; priority: number; changeFrequency: "weekly" | "monthly" }[] = [
  { path: MARKETING_ROUTES.home, priority: 1, changeFrequency: "weekly" },
  { path: MARKETING_ROUTES.platform, priority: 0.9, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.aiAct, priority: 0.9, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.nis2, priority: 0.9, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.advisors, priority: 0.8, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.integrations, priority: 0.7, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.security, priority: 0.8, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.resources, priority: 0.7, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.productTour, priority: 0.7, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.demo, priority: 0.9, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.contact, priority: 0.6, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.trustCenter, priority: 0.6, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.imprint, priority: 0.3, changeFrequency: "monthly" },
  { path: MARKETING_ROUTES.privacy, priority: 0.3, changeFrequency: "monthly" },
];

export default function sitemap(): MetadataRoute.Sitemap {
  const lastModified = new Date("2026-08-18T00:00:00.000Z");
  return ROUTES.map((route) => ({
    url: `${SITE_ORIGIN}${route.path === "/" ? "" : route.path}`,
    lastModified,
    changeFrequency: route.changeFrequency,
    priority: route.priority,
  }));
}
