/**
 * Zentrale deutschsprachige Texte für Governance Maturity (Readiness, GAI, OAMI).
 *
 * **Konvention:** Alle sichtbaren Board-/Berater-Strings zu diesen Themen kommen aus diesem Modul
 * (keine parallelen Inline-Literals in Komponenten). Anpassungen nur hier vornehmen.
 *
 * Inhaltliche Abstimmung mit dem Demo-Script: `docs/demo-board-ready-walkthrough.md`
 * Begriffstabelle: `docs/governance-maturity-copy-de.md`
 * Backend/API-Enums & LLM-Vertrag: `docs/governance-maturity-copy-contract.md`
 *
 * Level-Typen: `governanceMaturityTypes.ts` — Parser/Helper unten für konsistente Labels.
 */

import type { ActivityLevel, IndexLevel, MonitoringLevel, ReadinessLevel } from "@/lib/governanceMaturityTypes";
import {
  INDEX_LEVEL_API_VALUES,
  READINESS_LEVEL_API_VALUES,
} from "@/lib/governanceMaturityTypes";

/** Produktbezeichnung in der UI (nicht übersetzen: etabliertes Marken-Element). */
export const READINESS_PRODUCT_TITLE = "AI & Compliance Readiness";

/** Zeile unter dem Score: „Reifegrad: …“. */
export const READINESS_LEVEL_ROW_LABEL = "Reifegrad:";

/** Kurz erklärt, was der Score misst (Unterzeile / Fließtext). */
export const READINESS_TAGLINE =
  "Strukturelle Reife von Aufbau, Framework-Abdeckung, KPI-Register, Lücken und Board-Reporting – unabhängig von der Tagesnutzung der Plattform.";

/** Ein Satz für Tooltip / Hover (C-Level). */
export const READINESS_TOOLTIP_C_LEVEL =
  "Misst, wie gut KI-Governance dokumentiert und abgesichert ist: EU AI Act (u. a. Risiko, Nachweise, Art. 9–15), ISO/IEC 42001 (KI-Managementsystem) und ISMS (ISO/IEC 27001), mit Anknüpfung an NIS2 über Nachweise und Steuerung.";

/** Optional zweiter Satz (Berater-Detail, Snapshot). */
export const READINESS_ADVISOR_DETAIL_EXTRA =
  "Nicht identisch mit dem EU-AI-Act-Readiness-Badge in der Portfolio-Spalte (dort: heuristischer Registerüberblick).";

/** Kurzer Regulierungs-Footer für Tooltips. */
export const READINESS_REG_HINT_SHORT =
  "Regulatorik: EU AI Act Art. 9–15, ISO/IEC 42001, ISO/IEC 27001; NIS2-Anschluss über Governance und Incident-Prozesse.";

export const GAI_FULL_NAME = "Governance-Aktivitätsindex (GAI)";

export const GAI_TOOLTIP_C_LEVEL =
  "Zeigt, ob Playbook, Cross-Regulation, Board-Reports und Register in ComplianceHub tatsächlich genutzt werden – Unterscheidung von reiner Papier-Compliance.";

export const GAI_ADVISOR_DETAIL_EXTRA =
  "Hilft bei Audit- und Board-Vorbereitung: nachvollziehbare Aktivität statt nur dokumentierter Prozesse.";

export const GAI_REG_HINT_SHORT =
  "Steht für nachweisbare Steuerungsaktivität; unterstützt Aufsichts- und Prüfungsgespräche, ersetzt keine Prüfung.";

export const OAMI_FULL_NAME = "Operativer KI-Monitoring-Index (OAMI)";

export const OAMI_TOOLTIP_C_LEVEL =
  "Bündelt technische Laufzeit-Signale (Vorfälle, Schwellen, Deployments) aus dem KI-Betrieb – ohne Rohdaten aus Modellen oder personenbezogene Inhalte.";

export const OAMI_ADVISOR_DETAIL_EXTRA =
  "Unterstützt Gespräche zu Post-Market-Monitoring und NIS2-relevantem Incident-Management; keine automatische Qualifikation von Meldepflichten.";

export const OAMI_REG_HINT_SHORT =
  "Bezug: EU AI Act Post-Market-Monitoring (Art. 72), NIS2 zu Erkennung und Steuerung von Vorfällen.";

/** Abschnittstitel Snapshot / Board (90-Tage-Fenster). */
export const OAMI_SECTION_TITLE = "Operativer KI-Monitoring-Index (OAMI, 90 Tage)";

