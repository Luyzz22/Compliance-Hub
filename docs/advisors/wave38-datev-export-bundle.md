# Wave 38 – DATEV-freundliches Kanzlei-Export-Bundle (Arbeitspaket)

Internes **ZIP-Arbeitspaket** pro **Mandant** (`client_id`): dieselbe narrative und offene-Punkte-Logik wie der **Mandanten-Readiness-Export** (Wave 37), ergänzt um **stabile Dateinamen**, **semikolongetrennte CSV** (Excel DE / Büro-Workflow) und **Referenzliste** für Nachweise. Ziel: Kanzleien erhalten ein **kompaktes Archiv** zum Ablegen, Weiterleiten oder manuellen Anhang – nicht einen zusätzlichen „glossy“ Report.

## Inhalt des Bundles (stabile Namen)

| Datei | Inhalt |
|--------|--------|
| `01-mandantenstatus.md` | Vollständiger **Mandanten-Readiness**-Markdown (Wave 37): kompakter Status, relevante Systeme, offene Prüfpunkte, nächste Schritte, Nachweishinweise. |
| `02-offene-punkte.csv` | Offene Punkte tabellarisch: `mandant_id`, `pillar`, `object_type`, `object_reference`, `issue_summary`, `priority`, `owner`, `due_hint`, `last_update`. Spaltentrenner **Semikolon**; UTF-8 mit **BOM** für Excel. |
| `03-nachweis-referenzen.csv` | Kompakte **Nachweis-/Referenzzeilen**: letzter Mandanten-/Board-Report, EU-AI-Act-Readiness-Aggregat, Hochrisiko-KI-Systeme, optional NIS2-KPI-Snapshot (falls Dashboard liefert). |
| `04-metadata.json` | Bundle-Version, Mandanten-ID, Erzeugungszeitpunkt, Verweis auf Wave-37-Payload-Version, `api_fetch_ok`, Dateiliste, kurzer Hinweis DMS/DATEV (manuell). |

**Pillar-Codes** (filterbar in Excel): `EU_AI_Act`, `ISO_42001`, `NIS2`, `DSGVO` (Heuristik aus Prüfpunkt-Text und Punkt-Typ; Hochrisiko-/Board-Punkte standardmäßig EU AI Act).

## Kanzlei-Workflow (beabsichtigt)

1. Mandanten-ID eingeben und **DATEV-/Kanzlei-Export** auslösen (oder API direkt aufrufen).
2. ZIP speichern in **DMS** / **DATEV-Dokumentenablage** (manuell) oder per E-Mail an Bearbeiter:in.
3. `02-offene-punkte.csv` in Excel öffnen, priorisieren, **Verantwortliche** ergänzen, mit Jahresabschluss- oder Beratungsliste abgleichen.
4. `03-nachweis-referenzen.csv` als **Stichwortliste** zu vorhandenen Belegen / Systemen nutzen (kein Ersatz für originäre Nachweise in ComplianceHub).

## Unterschied zum reinen Mandanten-Readiness-Export (Wave 37)

| Aspekt | Wave 37 (JSON + Markdown) | Wave 38 (Bundle) |
|--------|---------------------------|-------------------|
| Ausgabe | Ein JSON mit `markdown_de` + strukturierte Felder | **ZIP** mit fester Dateistruktur |
| Tabellen | Nur in Markdown | **Dedizierte CSV** für offene Punkte und Referenzen |
| Ziel | Vorschau, Kopieren, einzelne `.md` | **Archiv / Weitergabe** an Büroprozesse |
| DATEV | Hinweis im Text | Gleicher Hinweis in `04-metadata.json`; Dateiformate **bürotauglich** |

Die **Fachlogik** der offenen Punkte bleibt zentral in `frontend/src/lib/tenantBoardReadinessGaps.ts` (`computeMandantOffenePunkte`); die Erzählung in `01` kommt aus `generateMandantReadinessAdvisorExport` (`mandantReadinessAdvisorExport.ts`).

## API

`GET /api/internal/advisor/datev-export-bundle?client_id=<mandanten_id>`

- **Auth:** wie andere interne Advisor-Routen (`LEAD_ADMIN_SECRET` / Session, siehe Wave 37).
- **Antwort:** `application/zip` mit `Content-Disposition: attachment`.
- **Validierung `client_id`:** wie Mandanten-Export (alphanumerisch plus `._-`).

## UI

`/admin/advisor-mandant-export` – Button **„DATEV-/Kanzlei-Export erstellen“** (ZIP-Download ohne große neue Oberfläche).

## Technische Implementierung

- Bundle- und CSV-Logik: `frontend/src/lib/datevKanzleiBundleGenerate.ts`
- ZIP: `jszip` (Server-Route, Node-Runtime)
- Route: `frontend/src/app/api/internal/advisor/datev-export-bundle/route.ts`

## Mögliche spätere Erweiterung Richtung DATEV

- Anbindung an **DATEV Unternehmen online** / **Belegbilderservice** über definierte Metadatenfelder (z. B. Mandantennummer, Geschäftsjahr) – **nicht** Teil von Wave 38.
- Optional: festes **Import-Mapping** für Kanzlei-Tools, sofern DATEV-seitig ein CSV-Profil vereinbart wird.

## Siehe auch

- `docs/advisors/wave37-mandant-readiness-export.md`
- `docs/integration/steuerkanzlei-datev-dms-integration.md`
