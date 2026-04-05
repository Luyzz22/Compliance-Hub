# Wave 40 – Kanzlei-Review-Kadenz & Export-Historie

Erweiterung der Advisor-Werkzeuge (Wave 37–39) um **sichtbare Kadenz**: wann zuletzt **geprüft** (Review), wann **Readiness-Export** und **DATEV-ZIP** erzeugt wurden, plus **einfache Überfälligkeits-Signale** im Portfolio – ohne Kalender- oder Benachrichtigungs-Engine.

## Was wird getrackt?

Pro **Mandant** (`tenant_id`), persistent in **`data/advisor-mandant-history.json`** (oder `ADVISOR_MANDANT_HISTORY_PATH`):

| Feld | Bedeutung |
|------|-----------|
| `last_mandant_readiness_export_at` | Zeitpunkt des letzten erfolgreichen `GET …/mandant-readiness-export` (JSON-Erzeugung) |
| `last_datev_bundle_export_at` | Zeitpunkt des letzten erfolgreichen `GET …/datev-export-bundle` (ZIP-Download) |
| `last_review_marked_at` | Zeitpunkt, zu dem die Kanzlei „Review durchgeführt“ bestätigt hat |
| `last_review_note_de` | Optionale kurze Notiz zum letzten Review |

**Legacy:** Die ältere Datei `data/advisor-portfolio-touchpoints.json` (Wave 39) wird beim **Lesen** noch mitgemischt (`last_export_iso` → Readiness-Export, `last_review_iso` → Review), wird aber bei neuen Events **nicht** beschrieben.

## APIs (intern, Lead-Admin)

| Methode | Pfad | Zweck |
|---------|------|--------|
| `GET` | `/api/internal/advisor/mandant-history?client_id=…` | Historie + berechnete Stale-Flags für einen Mandanten |
| `POST` | `/api/internal/advisor/mandant-review` | Body: `{ "client_id": "…", "note_de"?: "…" }` – setzt Review auf jetzt; optional Notiz (ohne `note_de`: alte Notiz bleibt) |

Readiness- und DATEV-Routen **schreiben** die Export-Zeitstempel automatisch nach erfolgreicher Antwort (Fehler beim Schreiben loggen, Export bleibt gültig).

## Schwellen (konfigurierbar im Code)

Zentral: `frontend/src/lib/kanzleiReviewCadenceThresholds.ts`

- **`KANZLEI_REVIEW_STALE_DAYS`** (Standard **90**): Review gilt als überfällig, wenn nie gesetzt oder älter.
- **`KANZLEI_ANY_EXPORT_MAX_AGE_DAYS`** (Standard **90**): „Jüngster Export“ = späteres Datum aus Readiness- vs. DATEV-Export; wenn keiner oder älter → Export-Signal.
- **`KANZLEI_MANY_OPEN_POINTS`** (**4**): Filter „viele offene Prüfpunkte“ im Cockpit.
- **`KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE`** (**5**): Kombiregel „viele Lücken ohne frischen Export“ für Attention-Score.

## Portfolio (`/admin/advisor-portfolio`)

- Spalten **Readiness-Export**, **DATEV-ZIP**, **Review** (Datum + Notiz).
- Badges **Kein Export** / **Review** bei `never_any_export` bzw. `review_stale`.
- Filter **Review überfällig**.
- Aktion **Review durchgeführt** pro Zeile (optionaler Kurztext per Prompt).

Payload-Version ab Wave 41 **`wave41-v1`** (inkl. `attention_queue`); Konstanten in `kanzlei_portfolio.constants` ausgeliefert.

## Mandanten-Readiness-UI (`/admin/advisor-mandant-export`)

- Block **Kanzlei-Historie** mit letzten Zeitpunkten und Textsignalen.
- **Review durchgeführt** mit optionalem Notizfeld; nach Readiness- oder ZIP-Export wird die Historie neu geladen.

## Attention-Score (Anpassung)

`kanzleiAttentionScore` berücksichtigt u. a.:

- `any_export_stale` (kein / alter Export, siehe oben),
- `review_stale`,
- `gaps_heavy_without_recent_export` (≥ `KANZLEI_GAP_HEAVY_FOR_EXPORT_RULE` offene Punkte **und** `any_export_stale`).

## Unterschied zu GTM / Board-Readiness-Kadenz

| Aspekt | GTM / Board Readiness | Wave 40 Kanzlei-Historie |
|--------|------------------------|---------------------------|
| Zweck | Produkt-/Portfolio-Ampeln, Nachfrage | **Operative Kanzlei-Arbeit** (wann zuletzt mit Mandant gearbeitet?) |
| Daten | API-Snapshots, Segmente | **Interne JSON-Datei** + Export-Hooks |
| Review | Kein Advisor-„Review“-Stamp | Expliziter **Review**-Zeitstempel durch Berater |

## Nutzung für wiederkehrende Mandanten-Checks

1. Portfolio nach **Score** und **Review-Filter** sortieren.
2. Pro Mandant Export ziehen (Readiness oder ZIP) – Zeitstempel aktualisieren sich.
3. Nach Gespräch **Review durchgeführt** setzen; optional Notiz für DMS/Arbeitsdatei.
4. Schwellen bei Bedarf im Threshold-Modul anpassen (kein UI-Configurator in Wave 40).

## Siehe auch

- `docs/advisors/wave41-kanzlei-review-playbook-and-queue.md`
- `docs/advisors/wave37-mandant-readiness-export.md`
- `docs/advisors/wave38-datev-export-bundle.md`
- `docs/advisors/wave39-kanzlei-portfolio-cockpit.md`