/** Hinweis unter OAMI in Demos (Snapshot). */
export const OAMI_DEMO_SIGNALS_NOTE =
  "In Demos typischerweise synthetische Signale – keine Anbindung an Produktiv-SAP.";

/** Demomandant: Board-Report-Banner (ein Absatz). */
export const DEMO_BANNER_BOARD_REPORT =
  "Demomandant (read-only): keine produktiven Änderungen. Alle Werte sind Beispieldaten ohne echten Betrieb. Sie dienen EU-AI-Act-, NIS2- und ISO-Gesprächen; vorgefüllte Reports ansehen und exportieren – neue KI-Generierung ist deaktiviert.";

/** Demomandant: Readiness-Karte. */
export const DEMO_HINT_READINESS_CARD =
  "Demomandant – Beispielwerte, keine echten Betriebsdaten. Dieser Score beschreibt die strukturelle KI-Compliance-Reife (EU AI Act, ISO/IEC 42001 und 27001, Nachweise). Governance-Aktivität (GAI) und Laufzeit-Signale (OAMI) zeigen Board-Report und Governance-Snapshot.";

/** Nach erfolgreichem Demo-Seed (Setup-Panel). */
export const DEMO_SEED_SUCCESS_GOVERNANCE_NOTE =
  "Zusätzlich werden synthetische Daten für den Governance-Aktivitätsindex (GAI) und den operativen KI-Monitoring-Index (OAMI) erzeugt. Internes Walkthrough: docs/demo-board-ready-walkthrough.md.";

/** Portfolio: Hinweis unter Überschrift / vor Tabelle. */
export const PORTFOLIO_GOVERNANCE_MATURITY_NOTE =
  "Hinweis: In der Spalte „Readiness“ sehen Sie den strukturellen AI- & Compliance-Readiness-Score (0–100). Spalten Governance-Aktivität und Operatives Monitoring zeigen GAI- und OAMI-Level; Details im Governance-Snapshot.";

/** Spalten-Header (kurz). */
export const PORTFOLIO_COL_READINESS = "Readiness";

export const PORTFOLIO_COL_READINESS_TOOLTIP = `${READINESS_TOOLTIP_C_LEVEL} ${READINESS_REG_HINT_SHORT}`;

/** Portfolio: GAI-Spalte (Kurzform). */
export const PORTFOLIO_COL_GAI_SHORT = "Governance-Aktivität";

export const PORTFOLIO_COL_GAI_TOOLTIP = `${GAI_TOOLTIP_C_LEVEL} ${GAI_REG_HINT_SHORT}`;

/** Portfolio: OAMI-Spalte (Kurzform). */
export const PORTFOLIO_COL_OAMI_SHORT = "Operatives Monitoring";

export const PORTFOLIO_COL_OAMI_TOOLTIP = `${OAMI_TOOLTIP_C_LEVEL} Sicherheitsnahe Laufzeit-Subtypen zählen im Index stärker als reine Verfügbarkeit (ohne angezeigte Gewichte). ${OAMI_REG_HINT_SHORT}`;

export const PORTFOLIO_COL_EU_AI_ACT = "EU AI Act (Register)";

export const PORTFOLIO_COL_EU_AI_ACT_TOOLTIP =
  "Heuristischer Überblick aus KI-Register und Klassifikation – nicht identisch mit dem strukturellen Readiness-Score (fünf Dimensionen).";

/** Fünf Dimensionen – Überschrift über Balken. */
export const READINESS_FIVE_DIMS_CAPTION =
  "Fünf Dimensionen der strukturellen Reife (operative KI-Laufzeit = OAMI)";

export const READINESS_DIM_SETUP = "Aufbau & Rollen";
export const READINESS_DIM_SETUP_HINT =
  "Wizard, Rollen, Framework-Scopes – u. a. ISO/IEC 42001 (KI-MS) und NIS2-Bezug im Setup.";

export const READINESS_DIM_COVERAGE = "Framework-Abdeckung";
export const READINESS_DIM_COVERAGE_HINT =
  "Abdeckung EU AI Act, NIS2, ISO/IEC 27001/42001 im Compliance-Graphen.";

export const READINESS_DIM_KPIS = "KPI-Register";
export const READINESS_DIM_KPIS_HINT =
  "Zeitreihen zu Drift, Incidents u. a. – Anschluss an Hochrisiko-Systeme.";

