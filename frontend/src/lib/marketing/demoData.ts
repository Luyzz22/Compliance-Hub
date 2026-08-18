/**
 * Demo-Datensatz für alle Produktvisualisierungen der öffentlichen Website.
 *
 * Referenzorganisation: „Musterindustrie GmbH“ — fiktiver Industriebetrieb
 * (Serienfertigung, ca. 180 Mitarbeitende, S/4HANA, NIS2-Anwendungsbereich).
 *
 * Alle Werte sind illustrativ und beschreiben eine realistische Governance-Lage,
 * keine Kundendaten und keine Zusicherung eines Prüfergebnisses.
 */

export const DEMO_ORG = {
  name: "Musterindustrie GmbH",
  profile: "Serienfertigung · 180 Mitarbeitende · 3 Standorte",
  workspace: "Konzern-Workspace",
  reportingPeriod: "Q3 2026",
  asOf: "Stand 01.09.2026",
} as const;

/* ── Frameworks ───────────────────────────────────────────────────── */

export type FrameworkId =
  | "ai-act"
  | "iso-42001"
  | "iso-27001"
  | "iso-27701"
  | "nis2"
  | "dsgvo";

export type Framework = {
  id: FrameworkId;
  short: string;
  name: string;
  /** Kurzbeschreibung des Regelungsgegenstands. */
  scope: string;
};

export const FRAMEWORKS: readonly Framework[] = [
  {
    id: "ai-act",
    short: "EU AI Act",
    name: "Verordnung (EU) 2024/1689",
    scope: "Risikoklassen, Anforderungen an Hochrisiko-KI, Transparenzpflichten",
  },
  {
    id: "iso-42001",
    short: "ISO 42001",
    name: "ISO/IEC 42001:2023",
    scope: "Managementsystem für Künstliche Intelligenz (AIMS)",
  },
  {
    id: "iso-27001",
    short: "ISO 27001",
    name: "ISO/IEC 27001:2022",
    scope: "Managementsystem für Informationssicherheit (ISMS)",
  },
  {
    id: "iso-27701",
    short: "ISO 27701",
    name: "ISO/IEC 27701:2019",
    scope: "Erweiterung für Datenschutz-Informationsmanagement (PIMS)",
  },
  {
    id: "nis2",
    short: "NIS2",
    name: "Richtlinie (EU) 2022/2555",
    scope: "Risikomanagement und Meldepflichten für wichtige Einrichtungen",
  },
  {
    id: "dsgvo",
    short: "DSGVO",
    name: "Verordnung (EU) 2016/679 · BDSG",
    scope: "Rechtmäßigkeit, Betroffenenrechte, Rechenschaftspflicht",
  },
] as const;

/* ── Board-KPIs ───────────────────────────────────────────────────── */

export const BOARD_KPIS = {
  readinessScore: 82,
  readinessDelta: 6,
  aiSystems: 27,
  aiSystemsHighRisk: 4,
  criticalFindings: 3,
  evidenceCoverage: 91,
  nis2HighRisks: 5,
  openDecisions: 3,
  actionsDueBySeptember: 7,
} as const;

/** Statusverteilung über 142 aktive Controls. */
export const CONTROL_STATUS = {
  total: 142,
  compliant: 89,
  atRisk: 37,
  actionRequired: 16,
} as const;

export const FRAMEWORK_COVERAGE: readonly {
  id: FrameworkId;
  label: string;
  coverage: number;
  controls: number;
  open: number;
}[] = [
  { id: "ai-act", label: "EU AI Act", coverage: 78, controls: 41, open: 9 },
  { id: "iso-42001", label: "ISO/IEC 42001", coverage: 71, controls: 38, open: 11 },
  { id: "iso-27001", label: "ISO/IEC 27001", coverage: 88, controls: 93, open: 11 },
  { id: "iso-27701", label: "ISO/IEC 27701", coverage: 74, controls: 31, open: 8 },
  { id: "nis2", label: "NIS2", coverage: 69, controls: 34, open: 12 },
  { id: "dsgvo", label: "DSGVO", coverage: 92, controls: 46, open: 4 },
];

/* ── Verantwortlichkeiten ─────────────────────────────────────────── */

