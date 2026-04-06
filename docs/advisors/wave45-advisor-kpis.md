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
- **Ohne rote Säule:** Im Strip weiterhin oft `unknown`; **Wave 46** ergänzt dafür persistierte **History-Trends** (siehe `wave46-kpi-trends.md`).

## API

`GET /api/internal/advisor/kpi-portfolio` (Lead-Admin wie andere Advisor-Interna)

| Parameter | Standard | Bedeutung |
|-----------|----------|-----------|
| `window_days` | `90` | Auswertungsfenster und Länge der Vorperiode (7–365) |
| `segment_by` | `readiness` | `readiness` oder `primary_segment` (Branchencluster aus GTM-Segment) |
| `persist_history` | — | `1` = nach Snapshot einen **Tagespunkt** in die KPI-History schreiben (Wave 46) |

Antwort: `{ ok, advisor_kpi_portfolio }` – vollständiger Snapshot inkl. `strip`, `segments`, `interpretation_notes_de`.

## Einbindung Monatsreport & Partner-Paket

- **Monatsreport:** Abschnitt **5) Kanzlei-KPIs** im Markdown/JSON, sofern KPIs nicht abgeschaltet werden. Query: `kpi_window_days`, `kpi=0` schaltet den Block ab. **Wave 46:** Abschnitt **6) KPI-Trends** (rolling 3 Monate), wenn KPIs an sind. **Wave 47–49:** Abschnitte **7) SLA**, **8) AI-Governance**, **9) Cross-Regulation** unabhängig von `kpi`.
- **Partner-Review-Paket:** Abschnitt **E) Kanzlei-KPIs**; `kpi=0` optional. **Wave 46:** Abschnitt **F) KPI-Trends**. **Wave 47:** Abschnitt **G) SLA-Lagebild** (Regeln & Eskalation aus KPI, Queue, Remindern) – siehe `wave47-sla-and-escalations.md`. **Wave 48:** Partner-Paket **H)** – AI-Governance; siehe `wave48-ai-governance-view.md`. **Wave 49:** Partner-Paket **I)** – Cross-Regulation; siehe `wave49-cross-regulation-matrix.md`.

## Grenzen (bewusst)

- **Keine Export-Event-Historie:** „Wie viele Exporte in einem Monat“ ist ohne separates Log nicht exakt; genutzt wird der **letzte** Zeitstempel pro Mandant und ob er im Fenster liegt.
- **Attention-Queue ohne Zeitstempel:** Es gibt kein „Eintrag in Queue um T0“. Der Median für `portfolio_attention`-Reminder ist ein **Proxy** (Bedingung erkannt → Auto-Reminder angelegt → erledigt).
- **Ein Kanzlei-Workspace:** Die APIs beziehen sich auf das **gemappte Mandantenportfolio** dieser Umgebung, nicht auf mandantenübergreifende SaaS-Analytics.

## Interpretation für Kanzleien (Beispiele)

- **Review aktuell unter 50 %, Trend ↓:** Review-Rhythmus mit Partnerterminen oder Playbook-Zyklen schärfen; Historie im Cockpit pflegen.
- **Median Reminder &gt; 168 h:** Follow-ups stauen sich – wöchentliche Queue-Durcharbeitung oder Delegation klären.
- **Viele rote Säulen:** Priorisierung über Attention-Queue und Mandanten-Exports, nicht über KPI-Strip alleine.

## Siehe auch

- `docs/advisors/wave49-cross-regulation-matrix.md`
- `docs/advisors/wave47-sla-and-escalations.md`
- `docs/advisors/wave46-kpi-trends.md`
- `docs/advisors/wave44-partner-review-package.md`
- `docs/advisors/wave42-kanzlei-monatsreport.md`
- `docs/advisors/wave43-reminders-and-followups.md`
- `frontend/src/lib/advisorKpiPortfolioBuild.ts`
