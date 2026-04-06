# Wave 49 – Cross-Regulation Advisor Matrix

Portfolio-weite **Steuerungsmatrix** über die vier Kern-Säulen des Board-Readiness-Modells: **EU AI Act**, **ISO 42001**, **NIS2 / KRITIS** und **DSGVO / BDSG**. Ziel: **„Map once, comply many“** – Berater sehen, wo ein Vorhaben mehrere Rahmen zugleich entlastet, ohne Rechtsautomatik.

## Modell (pro Mandant)

| Feld | Bedeutung |
|------|-----------|
| `pillars` | Pro Säule ein Bucket: `ok` \| `needs_attention` \| `priority` \| `unknown` |
| `active_pillar_pressure_count` | Anzahl Säulen mit `priority` oder `needs_attention` |
| `priority_pillar_count` | Anzahl Säulen mit `priority` |
| `notes_de` | Kurzimpulse (Mehrfachbelastung, NIS2/DSGVO-Hinweise, Export) |
| `links` | Wie Kanzlei-Portfolio (Export, Readiness-API, …) |

Säulen-Reihenfolge im Code: `eu_ai_act`, `iso_42001`, `nis2`, `dsgvo`.

## Bucket-Logik (transparent)

1. **Basis:** Board-Readiness-Ampel je Säule (`pillar_traffic`): grün → `ok`, gelb → `needs_attention`, rot → `priority`.
2. **`unknown`:** Wenn `api_fetch_ok` für den Mandanten false ist – keine belastbare Säulenlage.
3. **Lücken-Heuristik:** Ist die **Top-Gap-Säule** (`top_gap_pillar_code`) gleich der Säule und gibt es **offene Prüfpunkte** (`open_points_count > 0`) und entweder **hohe Dringlichkeit** oder **viele offene Punkte** (≥ `many_open_points_threshold`), wird das Bucket für diese Säule mindestens auf `needs_attention` angehoben (ohne `priority` zu überschreiben).

Es werden **keine** separaten juristischen Subsumtionen gebildet; die Matrix spiegelt **vorhandene** Board- und Gap-Signale.

## Portfolio-Aggregation

- **`totals.per_pillar`:** Zähler je Säule und Bucket.
- **`mandanten_multi_pillar_priority`:** Mandanten mit **≥2** Säulen `priority`.
- **`mandanten_multi_pillar_stress`:** Mandanten mit **≥2** Säulen unter Druck (`priority` oder `needs_attention`).
- **`top_cases`:** Sortierung nach gewichteter Stress-Score (Priorität stärker als Nacharbeit), dann Prioritätszahl – für Querschnittsgespräche.

## Interaktion der Säulen (für Berater)

- **EU AI Act / ISO 42001** – KI-Governance und Managementsystem; oft **gemeinsame** Rollen, Policies, Evidence.
- **NIS2 / KRITIS** – kann **unabhängig** von hoher KI-Nutzung relevant sein (Lieferkette, Meldewege, IKT-Risiko).
- **DSGVO / BDSG** – Verarbeitungsübersicht, Verträge, TOMs; Schnittmenge zu KI-Verarbeitung und Lieferanten.

Die Matrix macht sichtbar, wo **NIS2 oder DSGVO** Handlungsdruck erzeugen, **ohne** dass die EU-AI-Act-Säule rot ist – wichtig für **Mittelstand** und **WP-Kanzleien**.

## API

- `GET /api/internal/advisor/cross-regulation-matrix`  
  Antwort: `cross_regulation_matrix`, `markdown_de`.

## Cockpit

Panel **`#kanzlei-cross-regulation-panel`**: kompakte Tabelle Mandant × Säule (Kürzel O / ! / P / ?), Filter, Top-Querschnitt. Daten werden **aus dem geladenen Portfolio** abgeleitet (identisch zur API-Logik über `buildCrossRegulationMatrixFromPayload`).

## Reports

- **Kanzlei-Monatsreport:** Abschnitt **9) Cross-Regulation-Matrix**; Abschnitt **10) Enterprise Evidence Hooks** (Wave 50, SAP/ERP-Metadaten) siehe `wave50-enterprise-evidence-hooks.md`.
- **Partner-Review-Paket:** Teil **I)**; Teil **J)** Evidence Hooks (Wave 50).

## Wortlaut (advisor-safe)

- „Steuerungsmatrix“, „Nacharbeit“, „Priorität“, „Datenlage unbekannt“.
- Keine Formulierungen wie „rechtskonform“ oder „Pflicht besteht“ ohne Mandantenentscheid.

## Grenzen

- Keine Rechtsmeinung, kein Ersatz für Mandanten-Audit oder externe Beratung.
- Keine SAP/ERP-Anbindung in dieser Wave; **Evidenz-Anknüpfungspunkte** (Metadaten, kein ETL) in Wave 50: `docs/advisors/wave50-enterprise-evidence-hooks.md`.
- NIS2/KRITIS-Labeling ist **kommunikativ** (DACH-Kontext); fachliche Tiefe bleibt in Mandanten-Workspace und Board-Readiness.

## Siehe auch

- `docs/advisors/wave51-board-ready-evidence-pack.md`
- `docs/advisors/wave50-enterprise-evidence-hooks.md`
- `docs/advisors/wave48-ai-governance-view.md`
- `docs/advisors/wave39-kanzlei-portfolio-cockpit.md`
- `docs/advisors/wave41-kanzlei-review-playbook-and-queue.md`
- `frontend/src/lib/advisorCrossRegulationBuild.ts`
