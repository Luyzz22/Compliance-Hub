import "server-only";

import { mkdir, readFile, writeFile } from "fs/promises";
import { dirname, join } from "path";

const FILE_VERSION = "wave47-v1";

function statePath(): string {
  const fromEnv = process.env.ADVISOR_SLA_SIGNAL_STATE_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-advisor-sla-signal-state.json");
  }
  return join(process.cwd(), "data", "advisor-sla-signal-state.json");
}

export type AdvisorSlaSignalStateFile = {
  version: string;
  updated_at: string;
  /** Critical rule_ids vom letzten erfolgreichen Portfolio-Lauf. */
  last_critical_rule_ids: string[];
};

export async function readAdvisorSlaSignalState(): Promise<{ critical_rule_ids: string[] }> {
  const path = statePath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as Record<string, unknown>;
    if (!o || typeof o !== "object") return { critical_rule_ids: [] };
    const ids: string[] = [];
    if (Array.isArray(o.last_critical_rule_ids)) {
      for (const x of o.last_critical_rule_ids) {
        if (typeof x === "string" && x.trim()) ids.push(x.trim());
      }
    }
    return { critical_rule_ids: ids };
  } catch {
    return { critical_rule_ids: [] };
  }
}

export async function writeAdvisorSlaSignalState(criticalRuleIds: string[]): Promise<void> {
  const path = statePath();
  const state: AdvisorSlaSignalStateFile = {
    version: FILE_VERSION,
    updated_at: new Date().toISOString(),
    last_critical_rule_ids: [...new Set(criticalRuleIds)],
  };
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(state, null, 2)}\n`, "utf8");
}
