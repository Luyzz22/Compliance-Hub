import type { ReactNode } from "react";

import type { ClassificationViewModel } from "@/lib/aiActSelfAssessmentModels";
import { CH_CARD, CH_CARD_MUTED, CH_SECTION_LABEL } from "@/lib/boardLayout";

export interface ClassificationPanelProps {
  sectionLabel?: string;
  title?: string;
  runCompleted: boolean;
  pendingHint?: ReactNode;
  classificationError?: string | null;
  model: ClassificationViewModel | null;
}

/**
 * Klassifikations-/Ergebnis-Panel (domain-neutral, Inhalt aus ViewModel).
 */
export function ClassificationPanel({
  sectionLabel = "Risiko & Begründung",
  title = "Klassifikation",
  runCompleted,
  pendingHint,
  classificationError,
  model,
}: ClassificationPanelProps) {
  const defaultPending =
    pendingHint ??
    "Die Klassifikation steht erst nach Abschluss des Runs zur Verfügung. Bitte zuerst „Run abschließen“ ausführen.";

  return (
    <article className={CH_CARD}>
      <p className={CH_SECTION_LABEL}>{sectionLabel}</p>
      <h2 className="mt-1 text-lg font-semibold text-slate-900">{title}</h2>
      {!runCompleted ? (
        <p className="mt-4 text-sm leading-relaxed text-slate-600">{defaultPending}</p>
      ) : classificationError ? (
        <p className="mt-4 text-sm text-rose-800" role="alert">
          {classificationError}
        </p>
      ) : model ? (
        <div className={`mt-4 space-y-4 text-sm ${CH_CARD_MUTED}`}>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              risk_level
            </div>
            <div className="mt-1 text-base font-semibold text-slate-900">{model.riskLevel}</div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              requires_manual_review
            </div>
            <div className="mt-1 font-medium text-slate-800">
              {model.requiresManualReview == null
                ? "—"
                : model.requiresManualReview
                  ? "Ja"
                  : "Nein"}
            </div>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              rationale
            </div>
            <p className="mt-1 whitespace-pre-wrap text-slate-800">{model.rationale}</p>
          </div>
          <div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              eu_ai_act_refs
            </div>
            {model.euAiActRefs.length ? (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-slate-800">
                {model.euAiActRefs.map((ref) => (
                  <li key={ref}>{ref}</li>
                ))}
              </ul>
            ) : (
              <div className="mt-1">—</div>
            )}
          </div>
        </div>
      ) : (
        <p className="mt-4 text-sm text-slate-600">Keine Klassifikationsdaten geliefert.</p>
      )}
    </article>
  );
}
