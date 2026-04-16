"use client";

import { QuestionnairePanel, type GovernanceSaveState } from "@/components/governance/QuestionnairePanel";

const DOMAIN_OPTIONS = [
  { value: "HR", label: "HR" },
  { value: "Critical Infrastructure", label: "Kritische Infrastruktur" },
  { value: "Healthcare", label: "Gesundheitswesen" },
  { value: "Law Enforcement", label: "Strafverfolgung" },
  { value: "Other", label: "Sonstiges" },
] as const;

function asBool(v: unknown): boolean {
  if (typeof v === "boolean") {
    return v;
  }
  if (v === 1 || v === "1" || v === "true") {
    return true;
  }
  return false;
}

function asString(v: unknown, fallback: string): string {
  if (v == null) {
    return fallback;
  }
  return String(v);
}

const FIELD_CLASS =
  "mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-900 shadow-sm outline-none transition focus:border-[var(--sbs-navy-mid)] focus:ring-2 focus:ring-[var(--sbs-navy-mid)]/20 disabled:cursor-not-allowed disabled:bg-slate-50";

export interface AiActSelfAssessmentQuestionnairePanelProps {
  readOnly: boolean;
  answers: Record<string, unknown>;
  saveState: GovernanceSaveState;
  savedAt: string | null;
  initialAnswersError?: string | null;
  onAnswerChange: (key: string, value: unknown) => void;
}

export function AiActSelfAssessmentQuestionnairePanel({
  readOnly,
  answers,
  saveState,
  savedAt,
  initialAnswersError,
  onAnswerChange,
}: AiActSelfAssessmentQuestionnairePanelProps) {
  const domainValue = asString(
    answers.intended_use_domain,
    DOMAIN_OPTIONS[DOMAIN_OPTIONS.length - 1]!.value,
  );

  return (
    <QuestionnairePanel
      readOnly={readOnly}
      saveState={saveState}
      savedAtIso={savedAt}
      initialLoadError={initialAnswersError}
    >
      <div className="grid gap-6 sm:grid-cols-2">
        <label className="block text-sm">
          <span className="font-medium text-slate-800">Einsatzbereich (intended_use_domain)</span>
          <select
            className={FIELD_CLASS}
            disabled={readOnly}
            value={DOMAIN_OPTIONS.some((o) => o.value === domainValue) ? domainValue : "Other"}
            onChange={(e) => onAnswerChange("intended_use_domain", e.target.value)}
          >
            {DOMAIN_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        </label>

        {(
          [
            ["interacts_with_humans", "Interagiert mit Menschen"],
            ["uses_personal_data", "Verarbeitet personenbezogene Daten"],
            ["uses_biometric_identification", "Biometrische Identifikation"],
            ["is_gpai_model", "General Purpose AI (GPAI) / Foundation Model"],
            ["performs_automated_decision_making", "Automatisierte Entscheidungsfindung"],
            ["monitors_public_spaces", "Überwachung öffentlicher Räume"],
            ["safety_component_of_product", "Sicherheitskomponente eines Produkts"],
            ["uses_emotion_recognition", "Emotionserkennung"],
          ] as const
        ).map(([key, label]) => (
          <label
            key={key}
            className="flex items-center justify-between gap-3 rounded-xl border border-slate-200/80 bg-slate-50/40 px-3 py-3 text-sm"
          >
            <span className="text-slate-800">{label}</span>
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-slate-300 text-[var(--sbs-navy-mid)] focus:ring-[var(--sbs-navy-mid)] disabled:cursor-not-allowed"
              disabled={readOnly}
              checked={asBool(answers[key])}
              onChange={(e) => onAnswerChange(key, e.target.checked)}
            />
          </label>
        ))}
      </div>

      <label className="mt-6 block text-sm">
        <span className="font-medium text-slate-800">
          Dokumentationsreife (documentation_maturity)
        </span>
        <select
          className={`${FIELD_CLASS} max-w-md`}
          disabled={readOnly}
          value={asString(answers.documentation_maturity, "basic")}
          onChange={(e) => onAnswerChange("documentation_maturity", e.target.value)}
        >
          <option value="basic">Basis</option>
          <option value="structured">Strukturiert</option>
          <option value="full">Vollständig / auditierbar</option>
        </select>
      </label>
    </QuestionnairePanel>
  );
}
