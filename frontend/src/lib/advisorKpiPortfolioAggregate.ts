import "server-only";

import { buildAdvisorKpiPortfolioSnapshot } from "@/lib/advisorKpiPortfolioBuild";
import { readAdvisorMandantRemindersState } from "@/lib/advisorMandantReminderStore";
import { computeKanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioAggregate";
import type { KanzleiPortfolioPayload } from "@/lib/kanzleiPortfolioTypes";

/** KPIs zu bereits geladenem Portfolio (ein Portfolio-Compute pro Request). */
export async function attachAdvisorKpiToPayload(
  payload: KanzleiPortfolioPayload,
  nowMs: number,
  windowDays: number = 90,
  segmentBy: "readiness" | "primary_segment" = "readiness",
) {
  const { reminders } = await readAdvisorMandantRemindersState();
  return buildAdvisorKpiPortfolioSnapshot({
    payload,
    reminders,
    nowMs,
    windowDays,
    segmentBy,
  });
}

export async function computeAdvisorKpiPortfolioSnapshot(
  now: Date = new Date(),
  windowDays: number = 90,
  segmentBy: "readiness" | "primary_segment" = "readiness",
) {
  const payload = await computeKanzleiPortfolioPayload(now);
  return attachAdvisorKpiToPayload(payload, now.getTime(), windowDays, segmentBy);
}
