"use client";

import { useState } from "react";

import {
  type AIImpactAssessmentSystemRowDto,
  type AIImpactAssessmentUpsertDto,
  type ImpactAssessmentLifecycleDto,
  type ImpactAssessmentScopeDto,
  type ImpactDeployerContextDto,
  type ImpactResidualRiskDto,
  type ImpactSectionKeyDto,
  type ImpactSectionStatusDto,
  type PriorConsultationStatusDto,
  type StakeholderViewsStatusDto,
  updateAIImpactAssessment,
} from "@/lib/api";
import { CH_BTN_PRIMARY, CH_CARD, CH_SECTION_LABEL } from "@/lib/boardLayout";

type ImpactAssessmentEditorProps = {
  tenantId: string;
  system: AIImpactAssessmentSystemRowDto;
  onSaved: () => Promise<void>;
};

type EditableSection = AIImpactAssessmentUpsertDto["sections"][number] & {
  title_de: string;
  description_de: string;
  legal_basis: string;
};

const SCOPE_OPTIONS: { value: ImpactAssessmentScopeDto; label: string }[] = [
  { value: "undetermined", label: "Noch zu prüfen" },
  { value: "required", label: "Erforderlich" },
  { value: "not_required", label: "Nicht erforderlich, begründet" },
];

const CONTEXT_OPTIONS: { value: ImpactDeployerContextDto; label: string }[] = [
  { value: "unknown", label: "Kontext noch offen" },
  { value: "public_authority", label: "Öffentliche Stelle" },
  { value: "public_service_provider", label: "Privater Erbringer öffentlicher Dienste" },
  { value: "essential_private_service", label: "Wesentlicher privater Dienst" },
  { value: "other", label: "Anderer Einsatzkontext" },
];

const LIFECYCLE_OPTIONS: { value: ImpactAssessmentLifecycleDto; label: string }[] = [
  { value: "draft", label: "Entwurf" },
  { value: "in_review", label: "In unabhängiger Prüfung" },
  { value: "remediation_required", label: "Abhilfe erforderlich" },
  { value: "approved", label: "Intern freigegeben" },
];

const RISK_OPTIONS: { value: ImpactResidualRiskDto; label: string }[] = [
  { value: "unknown", label: "Noch nicht bewertet" },
  { value: "low", label: "Niedrig" },
  { value: "medium", label: "Mittel" },
  { value: "high", label: "Hoch" },
];

const CONSULTATION_OPTIONS: { value: PriorConsultationStatusDto; label: string }[] = [
  { value: "not_assessed", label: "Noch zu prüfen" },
  { value: "not_required", label: "Nicht erforderlich" },
  { value: "required", label: "Erforderlich" },
  { value: "planned", label: "Vorbereitet" },
  { value: "submitted", label: "Eingereicht" },
  { value: "closed", label: "Abgeschlossen" },
];

const STAKEHOLDER_OPTIONS: { value: StakeholderViewsStatusDto; label: string }[] = [
  { value: "not_assessed", label: "Noch zu prüfen" },
  { value: "not_applicable", label: "Nicht einschlägig, begründet" },
  { value: "planned", label: "Beteiligung geplant" },
  { value: "obtained", label: "Sichtweisen eingeholt" },
];

const SECTION_STATUS_OPTIONS: { value: ImpactSectionStatusDto; label: string }[] = [
  { value: "not_started", label: "Nicht begonnen" },
  { value: "drafted", label: "Beschrieben" },
  { value: "evidenced", label: "Mit Evidenz" },
  { value: "reviewed", label: "Unabhängig geprüft" },
  { value: "not_applicable", label: "Nicht anwendbar" },
];

function dateValue(timestamp: string | null): string {
  return timestamp ? timestamp.slice(0, 10) : "";
}

function utcDate(date: string): string | null {
  return date ? `${date}T12:00:00.000Z` : null;
}

function sectionStatusClasses(status: ImpactSectionStatusDto): string {
  if (status === "reviewed") return "bg-emerald-50 text-emerald-800 ring-emerald-200";
  if (status === "evidenced") return "bg-cyan-50 text-cyan-900 ring-cyan-200";
  if (status === "not_applicable") return "bg-slate-100 text-slate-700 ring-slate-200";
  if (status === "drafted") return "bg-amber-50 text-amber-900 ring-amber-200";
  return "bg-white text-slate-500 ring-slate-200";
}

