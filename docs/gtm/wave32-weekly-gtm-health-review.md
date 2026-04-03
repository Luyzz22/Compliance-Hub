# Wave 32 – Weekly GTM Health Review & minimale Alerts

## Zweck

Eine **feste wöchentliche Routine** (ca. 15–20 Minuten) und **optionale Automatisierung**, damit Founders und frühe GTM ohne weiteres Tooling sehen, ob Intake, Triage, Sync und Pipeline im Rahmen bleiben — aufbauend auf [Wave 29](wave29-founder-dashboard.md), [30](wave30-attribution-and-campaign-tracking.md) und [31](wave31-gtm-health-and-readiness.md).

## Wöchentliche Checkliste (15–20 Min.)

1. **GTM Health (oben auf `/admin/gtm`)**  
   - Eingang: Webhook/Spam-Signal.  
   - Triage: „Neu“-Backlog.  
   - CRM-Sync: Fehler/Dead Letter.  
   - Pipeline: qualifiziert vs. Deals (grob).

2. **Aufmerksamkeit + operative Hinweise**  
   - Fehlgeschlagene Webhooks / Syncs.  
   - Wiederholungen ohne Triage.  
   - SLA-Hinweise (ältere „Neu“, stuck failed sync, qualifiziert ohne Deal — letzteres ist ein **Proxy**, siehe Wave 31).

3. **Segment-Readiness**  
   - Mittelstand, Kanzlei, Enterprise: Volumen, Qualifikation, HubSpot/PD-Touches, Top-Quellen.  
   - Entscheidung: **Fokus** nächste Woche (Reichweite vs. ICP vs. Angebot).

4. **Attribution**  
   - Tabellen 7/30 Tage (Snapshot-API) bzw. Dashboard-Abschnitte: starke Quellen/Campaigns.  
   - **Noise**: viele Leads, wenig Qualifikation — Zielgruppe/Bots/CTA prüfen (heuristisch).

5. **2–3 konkrete Aktionen**  
   - z. B. Backlog leeren, CTA testen, Qualifikationskriterien schärfen, einen Sync-Job fixen.  
   - Optional als **Wochen-Notiz** im Dashboard speichern.

## Cadence & Rollen

| Thema | Empfehlung |
|--------|------------|
| **Rhythmus** | Fix **1× pro Woche** (z. B. Montag 15 Min.); bei Alerts **ad hoc** nachziehen. |
| **Teilnehmer** | Mindestens **1 Founder + GTM/Ops**; bei rein operativem All-Clear reicht 1 Person. |
| **Out-of-band** | Wenn **Alert-Check** `fired: true` liefert oder eine Health-Kachel dauerhaft „Handeln“ zeigt. |

## Alerts (Wave 32)

### Bedingungen (Schwellen)

Konfiguration: `frontend/src/lib/gtmAlertThresholds.ts`.

- **Triage:** „Neu“ älter als 3 Tage — Warning / Critical ab Zählgrenzen.  
- **Dead Letters:** CRM Dead Letters im 30-Tage-Fenster — Warning / Critical.  
- **Qualifiziert ohne Deal:** Proxy wie Wave 31 — Warning / Critical.

### Ausführung

| Mechanismus | Beschreibung |
|-------------|--------------|
| **HTTP** | `GET` oder `POST` `/api/admin/gtm/alert-check` mit `Authorization: Bearer <LEAD_ADMIN_SECRET>` **oder** `GTM_ALERT_SECRET`, alternativ `?secret=` (nur in vertrauenswürdigen Netzen). |
| **Log** | Bei ausgelösten Findings: strukturierter Log `[gtm-alert-wave32]`. |
| **Webhook** | Optional `GTM_ALERT_WEBHOOK_URL` — POST JSON mit `findings`, `summary_de`, `generated_at` (n8n, generischer Slack-Bridge, …). |
| **Script** | `frontend/scripts/gtm-alert-check.mjs` mit `COMPLIANCEHUB_BASE_URL` + Secret. Exit-Code `2`, wenn Alerts gefeuert haben (für CI). |

### Health-Snapshot (Maschinenlesbar)

`GET /api/admin/gtm/health-snapshot` — gleiche Auth wie Alert-Check (Lead-Admin **oder** `GTM_ALERT_SECRET`).

Liefert u. a. Health-Kachel-Status, `health_signal_counts`, Aufmerksamkeit nach `kind`, KPIs 7/30 Tage, Segment-Readiness kompakt, Attribution 7d + Top 30d, **`alerts_evaluated`** (gleiche Logik wie Alert-Check, ohne Seiteneffekt).

## Wochen-Review im Produkt

- **`/admin/gtm`:** Block „Wöchentlicher GTM-Review“ mit Kurz-Checkliste, **Zuletzt reviewt**, letzte Notizen, **Review abhaken** / **Notiz speichern**.  
- **Speicher:** JSON-Datei (Pfad über `GTM_WEEKLY_REVIEW_STORE_PATH`, sonst `data/gtm-weekly-review.json` unter `process.cwd()`, auf Vercel `/tmp/...`). **Kein Multi-User-Audit** — nur einfacher interner Zustand.

## API-Übersicht

| Route | Auth | Zweck |
|-------|------|--------|
| `GET /api/admin/gtm/summary` | Lead-Admin | Dashboard inkl. `weekly_review` (letzte Notizen, `last_reviewed_at`). |
| `GET/POST /api/admin/gtm/weekly-review` | GET/POST Lead-Admin | Lesen / Notiz + Abhaken (POST `mark_reviewed`, optional `note`). |
| `GET /api/admin/gtm/health-snapshot` | Lead-Admin oder `GTM_ALERT_SECRET` | Export für Skripte. |
| `GET/POST /api/admin/gtm/alert-check` | Lead-Admin oder `GTM_ALERT_SECRET` | Alerts auswerten, optional Webhook. |

## Technische Referenz

- `frontend/src/lib/gtmWeeklyReviewStore.ts`  
- `frontend/src/lib/gtmHealthSnapshotBuilder.ts`  
- `frontend/src/lib/gtmAlertEvaluator.ts`  
- `frontend/src/lib/gtmAlertDispatcher.ts`  
- `frontend/src/lib/gtmAlertThresholds.ts`

Siehe auch: [Wave 31 – Health & Readiness](wave31-gtm-health-and-readiness.md) (Aktualisierung unten).
