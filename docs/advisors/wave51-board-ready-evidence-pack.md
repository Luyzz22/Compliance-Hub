# Wave 51 – Board-Ready Evidence Pack

## Zweck und Zielgruppe

Kompaktes **Markdown-Artefakt** für **Geschäftsführung**, **Bereichsleitung** und **board-nahe** Gespräche in KMU und oberem Mittelstand (DACH). Es bündelt bestehende Advisor-Signale in einer **kurzen, sachlichen** Fassung – ohne PDF-Layout, ohne Folien-Engine, ohne Mandanten-Einzeltiefe.

**Nicht** gedacht als: Rechtsgutachten, Abschlussprüfung, vollständige Normenabdeckung oder Ersatz für Mandanten-Audit.

## Struktur (A–E)

| Abschnitt | Inhalt |
|-----------|--------|
| **A – Executive Readiness Snapshot** | Gesamtlage (Mandantenzahl, dominante Readiness-Klasse, Queue, offene Prüfpunkte); operative Top-Risiken aus SLA-Befunden/Eskalationssignalen; wesentliche offene Punkte (Kadenz, Queue-Kurzimpulse) |
| **B – Cross-Regulation (Kurz)** | Je Säule (EU AI Act, ISO 42001, NIS2, DSGVO) Zähler OK / Nacharbeit / Priorität / unbekannt; optional Hinweis Mehrfach-Druck |
| **C – AI-Governance (Kurz)** | Heuristische AI-Act-/Register-Relevanz; aggregierte Governance-Lücken (ISO 42001, Post-Market, Human Oversight); Hinweis zu Oversight/Monitoring |
| **D – Evidence Touchpoints** | Kurzfassung Evidence Hooks (DATEV, SAP/ERP-Metadaten); Statusüberblick verbunden/geplant/nicht verbunden/Fehler |
| **E – Empfohlene Management-Schritte** | 3–5 Punkte aus SLA-„Nächste Schritte“ und Portfolio-Schwerpunkt-Heuristik (wie Monatsreport Fokusliste), ohne Ticket-System |

Am Ende des Markdown: Liste **eingeschlossener Signalquellen** (`meta.included_signals_de`) für Transparenz.

## Eingeschlossene Signale (Build)

Deterministisch aus:

- `KanzleiPortfolioPayload` (Zeilen, Queue, SLA-Auswertung)
- `buildCrossRegulationMatrixFromPayload` (Wave 49)
- `AdvisorAiGovernancePortfolioDto` (Wave 48, aus Board-Bundle)
- `buildAdvisorEvidenceHooksPortfolioDto` (Wave 50, inkl. Store + synthetische Zeilen)
- optional `AdvisorKpiPortfolioSnapshot` (`attachAdvisorKpiToPayload`) für eine **zweizeilige KPI-Stichprobe** in Abschnitt A

## API

`GET /api/internal/advisor/board-ready-evidence-pack` (Lead-Admin-Auth wie andere Advisor-Routen)

| Query | Standard | Bedeutung |
|-------|----------|-----------|
| `kpi_window_days` | `90` | Fenster für KPI-Snapshot (7–365) |
| `kpi` | an | `kpi=0` schaltet KPI ab (kein Eintrag in Signalquellen-Liste für KPI, keine Stichprobe in A) |

**Antwort:** `board_ready_evidence_pack` (strukturiert, `wave51-v1`), `markdown_de` (identisch zu `board_ready_evidence_pack.markdown_de`).

## Wortwahl (management-tauglich)

- **Postur**, **Steuerung**, **Hinweis**, **Prüfbedarf**, **Kadenz**, **Evidenz-Reife** – statt „compliant“ oder „rechtssicher“.
- KI: **mögliche** Relevanz, **Dashboard-Indikator**, keine automatische Risikoklassifikation nach EU AI Act.
- ERP/SAP/DATEV: **Metadaten-Hooks**, **keine Live-Integration** in dieser Wave.
- Immer klarstellen: Angaben sind **Aggregat** aus ComplianceHub-Datenlage.

## Abgrenzung

| Artefakt | Fokus |
|----------|--------|
| **Partner-Review-Paket (Wave 44)** | Interne Kanzlei-/Partner-Steuerung, Top-Mandanten, Baseline-Delta, mehr operative Detailtiefe |
| **Monatsreport (Wave 42)** | Periodischer Sammelreport inkl. optionaler Baseline, KPI-Abschnitte, längere Struktur |
| **Board-Ready Evidence Pack (Wave 51)** | **Executive Kurzfassung** A–E, eine Seite Lesedauer, gleiche Datenbasis wie oben, andere Zuspitzung |

## UI

Kanzlei-Cockpit (`/admin/advisor-portfolio`): Block **„Board-Ready Pack erstellen“**, Vorschau, **Markdown kopieren**, Download als `.md`.

## Grenzen und rechtlicher Hinweis

- Keine Rechtsberatung; keine Gewähr für Vollständigkeit oder Aktualität außerhalb des erzeugten Portfolio-Zeitpunkts.
- Keine substanzielle Prüfung einzelner Verarbeitungen oder Systeme.
- Für verbindliche Board-Beschlüsse sind Mandanten-Fakten und externe Beratung erforderlich.

## Siehe auch

- `docs/advisors/wave50-enterprise-evidence-hooks.md`
- `docs/advisors/wave49-cross-regulation-matrix.md`
- `docs/advisors/wave48-ai-governance-view.md`
- `docs/advisors/wave42-kanzlei-monatsreport.md`
- `docs/advisors/wave44-partner-review-package.md`
- `frontend/src/lib/boardReadyEvidencePackBuild.ts`