function sectionStatusLabel(status: ImpactSectionStatusDto): string {
  return SECTION_STATUS_OPTIONS.find((option) => option.value === status)?.label ?? status;
}

type DraftForValidation = {
  dpiaScope: ImpactAssessmentScopeDto;
  friaScope: ImpactAssessmentScopeDto;
  scopeRationale: string;
  lifecycleStatus: ImpactAssessmentLifecycleDto;
  residualRisk: ImpactResidualRiskDto;
  assessmentOwner: string;
  independentReviewer: string;
  dpoInvolved: boolean;
  consultationStatus: PriorConsultationStatusDto;
  consultationReference: string;
  reviewedDate: string;
  approvedDate: string;
  reviewDueDate: string;
  sections: EditableSection[];
};

function validateDraft(draft: DraftForValidation): string | null {
  const reviewedWithoutEvidence = draft.sections.find(
    (section) =>
      section.status === "reviewed" &&
      (!section.summary?.trim() || !section.evidence_reference?.trim()),
  );
  if (reviewedWithoutEvidence) {
    return `„${reviewedWithoutEvidence.title_de}“ benötigt für den Review eine Zusammenfassung und Evidenzreferenz.`;
  }
  const missingRationale = draft.sections.find(
    (section) => section.status === "not_applicable" && !section.rationale?.trim(),
  );
  if (missingRationale) {
    return `„${missingRationale.title_de}“ benötigt eine konkrete Begründung der Nichtanwendbarkeit.`;
  }
  if (
    (draft.dpiaScope === "not_required" || draft.friaScope === "not_required") &&
    !draft.scopeRationale.trim()
  ) {
    return "Eine Entscheidung ‚nicht erforderlich‘ benötigt eine nachvollziehbare Scope-Begründung.";
  }
  if (
    draft.assessmentOwner.trim() &&
    draft.independentReviewer.trim() &&
    draft.assessmentOwner.trim().toLocaleLowerCase() ===
      draft.independentReviewer.trim().toLocaleLowerCase()
  ) {
    return "Assessment Owner und unabhängiger Reviewer müssen verschieden sein.";
  }
  if (
    ["submitted", "closed"].includes(draft.consultationStatus) &&
    !draft.consultationReference.trim()
  ) {
    return "Eine eingereichte oder abgeschlossene Konsultation benötigt eine kontrollierte Referenz.";
  }
  if (draft.reviewedDate && draft.reviewDueDate && draft.reviewDueDate < draft.reviewedDate) {
    return "Die Wiedervorlage darf nicht vor dem Review-Datum liegen.";
  }
  if (draft.reviewedDate && draft.approvedDate && draft.approvedDate < draft.reviewedDate) {
    return "Das Freigabedatum darf nicht vor dem Review-Datum liegen.";
  }
  if (
    ["in_review", "remediation_required", "approved"].includes(draft.lifecycleStatus) &&
    !draft.assessmentOwner.trim()
  ) {
    return "Ab dem Review-Status ist eine verantwortliche Funktionsrolle erforderlich.";
  }
  if (draft.lifecycleStatus !== "approved") return null;

  if (draft.dpiaScope === "undetermined" || draft.friaScope === "undetermined") {
    return "Vor einer internen Freigabe müssen DSFA- und FRIA-Scope entschieden sein.";
  }
  if (
    !draft.assessmentOwner.trim() ||
    !draft.independentReviewer.trim() ||
    !draft.reviewedDate ||
    !draft.approvedDate ||
    !draft.reviewDueDate
  ) {
    return "Eine interne Freigabe benötigt Owner, unabhängigen Reviewer, Review-, Freigabe- und Wiedervorlagetermine.";
  }
  if (draft.dpiaScope === "required" && !draft.dpoInvolved) {
    return "Bei erforderlicher DSFA muss die Einbindung der Datenschutzbeauftragten dokumentiert sein.";
  }
  const requiredScope = draft.dpiaScope === "required" || draft.friaScope === "required";
  if (requiredScope) {
    const incomplete = draft.sections.find((section) => section.status !== "reviewed");
    if (incomplete) {
      return `Vor der internen Freigabe muss „${incomplete.title_de}“ unabhängig geprüft sein.`;
    }
    if (draft.residualRisk === "unknown") {
      return "Vor der internen Freigabe muss das Residualrisiko bewertet sein.";
    }
  }
  if (draft.residualRisk === "high" && draft.consultationStatus !== "closed") {
    return "Hohes Residualrisiko blockiert die interne Freigabe bis zum dokumentierten Abschluss des Konsultations-Gates.";
  }
  return null;
}

