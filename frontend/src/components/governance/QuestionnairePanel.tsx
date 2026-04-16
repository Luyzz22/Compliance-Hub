import type { ReactNode } from "react";

import { CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";
import { formatGovernanceTime } from "@/lib/formatGovernanceDate";

export type GovernanceSaveState = "idle" | "saving" | "saved" | "error";

export interface QuestionnairePanelProps {
  sectionLabel?: string;
  title?: string;
  readOnly: boolean;
  saveState: GovernanceSaveState;
  savedAtIso: string | null;
  initialLoadError?: string | null;
  children: ReactNode;
}

/**
 * Fragebogen-Panel mit einheitlichem Autosave-Hinweis (ISO / NIS2 / AI Act).
 */
export function QuestionnairePanel({
  sectionLabel = "Fragebogen",
  title = "Eingaben",
  readOnly,
  saveState,
  savedAtIso,
  initialLoadError,
  children,
}: QuestionnairePanelProps) {
  return (
    <article className={CH_CARD}>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div>
          <p className={CH_SECTION_LABEL}>{sectionLabel}</p>
          <h2 className="mt-1 text-lg font-semibold text-slate-900">{title}</h2>
        </div>
        <p className="text-xs text-slate-500" aria-live="polite">
          {readOnly ? (
            <span className="font-medium text-slate-700">Abgeschlossen — nur Lesen.</span>
          ) : saveState === "saving" ? (
            <span className="font-medium text-[var(--sbs-navy-deep)]">Speichern…</span>
          ) : saveState === "saved" && savedAtIso ? (
            <span className="font-medium text-emerald-800">
              Gespeichert um {formatGovernanceTime(savedAtIso)}
            </span>
          ) : saveState === "error" ? (
            <span className="font-medium text-rose-800">Letzter Speicherversuch fehlgeschlagen</span>
          ) : (
            <span>Änderungen werden automatisch gespeichert.</span>
          )}
        </p>
      </div>

      {initialLoadError ? (
        <p className="mt-4 text-sm text-amber-900" role="alert">
          {initialLoadError}
        </p>
      ) : null}

      <div className="mt-6">{children}</div>
    </article>
  );
}
