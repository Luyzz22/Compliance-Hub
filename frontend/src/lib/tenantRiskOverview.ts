/**
 * Mandanten-weites „Risk & Control Overview“ (Frontend-ViewModel).
 * Aggregiert EU AI Act, NIS2/KRITIS (Block 3) und später ISO/Controls (Block 2).
 */

export type Nis2ExposureLevel = "low" | "medium" | "high";

/** Kundenfreundliche Kategorie (Mapping aus Score/Profil, keine Behördenfeststellung). */
export type Nis2ExposureCategory = "not_likely" | "maybe" | "very_likely";

export type AiActRiskBand = "HIGH" | "LIMITED" | "MINIMAL" | "UNKNOWN";

export interface AiActSystemRiskRow {
  ai_system_id: string;
  display_name: string;
  risk_level: AiActRiskBand;
  /** Letzter bekannter Self-Assessment-Status (draft / in_review / completed / …). */
  self_assessment_status: string;
  /** Deep-Link in den Self-Assessment-Run, sobald Backend session_id liefert (TODO). */
  self_assessment_href?: string | null;
}

export interface TenantRiskOverview {
  tenant_id: string;
  generated_at: string;

  aiSystemsTotal: number;
  aiHighRiskCount: number;
  aiLimitedRiskCount: number;
  aiMinimalRiskCount: number;
  /**
   * Offene Governance-Pflichten / Self-Assessments (heuristisch: nicht completed oder
   * fehlende Nachweise). TODO Backend: aus self_assessments + evidence_tasks aggregieren.
   */
  aiActOpenActionsCount: number;

  nis2InScopeScore: number;
  nis2ExposureLevel: Nis2ExposureLevel;
  nis2ExposureCategory: Nis2ExposureCategory;

  /** Block 2 — Platzhalter bis ISO-/Control-Register angebunden ist. */
  isoControlsImplemented: number;
  isoControlsPlanned: number;

  topRiskAiSystems: AiActSystemRiskRow[];
  derivedTodos: string[];
}

function exposureCategoryFromScore(score: number, level: Nis2ExposureLevel): Nis2ExposureCategory {
  if (level === "high" || score >= 72) {
    return "very_likely";
  }
  if (level === "medium" || score >= 40) {
    return "maybe";
  }
  return "not_likely";
}

function buildDummyTodos(o: TenantRiskOverview): string[] {
  const items: string[] = [];
  if (o.nis2ExposureLevel === "high") {
    items.push("NIS2-Exposure hoch → NIS2-Basiskontrollen und Lieferketten-Dokumentation priorisieren.");
  } else if (o.nis2ExposureLevel === "medium") {
    items.push("NIS2-Exposure mittel → Rechts- und Prozesscheck mit Fachbereich; Wizard erneut fahren.");
  }
  if (o.aiHighRiskCount >= 1) {
    items.push(
      `${o.aiHighRiskCount} KI-System(e) mit HIGH Risk → Technical File, Logging und PMS (Post-Market Surveillance) planen.`,
    );
  }
  if (o.aiActOpenActionsCount > 0) {
    items.push(
      `${o.aiActOpenActionsCount} offene AI-Act-Maßnahme(n) / Self-Assessments abschließen und evidenzieren.`,
    );
  }
  if (o.isoControlsPlanned > 0) {
    items.push(
      `${o.isoControlsPlanned} geplante ISO-/Controls (Block 2) — Umsetzung mit Security & Compliance abstimmen.`,
    );
  }
  if (items.length === 0) {
    items.push("Keine kritischen Heuristiken — regelmäßiges Monitoring und Dokumentation beibehalten.");
  }
  return items;
}

/**
 * Lädt aggregiertes Risiko-/Control-Overview für einen Mandanten.
 *
 * TODO Backend (Beispiel-Queries, nicht implementiert):
 * 1) AI-Act / KI-Register: COUNT/GROUP BY risk_level aus `ai_systems` bzw. letzter Klassifikation;
 *    JOIN `self_assessments` für Status pro System.
 * 2) Offene Maßnahmen: COUNT wo self_assessment.status != 'completed' ODER offene evidence_tasks.
 * 3) NIS2: aus `nis2_profiles` / letzter `nis2_assessment_sessions` + berechneter InScope-Score
 *    (serverseitig wie Frontend-Heuristik in nis2InScopeScore.ts).
 * 4) ISO (Block 2): implemented/planned aus control_implementations / roadmap.
 */
export async function fetchTenantRiskOverview(tenantId: string): Promise<TenantRiskOverview> {
  await Promise.resolve();

  const nis2Score = 68;
  const nis2Level: Nis2ExposureLevel = nis2Score >= 72 ? "high" : nis2Score >= 42 ? "medium" : "low";

  const overview: TenantRiskOverview = {
    tenant_id: tenantId,
    generated_at: new Date().toISOString(),
    aiSystemsTotal: 12,
    aiHighRiskCount: 3,
    aiLimitedRiskCount: 5,
    aiMinimalRiskCount: 4,
    aiActOpenActionsCount: 7,
    nis2InScopeScore: nis2Score,
    nis2ExposureLevel: nis2Level,
    nis2ExposureCategory: exposureCategoryFromScore(nis2Score, nis2Level),
    isoControlsImplemented: 42,
    isoControlsPlanned: 18,
    topRiskAiSystems: [
      {
        ai_system_id: "sys-hr-scoring",
        display_name: "HR Scoring Engine",
        risk_level: "HIGH",
        self_assessment_status: "in_review",
        self_assessment_href: null,
      },
      {
        ai_system_id: "sys-doc-ai",
        display_name: "Dokumenten-KI (Kanzlei)",
        risk_level: "HIGH",
        self_assessment_status: "draft",
        self_assessment_href: null,
      },
      {
        ai_system_id: "sys-chatbot",
        display_name: "Kunden-Chatbot",
        risk_level: "LIMITED",
        self_assessment_status: "completed",
        self_assessment_href: null,
      },
    ],
    derivedTodos: [],
  };
  overview.derivedTodos = buildDummyTodos(overview);
  return overview;
}

export function nis2ExposureCategoryLabel(de: Nis2ExposureCategory): string {
  switch (de) {
    case "very_likely":
      return "Sehr wahrscheinlich betroffen (Indikation)";
    case "maybe":
      return "Vielleicht betroffen — vertiefen";
    default:
      return "Geringere Indikation (nicht abschließend)";
  }
}
