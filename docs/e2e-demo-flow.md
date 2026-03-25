# E2E-Demo: High-Risk-KI von Onboarding bis Board-Export (5–10 Minuten)

Dieser Ablauf spiegelt den **automatisierten Backend-Pfad** in `tests/test_e2e_high_risk_governance_flow.py` wider. Voraussetzung: Frontend gegen laufende API (`NEXT_PUBLIC_API_BASE_URL`), gültiger `x-api-key` / Mandanten-Kontext wie in der Entwicklungsumgebung.

## AI Governance Playbook

Für **Rollen/RACI**, **Phasenplan** (Readiness → Operational → Excellence) und einen **kompakten Pilot-Ablauf** (4–6 Wochen) mit Deep-Links in Register, Board und Advisor: **`/tenant/ai-governance-playbook`** (schaltbar über `COMPLIANCEHUB_FEATURE_AI_GOVERNANCE_PLAYBOOK` / `NEXT_PUBLIC_FEATURE_AI_GOVERNANCE_PLAYBOOK`). Kurzbeschreibung und Flag-Details: **`docs/ai-governance-playbook.md`**.

## Cross-Regulation Dashboard

**`/tenant/cross-regulation-dashboard`**: Pflichten mehrerer Regelwerke (EU AI Act, ISO 42001/27001/27701, NIS2, DSGVO) vs. tenant-**Controls** und **Coverage** („Map once, comply many“). Flags: `COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD` / `NEXT_PUBLIC_FEATURE_CROSS_REGULATION_DASHBOARD`. Details: **`docs/cross-regulation-dashboard.md`**.

**`/board/ai-compliance-report`**: KI-generierter **AI-Compliance-Board-Report** (Markdown) aus Coverage, Top-Gaps und optional Gap-Assist; Persistenz in `ai_compliance_board_reports`. Flags: `COMPLIANCEHUB_FEATURE_AI_COMPLIANCE_BOARD_REPORT` / `NEXT_PUBLIC_FEATURE_AI_COMPLIANCE_BOARD_REPORT`.

## Guided Setup für neue Tenants

Für **CISO/ISB** und **AI-Governance-Leads** liefert der Workspace unter **`/tenant/compliance-overview`** den **Setup-Assistenten EU AI Act & NIS2**: eine Checkliste mit Fortschrittsbalken („X von 7 Schritten“). Der Status wird **nicht manuell abgehakt**, sondern aus Mandantendaten berechnet (`GET /api/v1/tenants/{tenant_id}/setup-status`).

**Typischer Ablauf aus Sicht CISO / AI-Governance:**

1. **Perspektive wählen** (optional, nur UI): CISO/Security, AI-Governance/Legal/DSB oder Fachbereich – beeinflusst Reihenfolge/Hervorhebung der Schritte (lokal im Browser gespeichert).
2. Schritte der Reihe nach über **„Jetzt erledigen“**-Links öffnen: KI-Register (`/tenant/ai-systems`), EU-AI-Act-Cockpit, Policies, Readiness-Board, System-Detail für KPIs und Evidenz.
3. **Policies:** Beim ersten Anlegen/Import eines KI-Systems legt die API Standard-Policy-Zeilen in der Datenbank an; im UI prüfen Sie die Inhalte unter **`/tenant/policies`**.
4. **Readiness-Baseline:** Der Assistent wertet u. a. fortgeschrittene **Compliance-Status-Einträge** (über `not_started` hinaus) als Signal, dass die Readiness-/Gap-Arbeit begonnen hat – zusätzlich zur reinen Ansicht von **`/board/eu-ai-act-readiness`**.

Nach Abschluss der sieben Kriterien zeigt die Übersicht **7 von 7**; Board- und Export-Flows aus den folgenden Abschnitten bauen darauf auf.

## Berater-Portfolio (Advisor-Workspace)

Für **Steuerberatung / WP / GRC-Beratung** mit mehreren Mandanten:

1. In der Tabelle **`advisor_tenants`** die Zuordnung **`advisor_id`** (z. B. E-Mail) → **`tenant_id`** pflegen; optional **`tenant_display_name`**, **`industry`**, **`country`**.
2. **API:** `GET /api/v1/advisors/{advisor_id}/tenants/portfolio` mit Header **`x-advisor-id`** (identisch zum Pfad) und **`x-api-key`**. In Produktion **`COMPLIANCEHUB_ADVISOR_IDS`** setzen (Komma-getrennte erlaubte `advisor_id`-Werte).
3. **Frontend:** `NEXT_PUBLIC_ADVISOR_ID` auf dieselbe `advisor_id` setzen; optional **`NEXT_PUBLIC_SHOW_ADVISOR_NAV=1`**, damit der Menüpunkt **Advisor** sichtbar ist. Route **`/advisor`**: Vergleich Readiness, NIS2-Mittelwert, Setup, High-Risk, offene Actions. **Tenant öffnen** setzt das Cookie **`ch_workspace_tenant`** und lädt **`/tenant/compliance-overview`** für diesen Mandanten.
4. **Export:** `GET /api/v1/advisors/{advisor_id}/tenants/portfolio-export?format=json|csv` (Dateiname z. B. `advisor-portfolio-YYYY-MM-DD`).

### Mandanten-Steckbrief (Advisor-Report)

Für **Angebotsunterlagen, Kickoff-Workshops, Status-Reviews oder kurze Vorstandstexte** liefert Compliance Hub pro Mandant einen **Mandanten-Steckbrief** (Readiness, NIS2-/KRITIS-KPIs, Governance-Actions, Guided-Setup):

1. **UI:** Auf **`/advisor`** in der Tabelle pro Zeile **Steckbrief (MD)** bzw. **JSON** – Download über die Next.js-Proxy-Route **`/api/advisor/tenant-report`** (übergibt `tenantId`, `format`, `advisorId`; serverseitig `COMPLIANCEHUB_API_KEY` und optional `COMPLIANCEHUB_ADVISOR_ID`).
2. **API:** `GET /api/v1/advisors/{advisor_id}/tenants/{tenant_id}/report?format=json|markdown` mit denselben Headern wie das Portfolio (`x-advisor-id`, `x-api-key`). Nur wenn der Mandant in **`advisor_tenants`** dem Berater zugeordnet ist.
3. **Markdown:** `Content-Type: text/markdown; charset=utf-8`, Dateiname z. B. `tenant-report-{tenant_id}.md` – als Basis für PDF, Slides oder Executive Summaries weiterverarbeiten.

## Demo-Tenant-Templates & One-Click-Setup

**Nur für interne Demos und Berater-Piloten** – nicht für produktive Mandanten. Das Seeding ist an **`COMPLIANCEHUB_DEMO_SEED_TENANT_IDS`** gebunden (Komma-getrennte erlaubte `tenant_id`-Werte) und erfordert einen separaten API-Key **`COMPLIANCEHUB_DEMO_SEED_API_KEYS`**.

1. **Leeren Demo-Mandanten** anlegen bzw. eine noch leere `tenant_id` wählen, die in der Allowlist steht.
2. **Backend:** `GET /api/v1/demo/tenant-templates` (mit `x-api-key` aus `COMPLIANCEHUB_DEMO_SEED_API_KEYS`) listet Szenarien: z. B. KRITIS-Energie, Industrie-Mittelstand, WP-Kanzlei.
3. **Backend:** `POST /api/v1/demo/tenants/seed` mit JSON `{ "template_key": "…", "tenant_id": "…", "advisor_id": "…" optional }` – legt KI-Systeme, Klassifikationen, NIS2-KPIs, Policies, Actions und Demo-Evidenzen an (nur wenn der Mandant noch **kein** KI-Register hat).
4. **Frontend:** Unter **`/settings`** und **`/advisor`** der Bereich **Demo-Tenants** – Button **Demo-Daten einspielen** ruft die Next.js-Routen **`/api/demo/tenant-templates`** und **`/api/demo/seed`** auf; serverseitig **`COMPLIANCEHUB_DEMO_SEED_API_KEY`** (ein Key aus der Backend-Allowlist) und **`COMPLIANCEHUB_API_BASE_URL`** setzen.
5. **Nach dem Seed:** Meldung mit Kennzahlen; **Compliance-Übersicht öffnen** setzt **`ch_workspace_tenant`** und springt zu **`/tenant/compliance-overview`**. Von dort **Guided Setup**, **`/board/*`**, **`/tenant/*`** und ggf. **`/advisor`** mit Portfolio/Steckbrief.

