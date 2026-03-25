# E2E-Demo: High-Risk-KI von Onboarding bis Board-Export (5–10 Minuten)

Dieser Ablauf spiegelt den **automatisierten Backend-Pfad** in `tests/test_e2e_high_risk_governance_flow.py` wider. Voraussetzung: Frontend gegen laufende API (`NEXT_PUBLIC_API_BASE_URL`), gültiger `x-api-key` / Mandanten-Kontext wie in der Entwicklungsumgebung.

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

**API-Referenz (kurz):** `POST /api/v1/ai-systems` oder `POST /api/v1/ai-systems/import` → `POST .../classify` → `POST .../nis2-kritis-kpis` → `POST /api/v1/ai-governance/actions` → `POST /api/v1/evidence/uploads` → `GET .../compliance/overview`, `GET .../readiness/eu-ai-act`, `GET .../board-kpis`, `GET .../alerts/board`, KPI-/Alert-Export.
