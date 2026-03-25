/** Zentrale Navigations-Definition (Single Source für Header + Secondary Nav). */

export const BOARD_NAV_ITEMS = [
  { href: "/board/kpis", label: "Board KPIs" },
  { href: "/board/nis2-kritis", label: "NIS2 / KRITIS" },
  { href: "/board/eu-ai-act-readiness", label: "EU AI Act Readiness" },
  { href: "/board/incidents", label: "Incidents" },
  { href: "/board/suppliers", label: "Supplier Risk" },
] as const;

export const WORKSPACE_NAV_ITEMS = [
  { href: "/tenant/compliance-overview", label: "Übersicht" },
  { href: "/tenant/ai-systems", label: "KI-Systeme" },
  { href: "/tenant/eu-ai-act", label: "EU AI Act" },
  { href: "/tenant/blueprints", label: "Blueprints" },
  { href: "/tenant/policies", label: "Policies" },
  { href: "/tenant/audit-log", label: "Audit-Log" },
] as const;

export const BRAND_TAGLINE =
  "GRC · EU AI Act · NIS2 · ISO 42001";