## 1) KI-System anlegen

1. Öffnen: **`/tenant/ai-systems`**.
2. **CSV/XLSX importieren** (Panel „AI-Systeme importieren“) mit mindestens einer Zeile High-Risk – oder „Neues System“ nutzen, falls angebunden.
3. Ziel: ein System wie **„KRITIS Netzlast-Prognose“**, **High-Risk**, Business Unit z. B. Netzbetrieb.

## 2) Detail: Klassifikation & NIS2-/KRITIS-KPIs

1. In der Tabelle **Detail** wählen → **`/tenant/ai-systems/[id]`**.
2. **Klassifikation (EU AI Act):** Use-Case **kritische Infrastruktur** / Anhang-III-Pfad prüfen (entspricht API `POST .../classify` mit `critical_infra`).
3. **NIS2-/KRITIS-KPIs** am System pflegen (Incident-Reife, Supplier-Coverage, OT/IT) – mittlere Werte (z. B. 40–60 %) zeigen Lücken und Board-Alerts.

## 3) Governance-Maßnahme & Evidenz

1. **Maßnahme:** Entweder über vorhandene Actions-UI oder über mit dem System verknüpfte Aufgaben – Titel z. B. *„NIS2 Supplier-Risk-Register für Netzlast-KI vollständig aufbauen“*, Requirement-Bezug NIS2 / EU AI Act.
2. **Evidenz:** Im Bereich **Evidenz & Dokumente** des Systems Datei hochladen (DPIA, Runbook). Wo die UI Maßnahmen-Evidenz anbietet: zweites Dokument an die **Action** hängen.
3. Optional: Board-**Audit-Record** anlegen und dort ein drittes Dokument für den Prüfpfad ablegen.

## 4) Board: Readiness & Lücken

1. **`/board/eu-ai-act-readiness`:** Gesamt-Readiness, **kritische Anforderungen**, **offene Maßnahmen** – das neue System und verknüpfte Actions sollten sichtbar sein.
2. **`/board/kpis`:** Executive-KPIs inkl. EU-AI-Act- und Governance-Scores.
3. **`/board/nis2-kritis`:** Drilldown zu NIS2-/KRITIS-KPIs; Einfluss des Systems auf Aggregationen.

## 5) Export für WP / DMS / DATEV

1. Board-**Export** (JSON/CSV) nutzen – je nach Produkt-UI: KPI-Export, Alert-Export oder verknüpfter Audit-/Report-Job.
2. Prüfen: Export enthält **Tenant**, **Zeitstempel** und **Systemzeilen** inkl. NIS2-KPI-Spalten (analog `GET /api/v1/ai-governance/report/board/kpi-export`).

---

**API-Referenz (kurz):** `GET /api/v1/demo/tenant-templates` → `POST /api/v1/demo/tenants/seed` (nur Demo-Allowlist) → `GET /api/v1/tenants/{tenant_id}/setup-status` → `GET /api/v1/advisors/{advisor_id}/tenants/portfolio` (optional Export) → `POST /api/v1/ai-systems` oder `POST /api/v1/ai-systems/import` → `POST .../classify` → `POST .../nis2-kritis-kpis` → `POST /api/v1/ai-governance/actions` → `POST /api/v1/evidence/uploads` → `GET .../compliance/overview`, `GET .../readiness/eu-ai-act`, `GET .../board-kpis`, `GET .../alerts/board`, KPI-/Alert-Export.
