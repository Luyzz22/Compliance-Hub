# Wave 48 – AI-Governance Advisor View

Interne **Advisor-Ansicht** für das Kanzlei-Portfolio mit Fokus auf **EU AI Act** und **ISO 42001**. Sie verdichtet dieselben Board-Readiness-Signale wie das Mandanten-Cockpit – **ohne** neue Rechtslogik und **ohne** automatische Risiko- oder Register-Qualifikation.

## Modell (pro Mandant)

Felder sind **erklärbar** und aus `TenantPillarSnapshot` / Roh-APIs abgeleitet (siehe `boardReadinessAggregate`, `tenantBoardReadinessGaps`).

| Feld | Werte | Quelle (kurz) |
|------|--------|----------------|
| `ai_systems_declared` | ja / nein / unbekannt | `ai_systems.length`, `fetch_ok` |
| `high_risk_indicator` | ja / nein / unbekannt | High-Risk-Einträge im Compliance-Dashboard |
| `ai_act_artifact_completeness` | schwach / mittel / stark / unbekannt | EU-AI-Act-Säulen-Ampel (`eu.status`) |
| `iso42001_governance_completeness` | schwach / mittel / stark / unbekannt | ISO-42001-Säule (`iso.status`) |
| `post_market_monitoring_readiness` | ja / nein / teilweise | Board-Report-Aktualität bei HR-Systemen, Ampel |
| `human_oversight_readiness` | ja / nein / teilweise | `owner_email` bei High-Risk-Systemen |
| `registration_relevance` | ja / nein / unbekannt | Dashboard vorhanden + HR > 0 → Hinweis; sonst Heuristik |
| `notes_de` | Kurztexte | Kombination aus obigen Signalen (Beratersprache) |
| `links` | Export + Board Readiness | wie Kanzlei-Portfolio-Zeilen |

## Portfolio-Aggregation

Modul: `frontend/src/lib/advisorAiGovernanceBuild.ts` (pure Logik) und `frontend/src/lib/advisorAiGovernanceAggregate.ts` (Server: Mapping aus Snapshots).

Zusammenfassung (`summary`):

- Zähler für Mandanten mit **Hinweis auf mögliche AI-Act-/Register-Thematik** (Heuristik: Register-Relevanz „ja“ oder sehr schwache EU-Act-Säule).
- **High-Risk-Exposition**: Mandanten mit mindestens einem High-Risk-System im Dashboard.
- **ISO-42001-Nachholbedarf**: Säule schwach oder mittel.
- **Post-Market/Reporting-Lücke**: HR-Kontext, Board-Report nicht frisch.
- **Human-Oversight-Prüfbedarf**: fehlende Owner bei High-Risk-Systemen.
- **Buckets** je Säule EU AI Act / ISO 42001 (schwach/mittel/stark/unbekannt).

**Top-Aufmerksamkeit:** Priorisierung über ein einfaches Gewicht (Post-Market, Oversight, schwache Säulen, HR) – keine Ticket-Engine.

## API

- `GET /api/internal/advisor/ai-governance-overview`  
  Antwort: `ai_governance_overview` (JSON), `markdown_de` (Kurz-Markdown für E-Mail/Wiki).
- `GET /api/v1/ki-register/posture` und Snapshot-Felder in `ai_systems_summary`:
  - `ki_register_registered`, `ki_register_planned`, `ki_register_partial`, `ki_register_unknown`
  - `advisor_attention_items` (fehlende Register-/Scope-/Owner-Angaben)

Monatsreport und Partner-Paket laden Snapshots **einmal** und nutzen `computeAdvisorAiGovernanceFromBundle` neben `computeKanzleiPortfolioPayload({ preloadedBundle })`, um doppelte Mandanten-Runden zu vermeiden.

## UI (Cockpit)

Bereich **`#kanzlei-ai-governance-panel`** im Kanzlei-Portfolio: Kacheln mit Kennzahlen, Top-Mandanten mit Links zu **Mandanten-Export** und **Board Readiness**, Verweis auf die Mandantentabelle.

## Wortlaut (DACH, advisor-safe)

UI und Markdown verwenden Formulierungen wie:

- „Hinweis auf mögliche AI-Act-Relevanz“
- „Fehlende Governance-Artefakte“
- „Prüfbedarf Human Oversight“
- „Keine automatische Rechtsbewertung“

Es wird **nicht** behauptet, dass ein Registerpflicht-Eintrag besteht oder ein System rechtsverbindlich „High-Risk“ ist – nur dass die **in der Plattform geführten** Daten solche **Beratungs- und Steuerungsfragen** nahelegen.

## Report-Einbindung

- **Kanzlei-Monatsreport:** Abschnitt **8) AI-Governance (Wave 48)**.
- **Partner-Review-Paket:** Teil **H) AI-Governance-Steuerung**.

## Grenzen / rechtliche Vorsicht

- Keine Rechtsberatung; keine vollautomatische Klassifizierung nach EU AI Act.
- Register- und Risikoentscheidungen liegen bei Mandant und qualifiziertem Berater.
- NIS2/DSGVO sind in den Säulen sichtbar, aber **nicht** Gegenstand dieser Wave (keine eigenen Regeln).

## Abgrenzung zu KPI, Queue und SLA

| Artefakt | Zweck |
|----------|--------|
| **KPI / Trends (Wave 45–46)** | Kadenz, Reaktionszeiten, Segmentüberblick |
| **Attention-Queue (Wave 41)** | Operative Priorität über Scores und harte Flags |
| **SLA (Wave 47)** | Regelbasierte Eskalation aus KPI + Queue + Remindern |
| **AI-Governance View (Wave 48)** | Fokus EU AI Act + ISO 42001 – **Posture** und Beraterkapazität |

## Siehe auch

- `docs/advisors/wave49-cross-regulation-matrix.md`
- `docs/advisors/wave47-sla-and-escalations.md`
- `docs/advisors/wave45-advisor-kpis.md`
- `docs/advisors/wave39-kanzlei-portfolio-cockpit.md`
- `frontend/src/lib/boardReadinessAggregate.ts`
