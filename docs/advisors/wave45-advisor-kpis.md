# Wave 45 – Advisor-KPIs / Kanzlei Performance Metrics

Interne, **erklärbare** Kennzahlen für operatives Kanzlei-Steering (Regelmäßigkeit von Reviews und Exporten, Reaktion auf Reminder-Signale, Portfolio-Hygiene). **Kein** öffentliches Dashboard und **kein** Analytics-Cube.

## KPI-Überblick (Strip + JSON)

| KPI | Bedeutung | Datenquelle |
|-----|-----------|-------------|
| **Review aktuell** | Anteil Mandanten ohne überfälliges Kanzlei-Review (Schwelle wie Cockpit, z. B. 90 Tage) | Portfolio-Zeilen + Historie (`review_stale`) |
| **Export-Kadenz OK** | Anteil Mandanten mit gültigem letztem Readiness-/DATEV-Export | Portfolio (`any_export_stale`) |
| **Reminder-Reaktionszeit (Median)** | Median Stunden von `created_at` bis `updated_at` bei Remindern mit Status done/dismissed, deren Abschluss im gewählten Fenster liegt | `data/advisor-mandant-reminders.json` |
| **Queue-Reminder (Median)** | Wie oben, nur Kategorie `portfolio_attention` (Proxy für Bearbeitung von Queue-Signalen) | Reminder-Store |
| **Ohne rote Säule** | Anteil Mandanten ohne rote Board-Readiness-Säule (EU AI Act, ISO 42001, NIS2, DSGVO) | Portfolio `pillar_traffic` |

Zusätzlich im JSON (nicht immer im Strip): **Mittleres Review-Alter** (Tage seit `last_review_marked_at` für Mandanten mit gültigem Datum), **Export-Aktivität im Fenster** (Anteil Mandanten, deren letzter Export-Zeitstempel in die letzten *N* Tage fällt), **Segment-Breakdown** nach Readiness-Klasse oder Primärsegment (Branchenlabel).

## Trend-Pfeile (↑ / ↓ / → / ○)

- **Review:** Vergleich der *Aktivität*: Anteil Mandanten mit Review-Zeitstempel im aktuellen Fenster vs. der Vorperiode (gleiche Länge).
- **Export-Aktivität:** Anteil Mandanten mit Export-Zeitstempel im Fenster vs. Vorperiode.
- **Median-Stunden (Reminder / Queue-Proxy):** niedrigere Mediane in der aktuellen Periode = Verbesserung (↑).
- **Ohne rote Säule:** Trend `unknown` (kein historischer Querschnitt ohne zusätzliche Persistenz).

## API

`GET /api/internal/advisor/kpi-portfolio` (Lead-Admin wie andere Advisor-Interna)

| Parameter | Standard | Bedeutung |
|-----------|----------|-----------|
| `window_days` | `90` | Auswertungsfenster und Länge der Vorperiode (7–365) |
| `segment_by` | `readiness` | `readiness` oder `primary_segment` (Branchencluster aus GTM-Segment) |

Antwort: `{ ok, advisor_kpi_portfolio }` – vollständiger Snapshot inkl. `strip`, `segments`, `interpretation_notes_de`.

## Einbindung Monatsreport & Partner-Paket

- **Monatsreport:** Abschnitt **5) Kanzlei-KPIs** im Markdown/JSON, sofern KPIs nicht abgeschaltet werden. Query: `kpi_window_days`, `kpi=0` schaltet den Block ab.
- **Partner-Review-Paket:** Abschnitt **E) Kanzlei-KPIs**; `kpi=0` optional.

## Grenzen (bewusst)

- **Keine Export-Event-Historie:** „Wie viele Exporte in einem Monat“ ist ohne separates Log nicht exakt; genutzt wird der **letzte** Zeitstempel pro Mandant und ob er im Fenster liegt.
- **Attention-Queue ohne Zeitstempel:** Es gibt kein „Eintrag in Queue um T0“. Der Median für `portfolio_attention`-Reminder ist ein **Proxy** (Bedingung erkannt → Auto-Reminder angelegt → erledigt).
- **Ein Kanzlei-Workspace:** Die APIs beziehen sich auf das **gemappte Mandantenportfolio** dieser Umgebung, nicht auf mandantenübergreifende SaaS-Analytics.

## Interpretation für Kanzleien (Beispiele)

- **Review aktuell unter 50 %, Trend ↓:** Review-Rhythmus mit Partnerterminen oder Playbook-Zyklen schärfen; Historie im Cockpit pflegen.
- **Median Reminder &gt; 168 h:** Follow-ups stauen sich – wöchentliche Queue-Durcharbeitung oder Delegation klären.
- **Viele rote Säulen:** Priorisierung über Attention-Queue und Mandanten-Exports, nicht über KPI-Strip alleine.

## Siehe auch

- `docs/advisors/wave44-partner-review-package.md`
- `docs/advisors/wave42-kanzlei-monatsreport.md`
- `docs/advisors/wave43-reminders-and-followups.md`
- `frontend/src/lib/advisorKpiPortfolioBuild.ts`