export const OWNERS = {
  aiOwner: { name: "R. Keller", role: "AI Owner" },
  ciso: { name: "M. Brandt", role: "CISO" },
  dpo: { name: "S. Hoffmann", role: "Datenschutzbeauftragte" },
  compliance: { name: "A. Lindner", role: "Compliance Officer" },
  process: { name: "T. Weiß", role: "Process Owner Fertigung" },
  aiRisk: { name: "J. Petrova", role: "AI Risk Officer" },
} as const;

/* ── KI-System-Register ───────────────────────────────────────────── */

export type RiskClass = "hoch" | "begrenzt" | "minimal" | "gpai";
export type SystemStatus = "compliant" | "at-risk" | "action";

export type AiSystemRow = {
  id: string;
  name: string;
  domain: string;
  riskClass: RiskClass;
  riskBasis: string;
  owner: string;
  status: SystemStatus;
};

export const AI_SYSTEM_REGISTER: readonly AiSystemRow[] = [
  {
    id: "AI-014",
    name: "Bewerber-Vorauswahl",
    domain: "Personal",
    riskClass: "hoch",
    riskBasis: "Anhang III Nr. 4",
    owner: "R. Keller",
    status: "action",
  },
  {
    id: "AI-021",
    name: "Bildprüfung Sicherheitsbauteil Linie 3",
    domain: "Fertigung",
    riskClass: "hoch",
    riskBasis: "Art. 6 Abs. 1",
    owner: "T. Weiß",
    status: "at-risk",
  },
  {
    id: "AI-009",
    name: "Predictive Maintenance Presswerk",
    domain: "Instandhaltung",
    riskClass: "minimal",
    riskBasis: "keine Sonderpflicht",
    owner: "T. Weiß",
    status: "compliant",
  },
  {
    id: "AI-027",
    name: "Serviceassistent Kundenportal",
    domain: "Vertrieb",
    riskClass: "begrenzt",
    riskBasis: "Art. 50 Transparenz",
    owner: "A. Lindner",
    status: "at-risk",
  },
  {
    id: "AI-004",
    name: "M365 Copilot (Fachbereiche)",
    domain: "Verwaltung",
    riskClass: "gpai",
    riskBasis: "GPAI-Nutzung",
    owner: "M. Brandt",
    status: "compliant",
  },
  {
    id: "AI-018",
    name: "Bonitätsprüfung Privatkunden",
    domain: "Finanzen",
    riskClass: "hoch",
    riskBasis: "Anhang III Nr. 5 b",
    owner: "S. Hoffmann",
    status: "at-risk",
  },
];

export const RISK_CLASS_LABEL: Record<RiskClass, string> = {
  hoch: "Hochrisiko",
  begrenzt: "Begrenzt",
  minimal: "Minimal",
  gpai: "GPAI-Nutzung",
};

export const SYSTEM_STATUS_LABEL: Record<SystemStatus, string> = {
  compliant: "Compliant",
  "at-risk": "At Risk",
  action: "Action required",
};

/* ── Maßnahmen ────────────────────────────────────────────────────── */

export type ActionPriority = "kritisch" | "hoch" | "mittel";

export type ActionRow = {
  id: string;
  title: string;
  owner: string;
  ownerRole: string;
  due: string;
  framework: string;
  reference: string;
  priority: ActionPriority;
};

