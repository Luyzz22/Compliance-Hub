import type { LeadSegment } from "@/lib/leadCapture";

export type LeadPriority = "low" | "normal" | "high";

/** Operative SLA-Einordnung für Sales (kein SLA-Vertrag). */
export type LeadSlaBucket = "standard" | "priority" | "enterprise";

export type LeadRoute = {
  /** Stabiler Schlüssel für Automation (n8n, CRM). */
  route_key: string;
  /** Menschlich lesbare Queue / Team-Bezeichnung (DE). */
  queue_label: string;
  priority: LeadPriority;
  sla_bucket: LeadSlaBucket;
};

/**
 * Interne Routing-Heuristik – leichtgewichtig, ohne CRM.
 * Erweiterung: Keyword-Mining in `message`, CRM-Sync, Round-Robin.
 */
export function determineLeadRoute(
  segment: LeadSegment,
  company: string,
  message: string,
  source_page: string,
): LeadRoute {
  const msg = `${message} ${company} ${source_page}`.toLowerCase();

  switch (segment) {
    case "enterprise_sap":
      return {
        route_key: "queue_enterprise_sap",
        queue_label: "Enterprise / SAP – Solution & Integration",
        priority: "high",
        sla_bucket: "enterprise",
      };
    case "kanzlei_wp":
      return {
        route_key: "queue_kanzlei_wp",
        queue_label: "Kanzlei / WP – Beratung & Mandanten",
        priority: "normal",
        sla_bucket: "priority",
      };
    case "industrie_mittelstand":
      return {
        route_key: "queue_industrie_mittelstand",
        queue_label: "Industrie / Mittelstand – AI Act & NIS2",
        priority: "normal",
        sla_bucket: "standard",
      };
    case "sonstiges":
      if (/sap|btp|s\/4|s4hana|konzern/i.test(msg)) {
        return {
          route_key: "queue_enterprise_sap",
          queue_label: "Enterprise / SAP (aus Kontext)",
          priority: "high",
          sla_bucket: "enterprise",
        };
      }
      if (/kanzlei|wp|wirtschaftsprüf|steuerberat|datev|mandant/i.test(msg)) {
        return {
          route_key: "queue_kanzlei_wp",
          queue_label: "Kanzlei / WP (aus Kontext)",
          priority: "normal",
          sla_bucket: "priority",
        };
      }
      return {
        route_key: "queue_other",
        queue_label: "Sonstiges / Qualifikation",
        priority: "low",
        sla_bucket: "standard",
      };
  }
}
