import { CH_BADGE } from "@/lib/boardLayout";

export type GovernanceStatusTone = "success" | "warning" | "neutral";

const TONE_CLASS: Record<GovernanceStatusTone, string> = {
  success: "bg-emerald-100 text-emerald-900 ring-emerald-200/80",
  warning: "bg-amber-100 text-amber-950 ring-amber-200/80",
  neutral: "bg-slate-100 text-slate-800 ring-slate-200/80",
};

/** Heuristik für Run-Status (EU AI Act & ähnliche Workspaces). */
export function governanceStatusToneFromRunStatus(status: string): GovernanceStatusTone {
  switch (status) {
    case "completed":
      return "success";
    case "in_review":
      return "warning";
    default:
      return "neutral";
  }
}

export interface StatusBadgeProps {
  status: string;
  /** Wenn gesetzt, überschreibt die automatische Tönung. */
  tone?: GovernanceStatusTone;
  className?: string;
}

/**
 * Wiederverwendbare Status-Pille für Governance-Workspaces (ISO, NIS2, AI Act, …).
 */
export function StatusBadge({ status, tone, className }: StatusBadgeProps) {
  const resolved = tone ?? governanceStatusToneFromRunStatus(status);
  return (
    <span className={`${CH_BADGE} ${TONE_CLASS[resolved]} ${className ?? ""}`.trim()}>
      {status}
    </span>
  );
}
