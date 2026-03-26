/**
 * Board-taugliche deutsche Texte: Governance-Maturity (Readiness, GAI, OAMI).
 * Einheitliche Begriffe für Board, CISO, Aufsichtsrat und Berater (DACH).
 *
 * Referenz für Redaktion: docs/governance-maturity-copy-de.md
 */

/** Produktbezeichnung in der UI (nicht übersetzen: etabliertes Marken-Element). */
export const READINESS_PRODUCT_TITLE = "AI & Compliance Readiness";

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
  "Hinweis: In der Spalte „Readiness“ sehen Sie den strukturellen AI- & Compliance-Readiness-Score (0–100). Governance-Aktivität (GAI) und operativer KI-Monitoring-Index (OAMI) je Mandant finden Sie im Governance-Snapshot.";

/** Spalten-Header (kurz). */
export const PORTFOLIO_COL_READINESS = "Readiness";

export const PORTFOLIO_COL_READINESS_TOOLTIP = `${READINESS_TOOLTIP_C_LEVEL} ${READINESS_REG_HINT_SHORT}`;

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

/** Readiness-Level (API: basic | managed | embedded). */
export function readinessLevelLabelDe(level: string): string {
  switch (level) {
    case "basic":
      return "Basis";
    case "managed":
      return "Etabliert";
    case "embedded":
      return "Integriert";
    default:
      return level;
  }
}

/** GAI / OAMI Level (API: low | medium | high). */
export function indexLevelLabelDe(level: string | null | undefined): string {
  if (!level) return "–";
  switch (String(level).toLowerCase()) {
    case "low":
      return "Niedrig";
    case "medium":
      return "Mittel";
    case "high":
      return "Hoch";
    default:
      return level;
  }
}
