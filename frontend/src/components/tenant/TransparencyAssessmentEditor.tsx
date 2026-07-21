"use client";

import { useState } from "react";

import {
  type AITransparencyAssessmentUpsertDto,
  type AITransparencySystemRowDto,
  type AIValueChainRoleDto,
  type TransparencyControlKeyDto,
  type TransparencyControlStatusDto,
  updateAITransparencyAssessment,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

type TransparencyAssessmentEditorProps = {
  tenantId: string;
  system: AITransparencySystemRowDto;
  onSaved: () => Promise<void>;
};

type EditableControl = AITransparencyAssessmentUpsertDto["controls"][number] & {
  title_de: string;
  description_de: string;
  legal_basis: string;
  accountable_role: string;
};

const STATUS_OPTIONS: { value: TransparencyControlStatusDto; label: string }[] = [
  { value: "not_assessed", label: "Nicht bewertet" },
  { value: "not_applicable", label: "Nicht anwendbar" },
  { value: "planned", label: "Geplant" },
  { value: "implemented", label: "Implementiert" },
  { value: "verified", label: "Evidenzgeprüft" },
];

const ROLE_OPTIONS: { value: AIValueChainRoleDto; label: string }[] = [
  { value: "unknown", label: "Rolle noch offen" },
  { value: "provider", label: "Provider" },
  { value: "deployer", label: "Deployer" },
  { value: "both", label: "Provider und Deployer" },
];

function dateValue(timestamp: string | null): string {
  return timestamp ? timestamp.slice(0, 10) : "";
}

function utcDate(date: string): string | null {
  return date ? `${date}T12:00:00.000Z` : null;
}

function validateDraft(
  roleScope: AIValueChainRoleDto,
  owner: string,
  reviewer: string,
  reviewedDate: string,
  reviewDueDate: string,
  controls: EditableControl[],
): string | null {
  const verified = controls.filter((control) => control.status === "verified");
  const missingEvidence = verified.find((control) => !control.evidence_reference?.trim());
  if (missingEvidence) {
    return `„${missingEvidence.title_de}“ benötigt vor Verifizierung einen konkreten Nachweis.`;
  }
  const missingRationale = controls.find(
    (control) => control.status === "not_applicable" && !control.rationale?.trim(),
  );
  if (missingRationale) {
    return `„${missingRationale.title_de}“ benötigt eine begründete Nichtanwendbarkeit.`;
  }
  if (verified.length > 0 && roleScope === "unknown") {
    return "Vor einer Verifizierung muss die Provider-/Deployer-Rolle geklärt sein.";
  }
  if (
    verified.length > 0 &&
    (!owner.trim() || !reviewer.trim() || !reviewedDate || !reviewDueDate)
  ) {
    return "Verifizierte Kontrollen benötigen Control Owner, Reviewer, Prüfdatum und nächsten Review-Termin.";
  }
  if (owner.trim() && reviewer.trim() && owner.trim().toLocaleLowerCase() === reviewer.trim().toLocaleLowerCase()) {
    return "Control Owner und Reviewer müssen nach dem Vier-Augen-Prinzip verschieden sein.";
  }
  if (reviewedDate && reviewDueDate && reviewDueDate < reviewedDate) {
    return "Der nächste Review-Termin darf nicht vor dem Prüfdatum liegen.";
  }
  return null;
}

export function TransparencyAssessmentEditor({
  tenantId,
  system,
  onSaved,
}: TransparencyAssessmentEditorProps) {
  const assessment = system.assessment;
  const [roleScope, setRoleScope] = useState<AIValueChainRoleDto>(assessment.role_scope);
  const [controlOwner, setControlOwner] = useState(assessment.control_owner ?? "");
  const [reviewer, setReviewer] = useState(assessment.reviewer ?? "");
  const [reviewedDate, setReviewedDate] = useState(dateValue(assessment.reviewed_at_utc));
  const [reviewDueDate, setReviewDueDate] = useState(dateValue(assessment.review_due_at_utc));
  const [controls, setControls] = useState<EditableControl[]>(() =>
    assessment.controls.map((control) => ({
      control_key: control.control_key,
      status: control.status,
      evidence_reference: control.evidence_reference,
      rationale: control.rationale,
      title_de: control.title_de,
      description_de: control.description_de,
      legal_basis: control.legal_basis,
      accountable_role: control.accountable_role,
    })),
  );
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const updateControl = (
    key: TransparencyControlKeyDto,
    update: Partial<Pick<EditableControl, "status" | "evidence_reference" | "rationale">>,
  ) => {
    setControls((current) =>
      current.map((control) =>
        control.control_key === key ? { ...control, ...update } : control,
      ),
    );
    setMessage(null);
    setError(null);
  };

  const save = async () => {
    setMessage(null);
    setError(null);
    const validationError = validateDraft(
      roleScope,
      controlOwner,
      reviewer,
      reviewedDate,
      reviewDueDate,
      controls,
    );
    if (validationError) {
      setError(validationError);
      return;
    }

    setSaving(true);
    const body: AITransparencyAssessmentUpsertDto = {
      expected_version: assessment.version,
      role_scope: roleScope,
      control_owner: controlOwner.trim() || null,
      reviewer: reviewer.trim() || null,
      reviewed_at_utc: utcDate(reviewedDate),
      review_due_at_utc: utcDate(reviewDueDate),
      controls: controls.map((control) => ({
        control_key: control.control_key,
        status: control.status,
        evidence_reference: control.evidence_reference?.trim() || null,
        rationale: control.rationale?.trim() || null,
      })),
    };
    try {
      await updateAITransparencyAssessment(tenantId, system.ai_system_id, body);
      setMessage("Assessment revisionssicher gespeichert. Readiness wird neu berechnet.");
      try {
        await onSaved();
      } catch {
        setMessage(
          "Assessment wurde gespeichert; die aktualisierte Portfolioansicht konnte noch nicht geladen werden.",
        );
      }
    } catch (saveError) {
      setError(
        saveError instanceof Error
          ? saveError.message
          : "Assessment konnte nicht gespeichert werden.",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className={CH_CARD} aria-labelledby="transparency-assessment-editor-title">
      <div className="border-b border-slate-200 pb-5">
        <p className={CH_SECTION_LABEL}>Control attestation</p>
        <h3 id="transparency-assessment-editor-title" className="mt-1 text-xl font-semibold text-slate-950">
          Transparenzkontrollen und Nachweise
        </h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Ein Status „Evidenzgeprüft“ wird nur mit Beleg, unabhängiger Review-Rolle und
          Wiedervorlage akzeptiert. Funktionsrollen statt privater Namen reduzieren unnötige
          personenbezogene Daten.
        </p>
      </div>

      <fieldset className="mt-6 grid gap-4 md:grid-cols-2">
        <legend className="sr-only">Verantwortung und Review</legend>
        <label className="text-xs font-semibold text-slate-700" htmlFor="transparency-role-scope">
          Rolle in der AI-Wertschöpfungskette
          <select
            id="transparency-role-scope"
            className="mt-1 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
            value={roleScope}
            onChange={(event) => setRoleScope(event.target.value as AIValueChainRoleDto)}
          >
            {ROLE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className="text-xs font-semibold text-slate-700" htmlFor="transparency-owner">
          Control Owner (Funktionsrolle)
          <input
            id="transparency-owner"
            className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm font-normal text-slate-950"
            value={controlOwner}
            maxLength={255}
            onChange={(event) => setControlOwner(event.target.value)}
            placeholder="z. B. AI Product Control"
          />
        </label>
        <label className="text-xs font-semibold text-slate-700" htmlFor="transparency-reviewer">
          Unabhängiger Reviewer (Funktionsrolle)
          <input
            id="transparency-reviewer"
            className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm font-normal text-slate-950"
            value={reviewer}
            maxLength={255}
            onChange={(event) => setReviewer(event.target.value)}
            placeholder="z. B. Data Protection Review"
          />
        </label>
        <div className="grid grid-cols-2 gap-3">
          <label className="text-xs font-semibold text-slate-700" htmlFor="transparency-reviewed-date">
            Geprüft am
            <input
              id="transparency-reviewed-date"
              type="date"
              className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm font-normal text-slate-950"
              value={reviewedDate}
              onChange={(event) => setReviewedDate(event.target.value)}
            />
          </label>
          <label className="text-xs font-semibold text-slate-700" htmlFor="transparency-review-due-date">
            Nächster Review
            <input
              id="transparency-review-due-date"
              type="date"
              className="mt-1 block w-full rounded-xl border border-slate-300 px-3 py-2.5 text-sm font-normal text-slate-950"
              value={reviewDueDate}
              onChange={(event) => setReviewDueDate(event.target.value)}
            />
          </label>
        </div>
      </fieldset>

      <div className="mt-7 space-y-4">
        {controls.map((control, index) => {
          const baseId = `transparency-${control.control_key}`;
          return (
            <fieldset key={control.control_key} className="rounded-2xl border border-slate-200 bg-slate-50/70 p-4">
              <legend className="sr-only">{control.title_de}</legend>
              <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_15rem]">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-[0.65rem] font-semibold text-slate-400">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <h4 className="text-sm font-semibold text-slate-950">{control.title_de}</h4>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-600">{control.description_de}</p>
                  <p className="mt-2 text-[0.7rem] font-semibold text-slate-500">
                    {control.legal_basis} · accountable: {control.accountable_role}
                  </p>
                </div>
                <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-status`}>
                  Kontrollstatus
                  <select
                    id={`${baseId}-status`}
                    className="mt-1 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
                    value={control.status}
                    onChange={(event) =>
                      updateControl(control.control_key, {
                        status: event.target.value as TransparencyControlStatusDto,
                      })
                    }
                  >
                    {STATUS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-evidence`}>
                  Evidenzreferenz
                  <input
                    id={`${baseId}-evidence`}
                    className="mt-1 block w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
                    value={control.evidence_reference ?? ""}
                    maxLength={1024}
                    onChange={(event) =>
                      updateControl(control.control_key, {
                        evidence_reference: event.target.value,
                      })
                    }
                    placeholder="Dokument-ID, kontrollierte URL oder Evidence-Bundle-Referenz"
                  />
                </label>
                <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-rationale`}>
                  Begründung / Scope-Entscheidung
                  <textarea
                    id={`${baseId}-rationale`}
                    className="mt-1 block min-h-20 w-full rounded-xl border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal leading-5 text-slate-950"
                    value={control.rationale ?? ""}
                    maxLength={4000}
                    onChange={(event) =>
                      updateControl(control.control_key, { rationale: event.target.value })
                    }
                    placeholder="Nachvollziehbare Begründung, Prüfmethode oder Ausnahme dokumentieren"
                  />
                </label>
              </div>
            </fieldset>
          );
        })}
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-5">
        <p className="text-xs text-slate-500">
          Aktuelle Version: v{assessment.version} · konfliktgeschütztes Speichern
        </p>
        <button
          type="button"
          className={CH_BTN_PRIMARY}
          disabled={saving}
          onClick={() => void save()}
        >
          {saving ? "Wird revisionssicher gespeichert…" : "Assessment speichern"}
        </button>
      </div>
      {error ? (
        <p role="alert" className="mt-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
          {error}
        </p>
      ) : null}
      {message ? (
        <p role="status" className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
          {message}
        </p>
      ) : null}
    </section>
  );
}
