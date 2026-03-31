export type PortfolioHealth = "critical" | "attention" | "on_track";

export function portfolioHealth(
  readiness: number,
  setupRatio: number
): PortfolioHealth {
  if (readiness < 0.5) return "critical";
  if (readiness < 0.6 || setupRatio < 0.5) return "attention";
  return "on_track";
}