export const ACTION_PLAN: readonly ActionRow[] = [
  {
    id: "M-118",
    title: "Technische Dokumentation Bewerber-Vorauswahl vervollständigen",
    owner: "R. Keller",
    ownerRole: "AI Owner",
    due: "30.09.2026",
    framework: "EU AI Act",
    reference: "Art. 11",
    priority: "kritisch",
  },
  {
    id: "M-121",
    title: "Verfahren zur menschlichen Aufsicht Linie 3 freigeben",
    owner: "T. Weiß",
    ownerRole: "Process Owner",
    due: "15.09.2026",
    framework: "EU AI Act",
    reference: "Art. 14",
    priority: "kritisch",
  },
  {
    id: "M-097",
    title: "MFA für OT-Fernwartung ausrollen",
    owner: "M. Brandt",
    ownerRole: "CISO",
    due: "30.09.2026",
    framework: "NIS2",
    reference: "Art. 21 Abs. 2 j",
    priority: "kritisch",
  },
  {
    id: "M-103",
    title: "DSFA Bonitätsprüfung aktualisieren",
    owner: "S. Hoffmann",
    ownerRole: "Datenschutzbeauftragte",
    due: "12.09.2026",
    framework: "DSGVO",
    reference: "Art. 35",
    priority: "hoch",
  },
  {
    id: "M-110",
    title: "Meldekette unter 24 Stunden testen",
    owner: "M. Brandt",
    ownerRole: "CISO",
    due: "22.09.2026",
    framework: "NIS2",
    reference: "Art. 23",
    priority: "hoch",
  },
  {
    id: "M-126",
    title: "Vertragsklauseln für KI-Zulieferer nachziehen",
    owner: "A. Lindner",
    ownerRole: "Compliance Officer",
    due: "30.09.2026",
    framework: "ISO/IEC 42001",
    reference: "A.10.3",
    priority: "hoch",
  },
  {
    id: "M-131",
    title: "Evidenz zur Trainingsdaten-Governance nachreichen",
    owner: "R. Keller",
    ownerRole: "AI Owner",
    due: "29.09.2026",
    framework: "ISO/IEC 42001",
    reference: "A.7.4",
    priority: "mittel",
  },
];

/* ── Fristen ──────────────────────────────────────────────────────── */

export const DEADLINES: readonly {
  label: string;
  detail: string;
  inDays: number;
  tone: "warn" | "info";
}[] = [
  {
    label: "EU AI Act",
    detail: "Review Risikoklassifizierung AI-014, AI-021",
    inDays: 14,
    tone: "warn",
  },
  {
    label: "ISO/IEC 42001",
    detail: "Internes Audit AIMS, Abschnitt 9.2",
    inDays: 38,
    tone: "info",
  },
  {
    label: "NIS2",
    detail: "Nachweis Awareness-Schulung Leitungsebene",
    inDays: 52,
    tone: "info",
  },
];

/* ── Control Mapping ──────────────────────────────────────────────── */

export type MappedControl = {
  id: string;
  title: string;
  owner: string;
  ownerRole: string;
  evidence: string;
  evidenceState: "aktuell" | "in Review" | "fällig";
  reviewCycle: string;
  mappings: { framework: FrameworkId; reference: string; label: string }[];
};

export const MAPPED_CONTROLS: readonly MappedControl[] = [
  {
    id: "AI-RA-01",
    title: "KI-Risikobeurteilung",
    owner: "J. Petrova",
    ownerRole: "AI Risk Officer",
    evidence: "Risikoanalyse v3",
    evidenceState: "aktuell",
    reviewCycle: "Quartalsweise",
    mappings: [
      { framework: "ai-act", reference: "Art. 9", label: "Risikomanagementsystem" },
      { framework: "iso-42001", reference: "6.1.2 · A.5.2", label: "AI-Risikobeurteilung" },
      { framework: "iso-27001", reference: "6.1.2", label: "Risikobeurteilung" },
      { framework: "iso-27701", reference: "5.4.1.2", label: "Datenschutzrisiken" },
      { framework: "nis2", reference: "Art. 21 Abs. 2 a", label: "Risikoanalyse" },
      { framework: "dsgvo", reference: "Art. 35", label: "Datenschutz-Folgenabschätzung" },
    ],
  },
  {
    id: "LOG-02",
    title: "Protokollierung & Aufzeichnungen",
    owner: "M. Brandt",
    ownerRole: "CISO",
    evidence: "Logging-Konzept v2.1",
    evidenceState: "in Review",
    reviewCycle: "Halbjährlich",
    mappings: [
      { framework: "ai-act", reference: "Art. 12 · Art. 19", label: "Aufzeichnungspflichten" },
      { framework: "iso-42001", reference: "A.6.2.8", label: "AI-System-Protokollierung" },
      { framework: "iso-27001", reference: "A.8.15", label: "Protokollierung" },
      { framework: "iso-27701", reference: "6.9.4", label: "Protokollierung PII" },
      { framework: "nis2", reference: "Art. 21 Abs. 2 b", label: "Bewältigung von Vorfällen" },
      { framework: "dsgvo", reference: "Art. 30 · Art. 32", label: "Verzeichnis · Sicherheit" },
    ],
  },
  {
    id: "SUP-04",
    title: "Anbieter- und Lieferantenprüfung",
    owner: "A. Lindner",
    ownerRole: "Compliance Officer",
    evidence: "Lieferantenbewertung 2026",
    evidenceState: "fällig",
    reviewCycle: "Jährlich",
    mappings: [
      { framework: "ai-act", reference: "Art. 25", label: "Pflichten entlang der Wertschöpfung" },
      { framework: "iso-42001", reference: "A.10.3", label: "Lieferantenbeziehungen" },
      { framework: "iso-27001", reference: "A.5.19 – A.5.22", label: "Lieferantensicherheit" },
      { framework: "iso-27701", reference: "7.2.6", label: "Auftragsverarbeitung" },
      { framework: "nis2", reference: "Art. 21 Abs. 2 d", label: "Sicherheit der Lieferkette" },
      { framework: "dsgvo", reference: "Art. 28", label: "Auftragsverarbeiter" },
    ],
  },
  {
    id: "HO-03",
    title: "Menschliche Aufsicht",
    owner: "T. Weiß",
    ownerRole: "Process Owner",
    evidence: "Aufsichtsverfahren Linie 3",
    evidenceState: "in Review",
    reviewCycle: "Quartalsweise",
    mappings: [
      { framework: "ai-act", reference: "Art. 14", label: "Menschliche Aufsicht" },
      { framework: "iso-42001", reference: "A.9.2", label: "Verantwortlichkeiten" },
      { framework: "iso-27001", reference: "A.5.4", label: "Managementverantwortung" },
      { framework: "iso-27701", reference: "7.2.2", label: "Rollen und Zuständigkeiten" },
      { framework: "nis2", reference: "Art. 20", label: "Verantwortung der Leitungsebene" },
      { framework: "dsgvo", reference: "Art. 22", label: "Automatisierte Entscheidungen" },
    ],
  },
];

