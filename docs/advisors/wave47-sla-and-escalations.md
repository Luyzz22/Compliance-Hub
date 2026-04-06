# Wave 47 – SLA-Regeln & Eskalationssignale (Advisor)

Interne, **regelbasierte** SLA-Sicht für Kanzlei-Steering: wenige Schwellen auf Basis von **KPI-Snapshot**, **Portfolio-Zählern**, **Reminder-Last** und **Attention-Queue**. **Kein** Workflow-Engine, **kein** externes Ticketing.

## Abgrenzung zu KPI, Trends und Queue

| Artefakt | Rolle |
|----------|--------|
| **KPI-Snapshot (Wave 45)** | Momentaufnahme: Deckungen, Mediane, Hygiene – mit Ampel und Kurz-Trend zur Vorperiode. |
| **KPI-Trends (Wave 46)** | Persistierte Tagespunkte, Vergleich letzter vs. vorheriger Punkt im Zeitraum. |
| **Attention-Queue (Wave 41)** | Mandanten-priorisierte Arbeitsliste nach Heuristik (Kadenz, Lücken, Ampeln). |
| **SLA / Eskalation (Wave 47)** | **Regelwerk**: explizite Schwellen → Befunde (info/warning/critical) → wenige **Eskalationssignale** + Auto-Reminder `sla_escalation` bei Portfolio-Druck. |

## Regel-Modell

Felder in `AdvisorSlaRuleDefinition` (Code: `frontend/src/lib/advisorSlaRulesDefault.ts`):

| Feld | Bedeutung |
|------|-----------|
| `rule_id` | Stabile ID (z. B. `sla_review_coverage_warn`). |
| `tenant_id` | `null` = gesamtes Advisor-Portfolio (Kanzlei-Workspace); mandantenbezogene Regeln sind Wave 47 nicht vorgesehen. |
| `scope` | `review` \| `export` \| `reminder` \| `gaps` – für Deep-Links und Reports. |
| `condition_type` | `threshold_kpi` \| `threshold_age` \| `threshold_count` (Auswertung erfolgt über `metric_key`). |
| `metric_key` | z. B. `kpi.review.current_share`, `payload.open_reminders_total`, `payload.attention_queue_size`. |
| `operator` | `lt` \| `lte` \| `gt` \| `gte` |
| `threshold` | Numerischer Schwellwert (Anteile 0–1, Tage, Stückzahlen). |
| `severity` | `info` \| `warning` \| `critical` |
| `active` | Regel ein-/ausschalten. |

## Vordefinierte Regeln (Auszug)

Typische DACH-Zielkorridore (anpassbar im Code):

- **Review:** Deckung &lt; 75 % Warnung, &lt; 55 % kritisch; mittleres Review-Alter &gt; 180 Tage Warnung (wenn KPI lieferbar).
- **Export:** „frisch“-Anteil &lt; 65 % Warnung, &lt; 45 % kritisch; ≥ 2 Mandanten „nie exportiert“ kritisch.
- **Reminder:** &gt; 12 offene Warnung, &gt; 25 kritisch; ≥ 3 heute/überfällig Warnung, ≥ 8 kritisch.
- **Gaps / Queue:** Queue ≥ 6 Warnung, ≥ 10 kritisch; Anteil ohne rote Säule &lt; 55 % Warnung; ≥ 4 Mandanten mit überfälligem Review kritisch.

Hinweis: **„Review alle 12 Monate“** entspricht in der Plattform der Kadenz-Schwelle (`review_stale_days`, typisch 90) in Queue/Reminder; SLA ergänzt **Portfolio-Deckungs**-Sicht aus KPI.

## Auswertung

- Läuft im **Portfolio-Compute** (`computeKanzleiPortfolioPayload`): nach normalem Reminder-Sync wird ein KPI-Snapshot gebaut, Regeln ausgewertet, Ergebnis als `payload.advisor_sla` angehängt.
- **Persistenz:** `data/advisor-sla-signal-state.json` (bzw. `ADVISOR_SLA_SIGNAL_STATE_PATH` / Vercel `/tmp`) speichert **Critical-Rule-IDs** des letzten Laufs für das Signal **Partner-Aufmerksamkeit** (fortbestehende Critical-Verletzungen).

## Eskalationssignale

| Signal | Aktiv wenn … |
|--------|----------------|
| `portfolio_red` | ≥ 2 **critical** Befunde gleichzeitig. |
| `partner_attention_required` | ≥ 3 critical **oder** mindestens ein critical, das auch im **vorherigen** Lauf critical war. |
| `client_risk_flag` | ≥ 2 Mandanten in der **Queue** mit **überfälligem Review** und **roter Säule**. |

## Reminder-Integration

Bei `portfolio_red` **oder** `partner_attention_required`: bis zu **drei** Auto-Reminder (`category: sla_escalation`) für die Top-Queue-Mandanten, mit kurzem Hinweistext. Wenn die Eskalation entfällt, werden offene SLA-Auto-Reminder geschlossen (nicht manuelle Einträge).

## API & UI

- Portfolio-Response enthält immer `advisor_sla`.
- Zusätzlich: `GET /api/internal/advisor/sla-status` (Lead-Admin) – liefert nur SLA-Block nach frischem Portfolio-Compute.
- Cockpit: kompaktes Panel mit Befunden, Signalen und Sprungmarken (Review / Export / Reminder / Queue / Tabelle).

## Reports

- **Monatsreport:** Abschnitt **7) SLA & Eskalation** (nach KPI & Trends).
- **Partner-Paket:** Abschnitt **G) SLA-Lagebild**.

## Grenzen

- Keine mandantenspezifischen SLA-Profile in Wave 47.
- Keine Garantie-Fristen gegenüber Mandanten; interne Steuerungshilfe.
- Schwellen sind **Code-Konstanten**, kein UI-Konfigurator.

## Siehe auch

- `docs/advisors/wave48-ai-governance-view.md`
- `docs/advisors/wave45-advisor-kpis.md`
- `docs/advisors/wave46-kpi-trends.md`
- `docs/advisors/wave43-reminders-and-followups.md`
- `frontend/src/lib/advisorSlaEvaluate.ts`
