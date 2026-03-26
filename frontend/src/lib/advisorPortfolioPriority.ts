import type { AdvisorPortfolioTenantEntry } from "@/lib/api";

export type PortfolioPillarFilter = "readiness" | "gai" | "monitoring";
export type PortfolioScenarioFilter = "a" | "b" | "c" | "d";
/** Schnellfilter: hohe Priorität / Aufbau+Monitoring vs. Optimierung. */
export type PortfolioSegmentFilter = "aufbau_monitoring" | "optimierung";

export function advisorPrioritySortKey(t: AdvisorPortfolioTenantEntry): number {
  const k = t.advisor_priority_sort_key;
  return typeof k === "number" ? k : 1;
}

export function priorityLabelDe(bucket: string | undefined): string {
  if (bucket === "high") return "Hoch";
  if (bucket === "low") return "Niedrig";
  return "Mittel";
}

export function priorityBadgeClasses(bucket: string | undefined): string {
  if (bucket === "high") {
    return "bg-rose-50 text-rose-900 ring-1 ring-rose-200";
  }
  if (bucket === "low") {
    return "bg-slate-100 text-slate-700 ring-1 ring-slate-200";
  }
  return "bg-amber-50 text-amber-950 ring-1 ring-amber-200";
}

export function matchesPillarFocus(
  t: AdvisorPortfolioTenantEntry,
  pillar: PortfolioPillarFilter,
): boolean {
  const primary = t.primary_focus_tag_de ?? "";
  const gai = t.governance_activity_summary?.level;
  const oami = t.operational_monitoring_summary?.level;
  if (pillar === "readiness") {
    return primary === "Readiness" || t.maturity_scenario_hint === "a";
  }
  if (pillar === "gai") {
    return primary === "Nutzung" || gai === "low" || gai === "medium";
  }
  return (
    primary === "Monitoring" ||
    t.maturity_scenario_hint === "b" ||
    oami === "low" ||
    oami == null
  );
}

export function matchesSegmentFilter(
  t: AdvisorPortfolioTenantEntry,
  segment: PortfolioSegmentFilter,
): boolean {
  const p = t.advisor_priority ?? "medium";
  const h = t.maturity_scenario_hint;
  if (segment === "aufbau_monitoring") {
    return p === "high" || h === "a" || h === "b";
  }
  return p === "low" || h === "d";
}

export function applyAdvisorPortfolioFilters(
  rows: AdvisorPortfolioTenantEntry[],
  filters: {
    pillar: PortfolioPillarFilter | null;
    scenario: PortfolioScenarioFilter | null;
    segment: PortfolioSegmentFilter | null;
    priorityBucket: "high" | "medium" | "low" | null;
  },
): AdvisorPortfolioTenantEntry[] {
  return rows.filter((t) => {
    if (filters.pillar && !matchesPillarFocus(t, filters.pillar)) return false;
    if (filters.scenario && t.maturity_scenario_hint !== filters.scenario) return false;
    if (filters.segment && !matchesSegmentFilter(t, filters.segment)) return false;
    if (filters.priorityBucket && (t.advisor_priority ?? "medium") !== filters.priorityBucket) {
      return false;
    }
    return true;
  });
}
