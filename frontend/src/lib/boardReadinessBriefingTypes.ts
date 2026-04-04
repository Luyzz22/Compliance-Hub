/**
 * Wave 35 – Board Readiness Briefing (structured narrative from dashboard data).
 */

import type { BoardReadinessPillarKey, BoardReadinessTraffic } from "@/lib/boardReadinessTypes";

/** Template outline (documentation + UI legend). */
export const BOARD_READINESS_BRIEFING_OUTLINE_DE: readonly {
  id: string;
  title_de: string;
  purpose_de: string;
}[] = [
  {
    id: "executive_summary",
    title_de: "Executive Summary",
    purpose_de:
      "Gesamt-Ampel, Säulen auf einen Blick, optional Delta zur letzten gespeicherten Baseline (kein Rechtsurteil).",
  },
  {
    id: "pillar_overview",
    title_de: "Säulenüberblick",
    purpose_de: "EU AI Act, ISO 42001, NIS2, DSGVO – jeweils 2–3 faktenbasierte Kernaussagen aus Indikatoren.",
  },
  {
    id: "attention_high_risk",
    title_de: "High-Risk / Attention Items",
    purpose_de: "Top-Lücken aus dem Dashboard mit Referenz-IDs für Rückverfolgung in UI/API.",
  },
  {
    id: "gtm_governance",
    title_de: "GTM vs. Governance",
    purpose_de: "Wo Nachfrage (30-Tage-Fenster) und Readiness auseinanderlaufen – und wo Governance vor Demand liegt.",
  },
  {
    id: "next_priorities",
    title_de: "Nächste Governance-Prioritäten",
    purpose_de: "1–3 konkrete nächste Schritte (Aktion, Owner-Platzhalter, Zeithorizont) – zur Freitext-Bearbeitung außerhalb der App.",
  },
] as const;

export type BriefingReference = {
  /** Stable tag, e.g. HR-AI-credit-scoring-v1 */
  ref_id: string;
  context_de: string;
};

export type BoardReadinessBriefingSection = {
  id: string;
  heading_de: string;
  bullets: string[];
  /** Evidence-style anchors for audit trail */
  references?: BriefingReference[];
};

export type BoardReadinessBriefingPayload = {
  generated_at: string;
  source_board_readiness_generated_at: string;
  outline_version: "wave35-v1";
  sections: BoardReadinessBriefingSection[];
  markdown_de: string;
  /** German sentences; empty if no baseline file */
  delta_bullets_de: string[];
  baseline_saved_at: string | null;
  meta_de: {
    mapped_tenant_count: number;
    backend_reachable: boolean;
    attention_items_included: number;
  };
};

export type BoardReadinessBriefingBaselineFile = {
  saved_at: string;
  source_board_readiness_generated_at: string;
  overall_status: BoardReadinessTraffic;
  pillar_status: Record<BoardReadinessPillarKey, BoardReadinessTraffic>;
  red_attention_count: number;
  amber_attention_count: number;
  attention_total: number;
};
