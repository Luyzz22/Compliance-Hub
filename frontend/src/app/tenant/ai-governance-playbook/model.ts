/**
 * Statisches UI-Modell für die AI-Governance-Playbook-Seite (kein Mandanten-RBAC).
 */

export type RaciCell = "R" | "A" | "C" | "I" | "—";

export interface RaciRole {
  id: string;
  label: string;
  short: string;
}

export const RACI_ROLES: RaciRole[] = [
  { id: "board", label: "Board / Geschäftsführung", short: "Board" },
  { id: "ciso", label: "CISO / Security Lead", short: "CISO" },
  { id: "ai_gov", label: "AI Governance Lead / AIMS-Owner", short: "AI Gov" },
  { id: "owner", label: "AI System Owner / Product Owner", short: "AI Owner" },
  { id: "dpo", label: "DPO / Datenschutzbeauftragter", short: "DPO" },
  { id: "it_ops", label: "IT Ops / Plattform", short: "IT Ops" },
  { id: "advisor", label: "Berater / Kanzlei / GRC-Boutique", short: "Berater" },
];

export interface RaciRow {
  id: string;
  task: string;
  ref: string;
  cells: Record<string, RaciCell>;
}

/** RACI nach typischen ISO-42001-/AI-Governance-Mustern (eine Zelle pro Rolle). */
export const RACI_ROWS: RaciRow[] = [
  {
    id: "inventory",
    task: "AI-System-Inventar & Klassifikation",
    ref: "EU AI Act Art. 6, Anhang III",
    cells: {
      board: "I",
      ciso: "C",
      ai_gov: "A",
      owner: "R",
      dpo: "C",
      it_ops: "R",
      advisor: "C",
    },
  },
  {
    id: "nis2",
    task: "NIS2-/KRITIS-Umsetzung",
    ref: "Risikoanalyse, Maßnahmen, Incident-Prozesse",
    cells: {
      board: "I",
      ciso: "A",
      ai_gov: "R",
      owner: "C",
      dpo: "C",
      it_ops: "R",
      advisor: "C",
    },
  },
  {
    id: "annex_iv",
    task: "AI-Act-Dokumentation (Technical File)",
    ref: "Anhang IV EU AI Act",
    cells: {
      board: "I",
      ciso: "C",
      ai_gov: "A",
      owner: "R",
      dpo: "C",
      it_ops: "C",
      advisor: "R",
    },
  },
  {
    id: "policies",
    task: "Policies & Governing Documents",
    ref: "AI-Policy, Data Governance, ISMS/DSMS",
    cells: {
      board: "I",
      ciso: "A",
      ai_gov: "R",
      owner: "C",
      dpo: "R",
      it_ops: "C",
      advisor: "C",
    },
  },
  {
    id: "evidence",
    task: "Evidence & Audits",
    ref: "Nachweise, Board-Reports, Notified Body / WP",
    cells: {
      board: "I",
      ciso: "R",
      ai_gov: "A",
      owner: "R",
      dpo: "C",
      it_ops: "C",
      advisor: "C",
    },
  },
  {
    id: "ppm",
    task: "Post-Market-Monitoring & Incident-Handling",
    ref: "EU AI Act Art. 72, NIS2",
    cells: {
      board: "I",
      ciso: "A",
      ai_gov: "R",
      owner: "R",
      dpo: "C",
      it_ops: "R",
      advisor: "C",
    },
  },
];

export interface PlaybookTaskLink {
  label: string;
  href: string;
  hint?: string;
}

export interface PlaybookPhase {
  id: string;
  stage: string;
  title: string;
  horizon: string;
  badges: string[];
  description: string;
  goals: string[];
  tasks: PlaybookTaskLink[];
}