/* ── NIS2-Risiken ─────────────────────────────────────────────────── */

export type Nis2Risk = {
  id: string;
  title: string;
  reference: string;
  impact: 1 | 2 | 3 | 4 | 5;
  likelihood: 1 | 2 | 3 | 4 | 5;
  owner: string;
  treatment: string;
};

export const NIS2_RISKS: readonly Nis2Risk[] = [
  {
    id: "R-07",
    title: "Fernwartungszugang OT ohne MFA",
    reference: "Art. 21 Abs. 2 j",
    impact: 5,
    likelihood: 4,
    owner: "M. Brandt",
    treatment: "Reduzieren",
  },
  {
    id: "R-12",
    title: "Wiederanlaufverfahren MES ungetestet",
    reference: "Art. 21 Abs. 2 c",
    impact: 5,
    likelihood: 3,
    owner: "T. Weiß",
    treatment: "Reduzieren",
  },
  {
    id: "R-03",
    title: "Einzelabhängigkeit Steuerungssoftware",
    reference: "Art. 21 Abs. 2 d",
    impact: 4,
    likelihood: 4,
    owner: "A. Lindner",
    treatment: "Reduzieren",
  },
  {
    id: "R-15",
    title: "Meldekette Erstmeldung über 24 h",
    reference: "Art. 23 Abs. 4",
    impact: 4,
    likelihood: 4,
    owner: "M. Brandt",
    treatment: "Reduzieren",
  },
  {
    id: "R-09",
    title: "Schwachstellenmanagement OT-Segment",
    reference: "Art. 21 Abs. 2 e",
    impact: 4,
    likelihood: 4,
    owner: "M. Brandt",
    treatment: "Reduzieren",
  },
  {
    id: "R-21",
    title: "Kryptografie-Richtlinie nicht aktualisiert",
    reference: "Art. 21 Abs. 2 h",
    impact: 3,
    likelihood: 2,
    owner: "M. Brandt",
    treatment: "Akzeptieren (befristet)",
  },
  {
    id: "R-25",
    title: "Zugriffsrezertifizierung Fachanwendungen",
    reference: "Art. 21 Abs. 2 i",
    impact: 3,
    likelihood: 3,
    owner: "A. Lindner",
    treatment: "Reduzieren",
  },
];

/* ── Evidence ─────────────────────────────────────────────────────── */

export type EvidenceEvent = {
  date: string;
  title: string;
  actor: string;
  actorRole: string;
  detail: string;
  kind: "upload" | "review" | "approval" | "mapping" | "export";
};

