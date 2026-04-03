# Wave 29 – Founder Dashboard / GTM Command Center

Ziel: **eine** interne, pragmatische Übersicht für operative GTM-Steuerung (Founder, frühe Sales, Ops) — **ohne** BI-Stack. Daten kommen aus dem bestehenden Lead-Store, Triage (`ops-state.json`) und Sync-Job-Store.

## Zugriff

- Route: **`/admin/gtm`**
- Autorisierung wie Lead-Inbox: `LEAD_ADMIN_SECRET`, Session-Cookie nach Login unter **`/admin/leads`**, oder Bearer/Query beim API-Zugriff.
- API: `GET /api/admin/gtm/summary` → JSON `snapshot` (nur mit gültiger Admin-Auth).

## Architektur

- **Aggregation:** `frontend/src/lib/gtmDashboardAggregate.ts` (server-only) lädt `readAllLeadRecordsMerged`, `readLeadOpsState`, `listAllLeadSyncJobs`, merged/rollups wie die Inbox (`mergeLeadsWithOps`, `attachContactRollups`).
- **Zeit-Hilfen (testbar):** `frontend/src/lib/gtmDashboardTime.ts`
- **Typen (Client + Server):** `frontend/src/lib/gtmDashboardTypes.ts`
- **UI:** `frontend/src/components/admin/GtmCommandCenterClient.tsx`

## KPI-Karten (7 / 30 Tage)

Zeitfenster beziehen sich auf **`created_at` der Anfrage** (Inbound), außer bei Sync-Zählern (siehe unten).

| KPI | Bedeutung |
|-----|-----------|
| **Inbound-Anfragen** | Anzahl `lead_inquiry` im Fenster. |
| **Wiederholte Kontakte** | Anfragen mit `contact_submission_count > 1` (gleiche E-Mail-Gruppe). |
| **Qualifiziert** | Triage `qualified` oder `closed_won_interest`. |
| **Kontaktiert** | Triage exakt `contacted`. |
| **Webhook fehlgeschlagen** | `forwarding_status === failed` (Legacy-Inbound-Webhook). |
| **Sync Dead Letters** | Jobs `dead_letter`; Zeitfilter auf `updated_at` / letzter Versuch. |
| **HubSpot erfolgreich** | Jobs `target === hubspot`, `status === sent` (echter Connector, kein Stub). |
| **Pipedrive Deals neu** | Jobs `pipedrive`, `sent`, `mock_result.deal_action === "created"`; Zeitfilter nach `synced_at` im Ergebnis. |

## Segmenttabelle (30 Tage)

Zeilen: `industrie_mittelstand`, `kanzlei_wp`, `enterprise_sap`, **Sonstiges** (inkl. `sonstiges`).

- **Anfragen / Qualifiziert:** wie KPI, nur auf Segment aufgeteilt.
- **CRM-Sync-Probleme:** Anzahl Jobs mit `failed` oder `dead_letter` für `hubspot` oder `pipedrive`, deren letztes Update im 30-Tage-Fenster liegt, pro Segment des zugehörigen Leads.

## Trichter

Absolute **Stückzahlen**, keine automatischen Conversion-Raten (vermeidet falsche Schlüsse bei verzögertem Triage).

- **CTA-Klicks:** aktuell **nicht** in einem abfragbaren Store — nur serverseitiges Log (`/api/marketing-event`). Im Dashboard **0** mit Hinweistext.
- Weitere Stufen: Anfragen nach Einreichungsdatum mit aktuellem Triage-Status bzw. Pipedrive-Deal-Count wie oben.

Hinweis: Ein Lead kann **nach** dem 30-Tage-Fenster qualifiziert werden; daher können spätere Stufen in einem Fenster nicht strikt „unter“ der vorherigen Stufe liegen.

## Aufmerksamkeit

Kurze Listen (jeweils bis ca. 8 Einträge): fehlgeschlagene Webhooks, Dead-Letter-Syncs, wiederholte Kontakte ohne Triage-Wechsel, CRM-Sync-Fehler. Links zur Inbox nutzen `?focus=<lead_id>` (UUID).

## Trends

- **Täglich:** Anfragen pro Kalendertag **UTC**, letzte 14 Tage.
- **Wöchentlich:** Qualifizierte nach **Kalenderwoche der Einreichung (UTC)**; Pipedrive „Deal neu“ nach **Sync-Zeitpunkt** in der jeweiligen Woche.

## Bekannte Grenzen

- Keine persistente CTA-Zeitreihe → Trichter beginnt faktisch bei Formular-Anfragen.
- Qualifizierung in der Wochenansicht bezieht sich auf **Einreichungsdatum**, nicht auf das Datum der Triage-Änderung (dafür fehlt eine dedizierte Event-Tabelle).
- Sehr große JSONL/Job-Stores: Aggregation ist O(n); bei Bedarf später cachen oder Zeitraum begrenzen.
- Fokus-Link setzt nur die `lead_id` in der Inbox, wenn die Liste geladen ist und die ID existiert.

Siehe auch: [Wave 28 – Lead-Sync](wave28-lead-sync-framework.md), [Wave 26 – Lead-Inbox](wave26-internal-lead-inbox.md), [Wave 30 – Attribution](wave30-attribution-and-campaign-tracking.md), [Wave 31 – Health & Readiness](wave31-gtm-health-and-readiness.md).
