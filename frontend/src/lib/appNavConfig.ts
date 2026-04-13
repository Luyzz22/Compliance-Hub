/** Zentrale Navigations-Definition (Single Source für Header + Secondary Nav). */
/** Hinweis: EU-AI-Act-Evidenz ist mandantenspezifisch unter `/tenants/{tenantId}/evidence/ai-act` und erscheint nur bei Feature + OPA (siehe TenantNav / GlobalWorkspaceEvidenceNavBlock). */

export const BOARD_NAV_ITEMS = [
  { href: "/board/kpis", label: "Board KPIs" },
  { href: "/board/nis2-kritis", label: "NIS2 / KRITIS" },
  { href: "/board/eu-ai-act-readiness", label: "EU AI Act Readiness" },
  { href: "/board/incidents", label: "Incidents" },
  { href: "/board/suppliers", label: "Supplier Risk" },
  { href: "/board/compliance-calendar", label: "Compliance Calendar" },
] as const;

export const WORKSPACE_NAV_ITEMS = [
  { href: "/tenant/compliance-overview", label: "Übersicht" },
  { href: "/tenant/ai-systems", label: "KI-Systeme" },
  { href: "/tenant/eu-ai-act", label: "EU AI Act" },
  { href: "/tenant/blueprints", label: "Blueprints" },
  { href: "/tenant/policies", label: "Policies" },
  { href: "/tenant/audit-log", label: "Audit-Log" },
  { href: "/tenant/trust-center", label: "Trust Center" },
] as const;

/** Enterprise Reporting & Export module pages. */
export const REPORTING_NAV_ITEMS = [
  { href: "/board/executive-dashboard", label: "Executive Dashboard" },
  { href: "/board/gap-analysis", label: "Gap Analysis" },
  { href: "/board/ai-compliance-report", label: "AI Compliance Report" },
  { href: "/board/datev-export", label: "DATEV Export" },
  { href: "/board/xrechnung-export", label: "XRechnung Export" },
  { href: "/board/n8n-workflows", label: "n8n Workflows" },
] as const;

/** Admin / internal management pages. */
export const ADMIN_NAV_ITEMS = [
  { href: "/admin/leads", label: "Leads" },
  { href: "/admin/board-readiness", label: "Board Readiness" },
  { href: "/admin/advisor-portfolio", label: "Advisor Portfolio" },
  { href: "/admin/advisor-mandant-export", label: "Mandant Export" },
  { href: "/admin/gtm", label: "GTM Command Center" },
  { href: "/admin/audit-log", label: "Audit-Log" },
] as const;

/** Auth-related navigation items. */
export const AUTH_NAV_ITEMS = [
  { href: "/auth/login", label: "Anmelden" },
  { href: "/auth/register", label: "Registrieren" },
] as const;

export const BRAND_TAGLINE =
  "GRC · EU AI Act · NIS2 · ISO 42001";