export const EVIDENCE_TIMELINE: readonly EvidenceEvent[] = [
  {
    date: "02.09.2026",
    title: "Evidenz-Dossier Q3 exportiert",
    actor: "A. Lindner",
    actorRole: "Compliance Officer",
    detail: "41 Nachweise · Prüfpfad signiert · Hash 8f3c…a10",
    kind: "export",
  },
  {
    date: "28.08.2026",
    title: "Risikoanalyse v3 freigegeben",
    actor: "J. Petrova",
    actorRole: "AI Risk Officer",
    detail: "Control AI-RA-01 · nächster Review 30.11.2026",
    kind: "approval",
  },
  {
    date: "21.08.2026",
    title: "Aufsichtsverfahren Linie 3 zur Prüfung",
    actor: "T. Weiß",
    actorRole: "Process Owner",
    detail: "Control HO-03 · Review durch Compliance offen",
    kind: "review",
  },
  {
    date: "14.08.2026",
    title: "Control LOG-02 auf NIS2 Art. 21 gemappt",
    actor: "M. Brandt",
    actorRole: "CISO",
    detail: "Wiederverwendung in 4 weiteren Regimen",
    kind: "mapping",
  },
  {
    date: "07.08.2026",
    title: "Logging-Konzept v2.1 hochgeladen",
    actor: "M. Brandt",
    actorRole: "CISO",
    detail: "Ersetzt v2.0 · Vorversion bleibt referenzierbar",
    kind: "upload",
  },
];

/* ── Board-Entscheidungen ─────────────────────────────────────────── */

export const BOARD_DECISIONS: readonly {
  title: string;
  context: string;
  needed: string;
}[] = [
  {
    title: "Freigabe Bewerber-Vorauswahl (AI-014)",
    context: "Hochrisiko nach Anhang III Nr. 4 · technische Dokumentation unvollständig",
    needed: "Entscheidung über Weiterbetrieb oder befristete Aussetzung",
  },
  {
    title: "Budget MFA-Rollout OT-Fernwartung",
    context: "NIS2 Art. 21 Abs. 2 j · höchstbewertetes Risiko im Register",
    needed: "Mittelfreigabe für Umsetzung bis Q4",
  },
  {
    title: "Externe Auditbegleitung ISO/IEC 42001",
    context: "Internes Audit 9.2 terminiert · Zertifizierungsziel Q2 2027",
    needed: "Beauftragung und Terminfenster bestätigen",
  },
];

/* ── Integrationen ────────────────────────────────────────────────── */

export type IntegrationGroup = {
  id: string;
  title: string;
  purpose: string;
  items: { name: string; note: string }[];
};

export const INTEGRATION_GROUPS: readonly IntegrationGroup[] = [
  {
    id: "erp",
    title: "ERP & Finance",
    purpose: "Stammdaten, Prozessbezug und Auswertungen aus der führenden Systemwelt.",
    items: [
      { name: "SAP S/4HANA", note: "Organisations- und Prozessstammdaten" },
      { name: "SAP BTP", note: "Serviceanbindung und Erweiterungen" },
      { name: "Microsoft Dynamics", note: "Alternative ERP-Landschaft" },
      { name: "DATEV-naher Export", note: "Strukturierte Übergabe an Kanzleien" },
    ],
  },
  {
    id: "identity",
    title: "Identity & Security",
    purpose: "Anmeldung, Rollenmodell und sicherheitsrelevante Signale.",
    items: [
      { name: "Microsoft Entra ID", note: "SSO und Gruppen-Mapping" },
      { name: "SAML 2.0", note: "Enterprise-Föderation" },
      { name: "SAP IAS", note: "Identitätsdienst in SAP-Landschaften" },
      { name: "SIEM", note: "Audit- und Sicherheitsereignisse" },
    ],
  },
  {
    id: "workflow",
    title: "Workflow & Engineering",
    purpose: "Maßnahmen dort abarbeiten, wo Teams ohnehin arbeiten.",
    items: [
      { name: "Jira", note: "Maßnahmen als Vorgänge synchronisieren" },
      { name: "ServiceNow", note: "Change- und Incident-Bezug" },
      { name: "Webhooks", note: "Ereignisgesteuerte Übergaben" },
      { name: "n8n", note: "Automatisierte Routineschritte" },
    ],
  },
  {
    id: "ai",
    title: "AI & Data",
    purpose: "KI-Nutzung erfassen und Datenquellen für Nachweise anbinden.",
    items: [
      { name: "Azure OpenAI", note: "Registrierte Modellnutzung" },
      { name: "Anthropic", note: "Registrierte Modellnutzung" },
      { name: "OpenAI", note: "Registrierte Modellnutzung" },
      { name: "Vertex AI", note: "Registrierte Modellnutzung" },
      { name: "Snowflake", note: "Datenquelle für Auswertungen" },
      { name: "Databricks", note: "Datenquelle für Auswertungen" },
    ],
  },
];