export const PLAYBOOK_PHASES: PlaybookPhase[] = [
  {
    id: "stage1",
    stage: "Stage 1",
    title: "Compliance Readiness",
    horizon: "z. B. 3–6 Monate",
    badges: ["Pflichtbasis High-Risk bis 08/2026", "EU AI Act"],
    description:
      "Fundament für High-Risk-Systeme: Inventar, erste KPIs und Readiness-Transparenz – ausgerichtet auf die vollständige Anwendbarkeit des EU AI Act ab August 2026.",
    goals: [
      "Vollständiges AI-System-Inventar und Klassifikation",
      "Erste NIS2-/KRITIS-KPIs und Policies",
      "EU-AI-Act-Readiness-KPIs und initiale Lücken",
    ],
    tasks: [
      {
        label: "AI-Systeme importieren & klassifizieren",
        href: "/tenant/ai-systems",
        hint: "Guided Setup Schritte 1–2; Register und EU-AI-Act-Cockpit",
      },
      {
        label: "NIS2-/KRITIS-Basiskennzahlen setzen",
        href: "/tenant/ai-systems",
        hint: "Je System unter „Detail“ NIS2-/KRITIS-KPIs; KI-Assist für Vorschläge",
      },
      { label: "Kern-Policies anlegen", href: "/tenant/policies" },
      { label: "Readiness-Dashboard prüfen", href: "/board/eu-ai-act-readiness" },
    ],
  },
  {
    id: "stage2",
    stage: "Stage 2",
    title: "Operational Compliance",
    horizon: "z. B. 6–12 Monate",
    badges: ["NIS2 in Kraft ohne Übergangsfrist", "Betrieb & Automatisierung"],
    description:
      "Risikomanagement und Dokumentation laufen im Alltag: Annex-IV-Unterlagen, verknüpfte Actions und belastbare Evidenzen für Vorstand und Prüfer.",
    goals: [
      "Risikomanagement-Prozess operativ (Art. 9 EU AI Act, ISO 42001)",
      "Technische Dokumentation (Anhang IV) für High-Risk-Systeme",
      "Integrierte NIS2-/AI-Incident-Prozesse",
    ],
    tasks: [
      {
        label: "AI-Act-Dokumentation pro System",
        href: "/tenant/ai-systems",
        hint: "System wählen → Tab „EU AI Act Dokumentation“, KI-Entwürfe nutzen",
      },
      {
        label: "Governance-Actions aus Gaps ableiten",
        href: "/board/eu-ai-act-readiness",
        hint: "Readiness-Seite, Action-Entwürfe (KI) nutzen",
      },
      {
        label: "Evidence-Pakete aufbauen",
        href: "/tenant/ai-systems",
        hint: "Evidenz je System / Maßnahme: DPIA, Runbooks, Verträge",
      },
      {
        label: "Board-Reports & Advisor-Reports",
        href: "/board/kpis",
        hint: "KPI-Board; Berater: /advisor und Mandanten-Steckbrief",
      },
    ],
  },
  {
    id: "stage3",
    stage: "Stage 3",
    title: "Compliance Excellence",
    horizon: "12+ Monate",
    badges: ["Cross-Regulation", "Prüfungsreife"],
    description:
      "Mehrmandanten- und regulatorische Querschnitte steuern, Szenarien für Investitionen nutzen und Audit-Pakete vorbereiten (Notified Body, WP, Aufsicht).",
    goals: [
      "Cross-Regulation-Dashboard (AI Act, NIS2, ISO 27001/42001)",
      "What-if-Szenarien und laufende Optimierung",
      "Vorbereitung Notified Body / WP / BaFin / BSI",
    ],
    tasks: [
      {
        label: "What-if-Simulation (Board-KPI-Impact)",
        href: "/board/kpis",
        hint: "Auf der KPI-Seite: What-if-Simulator (wenn aktiviert)",
      },
      {
        label: "Advisor-Portfolio & Steckbriefe",
        href: "/advisor",
        hint: "Für Berater-Mandanten: Portfolio und Mandanten-Steckbrief",
      },
      {
        label: "Dokumentationspakete exportieren",
        href: "/tenant/ai-systems",
        hint: "EU-AI-Act-Doku je System exportieren; Steckbrief über Advisor-Report",
      },
    ],
  },
];

export interface PilotWeek {
  week: string;
  title: string;
  bullets: string[];
  links: PlaybookTaskLink[];
}

export const PILOT_WEEKS: PilotWeek[] = [
  {
    week: "Woche 1",
    title: "Inventar & Klassifikation",
    bullets: [
      "Guided Setup starten, KI-Systeme erfassen und grob klassifizieren.",
      "Optional: Demo-Template einspielen (nur Demo-Allowlist).",
    ],
    links: [
      { label: "Compliance-Übersicht / Setup", href: "/tenant/compliance-overview" },
      { label: "KI-Register", href: "/tenant/ai-systems" },
    ],
  },
  {
    week: "Woche 2",
    title: "KPIs & Policies",
    bullets: [
      "NIS2-/KRITIS-KPIs in den System-Details pflegen.",
      "KI-Assist für KPI-Vorschläge und spätere Action-Entwürfe einplanen.",
    ],
    links: [
      { label: "Policies", href: "/tenant/policies" },
      { label: "Board KPIs", href: "/board/kpis" },
    ],
  },
  {
    week: "Woche 3",
    title: "AI-Act-Doku & Evidence",
    bullets: [
      "Annex-IV-Bausteine für High-Risk-Systeme entwerfen.",
      "Nachweise an Systeme und Maßnahmen hängen.",
    ],
    links: [
      { label: "KI-Register (Detail)", href: "/tenant/ai-systems" },
      { label: "EU AI Act Readiness", href: "/board/eu-ai-act-readiness" },
    ],
  },
  {
    week: "Woche 4",
    title: "Board-Demo",
    bullets: [
      "Vorstandstaugliche KPIs und What-if-Szenario zeigen.",
      "Bei Beratern: Advisor-Report / Steckbrief mitnehmen.",
    ],
    links: [
      { label: "Board KPIs", href: "/board/kpis" },
      { label: "Advisor-Workspace", href: "/advisor" },
      { label: "Workspace-Start", href: "/tenant/compliance-overview" },
    ],
  },
];