export function ImpactAssessmentEditor({
  tenantId,
  system,
  onSaved,
}: ImpactAssessmentEditorProps) {
  const assessment = system.assessment;
  const [dpiaScope, setDpiaScope] = useState(assessment.dpia_scope);
  const [friaScope, setFriaScope] = useState(assessment.fria_scope);
  const [deployerContext, setDeployerContext] = useState(assessment.deployer_context);
  const [scopeRationale, setScopeRationale] = useState(assessment.scope_rationale ?? "");
  const [lifecycleStatus, setLifecycleStatus] = useState(assessment.lifecycle_status);
  const [residualRisk, setResidualRisk] = useState(assessment.residual_risk);
  const [assessmentOwner, setAssessmentOwner] = useState(assessment.assessment_owner ?? "");
  const [independentReviewer, setIndependentReviewer] = useState(
    assessment.independent_reviewer ?? "",
  );
  const [dpoInvolved, setDpoInvolved] = useState(assessment.dpo_involved);
  const [stakeholderViewsStatus, setStakeholderViewsStatus] = useState(
    assessment.stakeholder_views_status,
  );
  const [consultationStatus, setConsultationStatus] = useState(
    assessment.prior_consultation_status,
  );
  const [consultationReference, setConsultationReference] = useState(
    assessment.prior_consultation_reference ?? "",
  );
  const [reviewedDate, setReviewedDate] = useState(dateValue(assessment.reviewed_at_utc));
  const [approvedDate, setApprovedDate] = useState(dateValue(assessment.approved_at_utc));
  const [reviewDueDate, setReviewDueDate] = useState(dateValue(assessment.review_due_at_utc));
  const [sections, setSections] = useState<EditableSection[]>(() =>
    assessment.sections.map((section) => ({
      section_key: section.section_key,
      status: section.status,
      summary: section.summary,
      evidence_reference: section.evidence_reference,
      rationale: section.rationale,
      title_de: section.title_de,
      description_de: section.description_de,
      legal_basis: section.legal_basis,
    })),
  );
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const updateSection = (
    key: ImpactSectionKeyDto,
    update: Partial<Pick<EditableSection, "status" | "summary" | "evidence_reference" | "rationale">>,
  ) => {
    setSections((current) =>
      current.map((section) =>
        section.section_key === key ? { ...section, ...update } : section,
      ),
    );
    setMessage(null);
    setError(null);
  };

  const save = async () => {
    setMessage(null);
    setError(null);
    const validationError = validateDraft({
      dpiaScope,
      friaScope,
      scopeRationale,
      lifecycleStatus,
      residualRisk,
      assessmentOwner,
      independentReviewer,
      dpoInvolved,
      consultationStatus,
      consultationReference,
      reviewedDate,
      approvedDate,
      reviewDueDate,
      sections,
    });
    if (validationError) {
      setError(validationError);
      return;
    }

    const body: AIImpactAssessmentUpsertDto = {
      expected_version: assessment.version,
      dpia_scope: dpiaScope,
      fria_scope: friaScope,
      deployer_context: deployerContext,
      scope_rationale: scopeRationale.trim() || null,
      lifecycle_status: lifecycleStatus,
      residual_risk: residualRisk,
      assessment_owner: assessmentOwner.trim() || null,
      independent_reviewer: independentReviewer.trim() || null,
      dpo_involved: dpoInvolved,
      stakeholder_views_status: stakeholderViewsStatus,
      prior_consultation_status: consultationStatus,
      prior_consultation_reference: consultationReference.trim() || null,
      reviewed_at_utc: utcDate(reviewedDate),
      approved_at_utc: utcDate(approvedDate),
      review_due_at_utc: utcDate(reviewDueDate),
      sections: sections.map((section) => ({
        section_key: section.section_key,
        status: section.status,
        summary: section.summary?.trim() || null,
        evidence_reference: section.evidence_reference?.trim() || null,
        rationale: section.rationale?.trim() || null,
      })),
    };

    setSaving(true);
    try {
      await updateAIImpactAssessment(tenantId, system.ai_system_id, body);
      setMessage("Assessment und Audit-Trail wurden gespeichert. Die Portfolio-Posture wird aktualisiert.");
      try {
        await onSaved();
      } catch {
        setMessage(
          "Assessment wurde gespeichert; die aktualisierte Portfolioansicht konnte noch nicht geladen werden.",
        );
      }
    } catch (saveError) {
      const detail =
        saveError instanceof Error ? saveError.message : "Assessment konnte nicht gespeichert werden.";
      setError(
        detail.includes("409")
          ? "Eine neuere Version liegt vor. Bitte laden Sie die Seite neu und übernehmen Sie Ihre Änderungen kontrolliert."
          : detail,
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className={CH_CARD} aria-labelledby="impact-assessment-editor-title">
      <div className="border-b border-slate-200 pb-5">
        <p className={CH_SECTION_LABEL}>Impact Assessment Record</p>
        <h3 id="impact-assessment-editor-title" className="mt-1 text-xl font-semibold text-slate-950">
          Scope, Risikoprüfung und Freigabe-Gates
        </h3>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
          Verwenden Sie Funktionsrollen und kontrollierte Dokument-IDs. Erfassen Sie keine Secrets,
          unnötigen Personendaten oder frei zugänglichen Links zu sensiblen Nachweisen.
        </p>
      </div>

      <fieldset className="mt-6">
        <legend className="text-sm font-semibold text-slate-950">1. Anwendungsbereich dokumentieren</legend>
        <p className="mt-1 text-xs leading-5 text-slate-500">
          Die Register-Signale unterstützen die Prüfung, ersetzen aber keine fachliche Scope-Entscheidung.
        </p>
        <div className="mt-4 grid gap-4 md:grid-cols-3">
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-dpia-scope">
            DSFA-Scope
            <select
              id="impact-dpia-scope"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
              value={dpiaScope}
              onChange={(event) => setDpiaScope(event.target.value as ImpactAssessmentScopeDto)}
            >
              {SCOPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-fria-scope">
            FRIA-Scope
            <select
              id="impact-fria-scope"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
              value={friaScope}
              onChange={(event) => setFriaScope(event.target.value as ImpactAssessmentScopeDto)}
            >
              {SCOPE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-deployer-context">
            Einsatzkontext
            <select
              id="impact-deployer-context"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
              value={deployerContext}
              onChange={(event) => setDeployerContext(event.target.value as ImpactDeployerContextDto)}
            >
              {CONTEXT_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
        </div>
        <label className="mt-4 block text-xs font-semibold text-slate-700" htmlFor="impact-scope-rationale">
          Scope-Begründung
          <textarea
            id="impact-scope-rationale"
            className="mt-1 block min-h-24 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal leading-6 text-slate-950"
            value={scopeRationale}
            maxLength={4000}
            onChange={(event) => setScopeRationale(event.target.value)}
            placeholder="Annahmen, Einsatzgrenze, Rechts- und Risikoprüfung sowie begründete Nichtanwendbarkeit dokumentieren"
          />
        </label>
      </fieldset>

      <fieldset className="mt-8 border-t border-slate-200 pt-6">
        <legend className="text-sm font-semibold text-slate-950">2. Steuerungs- und Reviewstatus</legend>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-lifecycle">
            Lifecycle
            <select
              id="impact-lifecycle"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
              value={lifecycleStatus}
              onChange={(event) => setLifecycleStatus(event.target.value as ImpactAssessmentLifecycleDto)}
            >
              {LIFECYCLE_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-residual-risk">
            Residualrisiko
            <select
              id="impact-residual-risk"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
              value={residualRisk}
              onChange={(event) => setResidualRisk(event.target.value as ImpactResidualRiskDto)}
            >
              {RISK_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-stakeholder-views">
            Sichtweisen Betroffener
            <select
              id="impact-stakeholder-views"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
              value={stakeholderViewsStatus}
              onChange={(event) => setStakeholderViewsStatus(event.target.value as StakeholderViewsStatusDto)}
            >
              {STAKEHOLDER_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-owner">
            Assessment Owner (Funktionsrolle)
            <input
              id="impact-owner"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-normal text-slate-950"
              value={assessmentOwner}
              maxLength={255}
              onChange={(event) => setAssessmentOwner(event.target.value)}
              placeholder="z. B. Privacy Impact Control"
            />
          </label>
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-reviewer">
            Unabhängiger Reviewer (Funktionsrolle)
            <input
              id="impact-reviewer"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-normal text-slate-950"
              value={independentReviewer}
              maxLength={255}
              onChange={(event) => setIndependentReviewer(event.target.value)}
              placeholder="z. B. Independent Data Protection Review"
            />
          </label>
          <label className="flex min-h-11 items-center gap-3 self-end rounded-lg border border-slate-300 bg-slate-50 px-3 py-2.5 text-xs font-semibold text-slate-800">
            <input
              type="checkbox"
              className="h-4 w-4 accent-[var(--sbs-navy-mid)]"
              checked={dpoInvolved}
              onChange={(event) => setDpoInvolved(event.target.checked)}
            />
            DSB-Einbindung dokumentiert
          </label>
        </div>
      </fieldset>

      <fieldset className="mt-8 border-t border-slate-200 pt-6">
        <legend className="text-sm font-semibold text-slate-950">3. Konsultation und Termine</legend>
        <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-consultation-status">
            Vorherige Konsultation
            <select
              id="impact-consultation-status"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
              value={consultationStatus}
              onChange={(event) => setConsultationStatus(event.target.value as PriorConsultationStatusDto)}
            >
              {CONSULTATION_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
            </select>
          </label>
          <label className="text-xs font-semibold text-slate-700 md:col-span-1 xl:col-span-2" htmlFor="impact-consultation-reference">
            Konsultationsreferenz
            <input
              id="impact-consultation-reference"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-normal text-slate-950"
              value={consultationReference}
              maxLength={1024}
              onChange={(event) => setConsultationReference(event.target.value)}
              placeholder="Kontrollierte Vorgangs- oder Dokument-ID, keine sensiblen Inhalte"
            />
          </label>
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-reviewed-date">
            Unabhängig geprüft am
            <input
              id="impact-reviewed-date"
              type="date"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-normal text-slate-950"
              value={reviewedDate}
              onChange={(event) => setReviewedDate(event.target.value)}
            />
          </label>
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-approved-date">
            Intern freigegeben am
            <input
              id="impact-approved-date"
              type="date"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-normal text-slate-950"
              value={approvedDate}
              onChange={(event) => setApprovedDate(event.target.value)}
            />
          </label>
          <label className="text-xs font-semibold text-slate-700" htmlFor="impact-review-due-date">
            Wiedervorlage
            <input
              id="impact-review-due-date"
              type="date"
              className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm font-normal text-slate-950"
              value={reviewDueDate}
              onChange={(event) => setReviewDueDate(event.target.value)}
            />
          </label>
        </div>
      </fieldset>

      <div className="mt-8 border-t border-slate-200 pt-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-slate-950">4. Acht Prüffelder mit Evidence-Proximity</p>
            <p className="mt-1 text-xs leading-5 text-slate-500">
              Öffnen Sie ein Feld für Zusammenfassung, Nachweis und Begründung.
            </p>
          </div>
          <p className="text-xs text-slate-500">
            {sections.filter((section) => section.status === "reviewed").length}/8 reviewed
          </p>
        </div>
        <div className="mt-4 divide-y divide-slate-200 border-y border-slate-200">
          {sections.map((section, index) => {
            const baseId = `impact-${section.section_key}`;
            return (
              <details key={section.section_key} className="group bg-white">
                <summary className="flex min-h-14 cursor-pointer list-none items-center justify-between gap-4 py-3 focus-visible:outline-none">
                  <span className="flex min-w-0 items-center gap-3">
                    <span className="font-mono text-[0.65rem] font-semibold text-slate-400">
                      {String(index + 1).padStart(2, "0")}
                    </span>
                    <span className="min-w-0">
                      <span className="block text-sm font-semibold text-slate-950">{section.title_de}</span>
                      <span className="mt-0.5 block text-[0.7rem] text-slate-500">{section.legal_basis}</span>
                    </span>
                  </span>
                  <span className="flex shrink-0 items-center gap-2">
                    <span className={`hidden rounded-lg px-2 py-1 text-[0.65rem] font-semibold ring-1 ring-inset sm:inline-flex ${sectionStatusClasses(section.status)}`}>
                      {sectionStatusLabel(section.status)}
                    </span>
                    <span className="text-slate-400 transition-transform group-open:rotate-180" aria-hidden>⌄</span>
                  </span>
                </summary>
                <fieldset className="pb-5 pl-0 sm:pl-8">
                  <legend className="sr-only">{section.title_de}</legend>
                  <p className="max-w-3xl text-xs leading-5 text-slate-600">{section.description_de}</p>
                  <div className="mt-4 grid gap-4 lg:grid-cols-[15rem_minmax(0,1fr)]">
                    <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-status`}>
                      Prüffeldstatus
                      <select
                        id={`${baseId}-status`}
                        aria-label="Prüffeldstatus"
                        className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
                        value={section.status}
                        onChange={(event) => updateSection(section.section_key, { status: event.target.value as ImpactSectionStatusDto })}
                      >
                        {SECTION_STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                      </select>
                    </label>
                    <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-evidence`}>
                      Evidenzreferenz
                      <input
                        id={`${baseId}-evidence`}
                        aria-label="Evidenzreferenz"
                        className="mt-1 block min-h-11 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal text-slate-950"
                        value={section.evidence_reference ?? ""}
                        maxLength={1024}
                        onChange={(event) => updateSection(section.section_key, { evidence_reference: event.target.value })}
                        placeholder="Evidence-Bundle-, Dokument- oder kontrollierte Vorgangs-ID"
                      />
                    </label>
                  </div>
                  <div className="mt-4 grid gap-4 lg:grid-cols-2">
                    <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-summary`}>
                      Fachliche Zusammenfassung
                      <textarea
                        id={`${baseId}-summary`}
                        aria-label="Fachliche Zusammenfassung"
                        className="mt-1 block min-h-28 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal leading-5 text-slate-950"
                        value={section.summary ?? ""}
                        maxLength={8000}
                        onChange={(event) => updateSection(section.section_key, { summary: event.target.value })}
                        placeholder="Prüfgegenstand, Annahmen, Befund und kontrollierte Einsatzgrenze"
                      />
                    </label>
                    <label className="text-xs font-semibold text-slate-700" htmlFor={`${baseId}-rationale`}>
                      Begründung und Review-Notiz
                      <textarea
                        id={`${baseId}-rationale`}
                        aria-label="Begründung und Review-Notiz"
                        className="mt-1 block min-h-28 w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm font-normal leading-5 text-slate-950"
                        value={section.rationale ?? ""}
                        maxLength={4000}
                        onChange={(event) => updateSection(section.section_key, { rationale: event.target.value })}
                        placeholder="Risikobezug, Prüfmethode, Ausnahme oder Abhilfebedarf"
                      />
                    </label>
                  </div>
                </fieldset>
              </details>
            );
          })}
        </div>
      </div>

      <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-5">
        <p className="text-xs text-slate-500">
          Aktuelle Version: v{assessment.version} · konfliktgeschütztes Speichern · Audit-Event
        </p>
        <button
          type="button"
          className={CH_BTN_PRIMARY}
          disabled={saving}
          aria-busy={saving}
          onClick={() => void save()}
        >
          {saving ? "Assessment wird gespeichert…" : "Assessment speichern"}
        </button>
      </div>
      <div aria-live="polite" aria-atomic="true">
        {error ? (
          <p role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-900">
            {error}
          </p>
        ) : null}
        {message ? (
          <p role="status" className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900">
            {message}
          </p>
        ) : null}
      </div>
    </section>
  );
}