/* ── Ressourcen ───────────────────────────────────────────────────── */

export const RESOURCES: readonly {
  slug: string;
  kind: string;
  title: string;
  summary: string;
  readingTime: string;
  audience: string;
}[] = [
  {
    slug: "eu-ai-act-readiness-guide",
    kind: "Leitfaden",
    title: "EU AI Act Readiness Guide",
    summary:
      "Von der Systemerhebung über die Risikoklassifizierung bis zur Technical-File-Struktur: ein Arbeitsweg für Organisationen ohne eigenes AI-Governance-Team.",
    readingTime: "18 Seiten",
    audience: "Compliance, AI Owner, Geschäftsführung",
  },
  {
    slug: "iso-42001-ai-act-mapping",
    kind: "Mapping",
    title: "ISO/IEC 42001 × EU AI Act",
    summary:
      "Gegenüberstellung der AIMS-Anforderungen mit den Pflichten der KI-Verordnung, inklusive Hinweisen auf gemeinsam nutzbare Nachweise.",
    readingTime: "Referenztabelle",
    audience: "ISMS- und AIMS-Verantwortliche",
  },
  {
    slug: "nis2-management-checkliste",
    kind: "Checkliste",
    title: "NIS2 Management-Checkliste",
    summary:
      "Die zehn Risikomanagementmaßnahmen nach Art. 21 als prüfbare Fragen für Leitungsorgane, mit Zuständigkeit und typischen Nachweisen.",
    readingTime: "6 Seiten",
    audience: "Geschäftsführung, CISO",
  },
  {
    slug: "board-report-vorlage",
    kind: "Vorlage",
    title: "Board-Report-Vorlage",
    summary:
      "Struktur für ein Governance-Update an Geschäftsführung und Beirat: Lage, Risiken, Entscheidungsbedarf, Fristen — auf zwei Seiten.",
    readingTime: "Vorlage",
    audience: "Compliance, Geschäftsführung",
  },
  {
    slug: "dach-ai-governance-briefing",
    kind: "Briefing",
    title: "DACH AI Governance Briefing",
    summary:
      "Quartalsweise Einordnung zu Umsetzungsstand, nationalen Konkretisierungen und Praxisfragen aus Mittelstand und Beratung.",
    readingTime: "Quartalsformat",
    audience: "Kanzleien, Beratungen, Governance-Teams",
  },
];

/* ── Kanzlei-/Beratungsportfolio ──────────────────────────────────── */

export const ADVISOR_PORTFOLIO: readonly {
  mandant: string;
  branche: string;
  regime: string;
  readiness: number;
  open: number;
  next: string;
}[] = [
  {
    mandant: "Musterindustrie GmbH",
    branche: "Fertigung",
    regime: "AI Act · NIS2 · ISO 27001",
    readiness: 82,
    open: 3,
    next: "15.09.",
  },
  {
    mandant: "Nordwerk Logistik SE",
    branche: "Logistik",
    regime: "NIS2 · ISO 27001",
    readiness: 74,
    open: 5,
    next: "24.09.",
  },
  {
    mandant: "Vitalis Medizintechnik",
    branche: "Medizintechnik",
    regime: "AI Act · ISO 42001 · DSGVO",
    readiness: 63,
    open: 8,
    next: "08.09.",
  },
  {
    mandant: "Ostheim Energie AG",
    branche: "Energie",
    regime: "NIS2 · KRITIS",
    readiness: 91,
    open: 1,
    next: "02.10.",
  },
  {
    mandant: "Hansa Chemie GmbH",
    branche: "Chemie",
    regime: "NIS2 · ISO 27701",
    readiness: 58,
    open: 11,
    next: "11.09.",
  },
];
