import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Compliance Hub",
    short_name: "Compliance Hub",
    description: "Enterprise GRC und AI Governance für den DACH-Markt.",
    start_url: "/",
    display: "standalone",
    background_color: "#f5f7fb",
    theme_color: "#07111f",
    lang: "de",
  };
}
