import "server-only";

import { join } from "path";

import type { BoardReadinessBriefingBaselineFile } from "@/lib/boardReadinessBriefingTypes";
import {
  absoluteRuntimeFilePath,
  readRuntimeTextFile,
  writeRuntimeTextFile,
} from "@/lib/runtimeFileIO";

function resolvePath(): string {
  const fromEnv = process.env.BOARD_READINESS_BRIEFING_BASELINE_PATH?.trim();
  if (fromEnv) return absoluteRuntimeFilePath(fromEnv);
  if (process.env.VERCEL) {
    return join("/tmp", "compliancehub-board-readiness-briefing-baseline.json");
  }
  return join(process.cwd(), "data", "board-readiness-briefing-baseline.json");
}

export async function readBoardReadinessBriefingBaseline(): Promise<BoardReadinessBriefingBaselineFile | null> {
  const path = resolvePath();
  try {
    const raw = await readRuntimeTextFile(path);
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
  await writeRuntimeTextFile(path, `${JSON.stringify(baseline, null, 2)}\n`);
}