export const READINESS_DIM_GAPS = "Regulatorische Lücken";
export const READINESS_DIM_GAPS_HINT =
  "Sichtbare Lücken zu Pflichten des EU AI Act und weiterer Frameworks.";

export const READINESS_DIM_REPORTING = "Board-Reporting";
export const READINESS_DIM_REPORTING_HINT =
  "Berichte für Vorstand, Aufsichtsrat und Prüfer – Transparenz der Governance.";

const READINESS_LEVEL_LABEL_DE: Record<ReadinessLevel, string> = {
  basic: "Basis",
  managed: "Etabliert",
  embedded: "Integriert",
};

const INDEX_LEVEL_LABEL_DE: Record<IndexLevel, string> = {
  low: "Niedrig",
  medium: "Mittel",
  high: "Hoch",
};

export function parseReadinessLevel(raw: string | null | undefined): ReadinessLevel | null {
  if (raw == null || raw === "") return null;
  const v = String(raw).toLowerCase().trim();
  return (READINESS_LEVEL_API_VALUES as readonly string[]).includes(v)
    ? (v as ReadinessLevel)
    : null;
}

export function parseIndexLevel(raw: string | null | undefined): IndexLevel | null {
  if (raw == null || raw === "") return null;
  const v = String(raw).toLowerCase().trim();
  return (INDEX_LEVEL_API_VALUES as readonly string[]).includes(v) ? (v as IndexLevel) : null;
}

/** Tooltip-Text für Readiness-Badge in der Portfolio-Tabelle (ohne numerischen Score). */
export function readinessPortfolioBadgeTooltip(levelApi: string): string {
  const p = parseReadinessLevel(levelApi);
  const label = p ? getReadinessCopy(p).levelLabelDe : levelApi;
  return `Reifegrad ${label} (0–100). ${READINESS_REG_HINT_SHORT}`;
}

export function getReadinessCopy(level: ReadinessLevel) {
  return {
    levelLabelDe: READINESS_LEVEL_LABEL_DE[level],
    productTitle: READINESS_PRODUCT_TITLE,
    tagline: READINESS_TAGLINE,
    cLevelTooltip: READINESS_TOOLTIP_C_LEVEL,
    regHintShort: READINESS_REG_HINT_SHORT,
    /** Kurz-Tooltip nur für das Level-Badge (Readiness-Karte / Snapshot). */
    levelWithRegTooltip: `${READINESS_LEVEL_LABEL_DE[level]} — ${READINESS_REG_HINT_SHORT}`,
  };
}

export function getActivityCopy(level: ActivityLevel) {
  return {
    levelLabelDe: INDEX_LEVEL_LABEL_DE[level],
    fullName: GAI_FULL_NAME,
    cLevelTooltip: GAI_TOOLTIP_C_LEVEL,
    advisorExtra: GAI_ADVISOR_DETAIL_EXTRA,
    regHintShort: GAI_REG_HINT_SHORT,
    columnHeaderShort: PORTFOLIO_COL_GAI_SHORT,
    columnTooltip: PORTFOLIO_COL_GAI_TOOLTIP,
  };
}

export function getMonitoringCopy(level: MonitoringLevel) {
  return {
    levelLabelDe: INDEX_LEVEL_LABEL_DE[level],
    fullName: OAMI_FULL_NAME,
    sectionTitle: OAMI_SECTION_TITLE,
    cLevelTooltip: OAMI_TOOLTIP_C_LEVEL,
    advisorExtra: OAMI_ADVISOR_DETAIL_EXTRA,
    regHintShort: OAMI_REG_HINT_SHORT,
    columnHeaderShort: PORTFOLIO_COL_OAMI_SHORT,
    columnTooltip: PORTFOLIO_COL_OAMI_TOOLTIP,
  };
}

/** Readiness-Level (API: basic | managed | embedded). */
export function readinessLevelLabelDe(level: string): string {
  const p = parseReadinessLevel(level);
  return p ? getReadinessCopy(p).levelLabelDe : level;
}

/** GAI / OAMI Level (API: low | medium | high). */
export function indexLevelLabelDe(level: string | null | undefined): string {
  if (level == null || level === "") return "–";
  const p = parseIndexLevel(level);
  return p ? INDEX_LEVEL_LABEL_DE[p] : String(level);
}

export type { ActivityLevel, IndexLevel, MonitoringLevel, ReadinessLevel } from "@/lib/governanceMaturityTypes";
export {
  INDEX_LEVEL_API_VALUES,
  READINESS_LEVEL_API_VALUES,
} from "@/lib/governanceMaturityTypes";
