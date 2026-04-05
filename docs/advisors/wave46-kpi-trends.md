# Wave 46 – KPI-Trends / einfache Zeitreihen (Advisor)

Leichtgewichtige **Trend-Sicht** für Kanzlei-Steering: wenige Metriken, **persistierte Tages-Snapshots** (erklärbar, kein Event-Rebuild), kompakte API und Cockpit-Visuals. **Kein** BI-Warehouse und kein Charting-Framework.

## Unterstützte Metriken (History)

Alle Werte stammen aus dem gleichen Tagespunkt wie der Wave-45-KPI-Snapshot (ein Eintrag pro UTC-Tag, letzter Stand des Tages gewinnt):

| ID | Bedeutung | Einheit |
|----|-----------|---------|
| `review_coverage` | Review aktuell (Anteil) | 0–1 |
| `export_fresh` | Export-Kadenz OK (Anteil) | 0–1 |
| `open_reminders` | Offene Reminder (Anzahl) | Zahl |
| `no_open_reminders_share` | Anteil Mandanten ohne offenen Reminder | 0–1 |
| `no_red_pillar` | Anteil Mandanten ohne rote Board-Säule | 0–1 |
| `reminder_median_hours` | Median Auflösungszeit Reminder im KPI-Fenster | Stunden oder `null` |

## Snapshot- / History-Logik

- **Speicherort:** `data/advisor-kpi-history.json` (lokal) bzw. `ADVISOR_KPI_HISTORY_PATH` oder unter Vercel `/tmp/...`.
- **Version:** `ADVISOR_KPI_HISTORY_FILE_VERSION` (`wave46-v1`).
- **Granularität:** höchstens **ein Punkt pro UTC-Kalendertag**; erneuter Auftag am selben Tag **ersetzt** den Punkt.
- **Retention:** maximal **120** Punkte (älteste werden verworfen).
- **Schreiben:** erfolgt u. a. bei `GET /api/internal/advisor/kpi-portfolio?persist_history=1`, bei `GET /api/internal/advisor/kpi-trends` mit `append` ungleich `0`, sowie beim Erzeugen von Monatsreport / Partner-Paket mit aktivem KPI-Block (`kpi` nicht `0`).

## API `GET /api/internal/advisor/kpi-trends`

Lead-Admin-Auth wie andere Advisor-Interna (`LEAD_ADMIN_SECRET`).

| Parameter | Standard | Bedeutung |
|-----------|----------|-----------|
| `period` | `4w` | `4w` (28 Tage), `3m` (92 Tage), `qtd` (Quartal bis heute, UTC) |
| `append` | `1` | `0` = keine neue History schreiben, nur lesen/rechnen |
| `kpi_window_days` | `90` | muss zum Snapshot passen (7–365); gleiches Fenster wie KPI-Portfolio |
| `segment` | — | optional; wenn gesetzt und nicht `all`, liefert die API nur einen **Hinweistext** (`segment_note_de`) – Zeitreihen bleiben portfolio-weit (v1) |
| `segment_by` | `readiness` | nur bei `append=1`: `readiness` oder `primary_segment` für den Snapshot beim Append |

**Antwort (Auszug):** `advisor_kpi_trends` mit `version`, `period`, `period_label_de`, `history_points_in_period`, `segment_note_de`, `metrics[]` (je `current_value`, `previous_value`, `direction` `up|down|flat|unknown`, `delta_display_de`, `series[]` mit `t`/`v`), `narrative_lines_de` (Kurzsätze DE).

**Richtung / Delta:** `up` bedeutet „verbessert“ im KPI-Sinn (`lower_is_better` für Counts und Median-Stunden). Vergleich = **letzter gültiger History-Punkt vs. vorheriger gültiger Punkt** innerhalb des gewählten `period`-Fensters (nicht automatisch „Vormonat“).

## Cockpit (UI)

- Nach dem KPI-Strip: **Verlauf (History)** mit Periodenwahl (4 Wochen / 3 Monate / QTD), dezente **Sparklines**, Delta-Text und Scope-Label.
- KPI-Laden nutzt `kpi-portfolio` mit `persist_history=1`; Trends werden mit `kpi-trends?append=0` geholt (ein Portfolio-Compute pro Refresh).
- Readiness-Filter ≠ `all` setzt `segment` für den Hinweis (`segment_note_de`).

## Monatsreport & Partner-Paket

- **Monatsreport:** Abschnitt **6) KPI-Trends** – rolling **3 Monate** (`period` `3m`), Kurzsätze aus `narrative_lines_de`. Nur wenn KPIs nicht mit `kpi=0` abgeschaltet sind.
- **Partner-Review-Paket:** Abschnitt **F) KPI-Trends (Kurz)** – gleiche Logik.

## Interpretation (Kurz)

- Wenige Punkte im Zeitraum → Richtung oft `unknown` oder `flat`; Narrativ weist auf fehlende History hin.
- Sätze beziehen sich auf **aufeinanderfolgende Snapshots**, nicht auf Steuerungs-Baseline des Monatsreports (Abschnitt 3).
- **Segment-Filter** im Cockpit filtert die Tabelle, nicht die persistierte History (v1).

## Grenzen (bewusst)

- Keine mandantenweise Zeitreihen, keine Segment-Zeitreihen in v1.
- Median-Stunden hängen vom gewählten `kpi_window_days` ab; ändernde Fenster erschweren Vergleich über lange Zeiträume.
- Datei-basierte History: bei serverlosem Betrieb (z. B. Vercel) ist Persistenz instanzgebunden (`/tmp`).

## Siehe auch

- `docs/advisors/wave45-advisor-kpis.md`
- `docs/advisors/wave42-kanzlei-monatsreport.md`
- `docs/advisors/wave44-partner-review-package.md`
- `frontend/src/lib/advisorKpiTrendsBuild.ts`
- `frontend/src/lib/advisorKpiHistoryStore.ts`
