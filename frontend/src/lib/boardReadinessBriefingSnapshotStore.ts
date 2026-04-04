import "server-only";

import { mkdir, readFile, writeFile } from "fs/promises";
import { dirname, join } from "path";

import type { BoardReadinessBriefingBaselineFile } from "@/lib/boardReadinessBriefingTypes";

function resolvePath(): string {
  const fromEnv = process.env.BOARD_READINESS_BRIEFING_BASELINE_PATH?.trim();
  if (fromEnv) return fromEnv;
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-board-readiness-briefing-baseline.json");
  }
  return join(process.cwd(), "data", "board-readiness-briefing-baseline.json");
}

export async function readBoardReadinessBriefingBaseline(): Promise<BoardReadinessBriefingBaselineFile | null> {
  const path = resolvePath();
  try {
    const raw = await readFile(path, "utf8");
    const o = JSON.parse(raw) as BoardReadinessBriefingBaselineFile;
    if (!o || typeof o !== "object") return null;
    if (typeof o.saved_at !== "string" || typeof o.overall_status !== "string") return null;
    if (!o.pillar_status || typeof o.pillar_status !== "object") return null;
    return o;
  } catch {
    return null;
  }
}

export async function writeBoardReadinessBriefingBaseline(
  baseline: BoardReadinessBriefingBaselineFile,
): Promise<void> {
  const path = resolvePath();
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(baseline, null, 2)}\n`, "utf8");
}
