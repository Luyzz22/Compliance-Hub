export type DemoGuideStep = {
  id: string;
  title: string;
  hint: string;
  /** Statische Route oder Präfix für Step-Matching */
  path: string;
  /** Ersten Hochrisiko-Eintrag aus dem Register auflösen */
  resolveHighRiskSystem?: boolean;
};

export const DEMO_GUIDE_STEPS: DemoGuideStep[] = [
  {
    id: "readiness",
    title: "AI & Compliance Readiness Score",
    hint: "Zeigen Sie den gewichteten Reifegrad aus Setup, Coverage, KPIs, Gaps und Reporting.",
    path: "/board/kpis",
  },
  {
    id: "playbook",
    title: "AI Governance Playbook",
    hint: "RACI, Phasen und operative Leitplanken für AI Act & ISO 42001.",
    path: "/tenant/ai-governance-playbook",
  },
  {
    id: "crossreg",
    title: "Cross-Regulation & Gap-Assist",
    hint: "Regelwerksgraph, Abdeckung und strukturierte Lücken über EU AI Act, NIS2, ISO.",
    path: "/tenant/cross-regulation-dashboard",
  },
  {
    id: "highrisk",
    title: "Hochrisiko-KI & KPIs/KRIs",
    hint: "Systemkontext, NIS2-KPIs und Performance-Kennzahlen je KI-System.",
    path: "/tenant/ai-systems",
    resolveHighRiskSystem: true,
  },
  {
    id: "boardreport",
    title: "AI Compliance Board-Report",
    hint: "Vorstands- oder Management-Report aus Coverage und Top-Gaps.",
    path: "/board/ai-compliance-report",
  },
  {
    id: "advisor",
    title: "Berater-Portfolio & Snapshot",
    hint: "Mandantenüberblick, Readiness und Governance-Snapshot für Beratungsgespräche.",
    path: "/advisor",
  },
  {
    id: "wizard",
    title: "Setup-Wizard",
    hint: "So starten neue Kunden: Frameworks, Register, KPIs und Board-Follow-up.",
    path: "/tenant/ai-governance-setup",
  },
];

export function demoStepIndexForPath(pathname: string): number | null {
  const p = pathname.split("?")[0] ?? pathname;
  for (let i = 0; i < DEMO_GUIDE_STEPS.length; i++) {
    const step = DEMO_GUIDE_STEPS[i];
    if (step.resolveHighRiskSystem && p.startsWith("/tenant/ai-systems")) {
      return i;
    }
    if (!step.resolveHighRiskSystem && (p === step.path || p.startsWith(`${step.path}/`))) {
      return i;
    }
  }
  return null;
}
