# Frontend Unification Plan

## 1. Audit Summary

### Current Route Structure

| Area | Routes | Layout |
|------|--------|--------|
| **Public/Marketing** | `/` (home), `/kontakt` | Root layout (`SbsHeader` + `SbsFooter`) |
| **Auth** | `/auth/login`, `/auth/register`, `/auth/forgot-password`, `/auth/reset-password`, `/auth/profile` | Root layout (no dedicated auth shell) |
| **Board (Enterprise)** | `/board/kpis`, `/board/nis2-kritis`, `/board/eu-ai-act-readiness`, `/board/incidents`, `/board/suppliers`, `/board/compliance-calendar`, `/board/executive-dashboard`, `/board/gap-analysis`, `/board/datev-export`, `/board/xrechnung-export`, `/board/ai-compliance-report`, `/board/n8n-workflows` | Board layout (`TenantWorkspaceShell`) |
| **Tenant Workspace** | `/tenant/compliance-overview`, `/tenant/ai-systems`, `/tenant/eu-ai-act`, `/tenant/blueprints`, `/tenant/policies`, `/tenant/audit-log`, `/tenant/ai-governance-playbook`, `/tenant/ai-governance-setup`, `/tenant/cross-regulation-dashboard`, `/tenant/pilot-runbook`, `/tenant/onboarding-readiness` | Tenant layout (sidebar + `TenantNav`) |
| **AI Systems** | `/ai-systems` | Root layout (top-level, outside tenant) |
| **Incidents** | `/incidents` | Root layout (top-level) |
| **Settings** | `/settings` | Root layout |
| **Advisor** | `/advisor`, `/advisor/clients/[tenantId]/governance-snapshot`, `/advisor/clients/[tenantId]/incident-drilldown` | Root layout |
| **Admin** | `/admin/leads`, `/admin/board-readiness`, `/admin/advisor-portfolio`, `/admin/advisor-mandant-export`, `/admin/gtm` | Admin layout (metadata only) |
| **Internal** | `/internal/advisor-metrics` | Root layout |
| **Multi-tenant Evidence** | `/tenants/[tenantId]/evidence/ai-act` | Tenants layout (sidebar + `TenantNav`) |

### Identified Issues

1. **No dedicated auth shell** — login/register pages render inside the full app layout with global nav, which is inconsistent with enterprise auth flows
2. **Enterprise modules scattered** — Gap Analysis, DATEV Export, Board Reporting live under `/board/` but are not visible in the global nav dropdown
3. **No auth links in header** — users cannot navigate to login/register from the main header
4. **Login success dead-end** — after login, user sees raw JSON result instead of redirect to dashboard
5. **Landing page CTAs disconnected** — "Demo anfragen" goes to contact, but there's no prominent signup/login CTA
6. **Admin pages have no nav** — admin layout is empty, no sidebar/breadcrumbs
7. **Inconsistent module grouping** — AI Systems exists both at `/ai-systems` (top-level) and `/tenant/ai-systems` (workspace)
8. **Footer links incomplete** — footer only shows Start, Board KPIs, Tenant, Supplier, Kontakt

### Shared Component System

- **`EnterprisePageHeader`** — used across all enterprise pages (good)
- **`boardLayout.ts`** — design token file with `CH_*` constants (good, needs more tokens)
- **`TenantNav`** — sidebar nav for workspace (good)
- **`GlobalAppNav`** — top-level dropdown nav (needs expansion)
- **`AppSecondaryNav`** — contextual sub-nav strip (needs expansion)

## 2. Target Architecture

### Layout Hierarchy

```
RootLayout (html/body, SbsHeader, SbsFooter)
├── / (public marketing — home, kontakt)
├── /auth/* (AuthLayout — centered card, minimal chrome)
│   ├── /auth/login
│   ├── /auth/register
│   ├── /auth/forgot-password
│   ├── /auth/reset-password
│   └── /auth/profile
├── /board/* (Board layout — TenantWorkspaceShell)
│   ├── Executive & KPIs
│   ├── Compliance modules
│   └── Reporting & Export
├── /tenant/* (Tenant layout — sidebar + TenantNav)
│   └── Workspace modules
├── /ai-systems (top-level AI systems registry)
├── /incidents (incident management)
├── /settings (workspace settings)
├── /advisor/* (advisor portal)
└── /admin/* (admin portal)
```

### Unified Navigation Structure

**Primary Nav (Header):**
- Start (home)
- Board ▾ (KPIs, NIS2, EU AI Act, Incidents, Suppliers, Calendar)
- Workspace ▾ (tenant modules)
- Reporting ▾ (Executive Dashboard, Gap Analysis, DATEV, XRechnung, AI Compliance Report)
- AI Systems
- Incidents
- Admin ▾ (visible for admin roles: Leads, Board Readiness, GTM, Advisor Portfolio)
- Settings (gear icon)
- Auth (Login/Register or Profile)

**Secondary Nav (context strip):**
- Board area: board sub-pages + link to workspace
- Workspace area: tenant sub-pages + link to board
- Reporting area: reporting sub-pages
- Admin area: admin sub-pages
- Auth area: hidden (minimal chrome)

### Page Mapping

| Legacy/Current | Target | Action |
|---------------|--------|--------|
| `/` | `/` | Keep — add auth CTAs |
| `/auth/*` | `/auth/*` | Add dedicated auth layout |
| `/board/*` | `/board/*` | Keep — add to Reporting nav group |
| `/tenant/*` | `/tenant/*` | Keep |
| `/ai-systems` | `/ai-systems` | Keep — add to primary nav |
| `/incidents` | `/incidents` | Keep |
| `/settings` | `/settings` | Keep |
| `/admin/*` | `/admin/*` | Keep — add admin nav |
| `/kontakt` | `/kontakt` | Keep |
| `/advisor/*` | `/advisor/*` | Keep |

## 3. Implementation Summary

### Phase 1: Navigation & Shell
- Extended `appNavConfig.ts` with reporting, admin, and auth nav items
- Auth layout (`/auth/layout.tsx`) for centered, minimal auth pages
- Updated `GlobalAppNav` with Reporting dropdown, Admin dropdown, auth user menu
- Updated `AppSecondaryNav` for reporting and admin context strips
- Auth links in header via `SbsHeader`

### Phase 2: Flow Connections
- Landing page CTAs → auth signup/login
- Login success → dashboard redirect
- Footer updated with enterprise module links

### Phase 3: Design Consistency
- Extended `boardLayout.ts` with additional enterprise design tokens
- Breadcrumb support in `EnterprisePageHeader`
- Consistent spacing, typography, and card styles across all modules
