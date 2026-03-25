# AI Governance Playbook (Tenant-Workspace)

Die Seite **`/tenant/ai-governance-playbook`** richtet sich an **CISO**, **AI-Governance-Lead**, **Projektleitung** und **Berater**. Sie bündelt Rollen/RACI, einen **dreistufigen Phasenplan** (Readiness → Operational → Excellence) und einen **kurzen Pilot-Ablauf** (4–6 Wochen) mit Deep-Links in die bestehenden Module (KI-Register, Policies, Board-Readiness, KPIs inkl. What-if, Advisor).

## Feature-Flags

- **Backend:** `COMPLIANCEHUB_FEATURE_AI_GOVERNANCE_PLAYBOOK` (Standard wie andere Pilot-Flags: an, wenn nicht gesetzt)
- **Frontend:** `NEXT_PUBLIC_FEATURE_AI_GOVERNANCE_PLAYBOOK` (spiegelnd; Standard an)

Ist das Flag aus, liefert die Route **404**; Navigations- und Übersichts-Links werden nicht gerendert.

## Zusammenspiel mit Guided Setup und KI

1. **Guided Setup** (`/tenant/compliance-overview`): Die Checkliste bleibt die operative „Was jetzt?“-Ansicht. Im Playbook verlinkte Aufgaben entsprechen typischerweise den Setup-Schritten 1–2 (Inventar/Klassifikation), Policies, Readiness und System-Details für KPIs/Evidenz.
2. **KI-Assist:** Wo im Playbook NIS2-KPI-Vorschläge, EU-AI-Act-Doku-Entwürfe oder Action-Entwürfe genannt sind, gelten dieselben Backend-Flags wie überall (`COMPLIANCEHUB_FEATURE_LLM_*` / `NEXT_PUBLIC_FEATURE_LLM_*`).
3. **Berater:** Kasten „Für Berater“ verweist auf `/advisor`, Mandanten-Steckbriefe und Demo-Templates – konsistent mit `docs/e2e-demo-flow.md`.

## Navigation

- Prominenter Block auf **`/tenant/compliance-overview`**
- Eintrag **„AI Governance Playbook“** in der Tenant-Sidebar (neben Pilot-Runbook, falls aktiv)
- Optionaler Link **„Mehr dazu im AI Governance Playbook“** im Guided-Setup-Header
