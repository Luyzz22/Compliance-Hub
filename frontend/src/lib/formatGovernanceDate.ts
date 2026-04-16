/**
 * Einheitliche Datums-/Zeitdarstellung für Governance-Workspaces (de-DE).
 */
export function formatGovernanceDateTime(iso: string | null | undefined): string {
  if (!iso) {
    return "—";
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return iso;
  }
  return d.toLocaleString("de-DE", { dateStyle: "short", timeStyle: "short" });
}

export function formatGovernanceTime(iso: string | null | undefined): string {
  if (!iso) {
    return "";
  }
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) {
    return "";
  }
  return d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
}
