/**
 * Domain-View-Modelle für EU-AI-Act-Self-Assessment (API → UI).
 * API-Rohtypen bleiben in aiActSelfAssessmentApi.ts.
 */
import type {
  SelfAssessmentAuditEvent,
  SelfAssessmentClassification,
  SelfAssessmentSessionDetail,
  SelfAssessmentStatus,
} from "@/lib/aiActSelfAssessmentApi";

export type { SelfAssessmentSessionDetail, SelfAssessmentStatus };

export interface GovernanceAuditEventRow {
  rowKey: string;
  eventType: string;
  actor: string;
  whenDisplay: string;
  whenIso: string;
  details: string;
}

export interface ClassificationViewModel {
  riskLevel: string;
  rationale: string;
  euAiActRefs: string[];
  requiresManualReview: boolean | null;
}

export function isSelfAssessmentStatus(s: string): s is SelfAssessmentStatus {
  return s === "draft" || s === "in_review" || s === "completed";
}

export function toClassificationViewModel(
  c: SelfAssessmentClassification | null,
): ClassificationViewModel | null {
  if (!c) {
    return null;
  }
  return {
    riskLevel: c.risk_level ?? "—",
    rationale: c.rationale ?? "—",
    euAiActRefs: Array.isArray(c.eu_ai_act_refs) ? c.eu_ai_act_refs.map(String) : [],
    requiresManualReview:
      typeof c.requires_manual_review === "boolean" ? c.requires_manual_review : null,
  };
}

export function auditEventToRow(
  e: SelfAssessmentAuditEvent,
  index: number,
  formatWhen: (iso: string) => string,
): GovernanceAuditEventRow {
  const whenIso = String(e.timestamp ?? e.created_at ?? "");
  const detailsRaw = e.details ?? e.detail;
  let details = "—";
  if (detailsRaw != null) {
    details =
      typeof detailsRaw === "string" ? detailsRaw : JSON.stringify(detailsRaw as object);
  }
  return {
    rowKey: `${whenIso}-${index}`,
    eventType: String(e.event_type ?? e.type ?? "—"),
    actor: String(e.user ?? e.actor ?? e.user_id ?? "—"),
    whenIso,
    whenDisplay: whenIso ? formatWhen(whenIso) : "—",
    details,
  };
}
