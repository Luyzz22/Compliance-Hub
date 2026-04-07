# Wave 36 – Quarterly Board Pack Export

Leichtgewichtiger **Board-/Advisory-Pack** aus den bestehenden Board-Readiness-Daten: strukturiertes Memo, priorisierte Attention-Liste und **Aktionsregister** – als JSON und **Markdown** für Notion, Confluence, E-Mail oder ein Folien-Gerüst. **Kein PDF**, keine automatischen Rechtsfolgen.

## Zweck und Scope

- **Intern** für Founder, CCO, CISO: in **~10 Minuten** lesbar, dann manuell verfeinern.
- Datenbasis: gleiche Aggregation wie `/admin/board-readiness` (gemappte Mandanten, Live-API).
- **Baseline** (optional, Wave 35): `data/board-readiness-briefing-baseline.json` liefert **Delta-Zeilen** im Executive-Memo.

## Pack-Struktur (3 Teile)

| Teil | Inhalt |
|------|--------|
| **A – Executive Memo** | Kopfzeile/Datum, **Ampel je Säule** (EU AI Act, ISO 42001, NIS2, DSGVO), **Änderungen seit Baseline**, **Risiken/Aufmerksamkeit** (faktisch, aus roten Säulen + roten Attention-Items). |
| **B – Attention Items** | Top-Liste aus dem Dashboard, **regelbasiert priorisiert**, mit Referenz-ID (`HR-AI-…`, `TENANT-…`, `GTM-…`) und Kurztext. |
| **C – Aktionsregister** | Kandidaten-Maßnahmen aus Lücken + optional **Säulen-Sweep** bei roter Portfolio-Ampel einer Säule; Spalten: Aktion, Säule, Owner (Platzhalter, wenn unbekannt), Horizont, Referenzen. |

Implementierung: `frontend/src/lib/boardPackTypes.ts`, `frontend/src/lib/boardPackGenerate.ts`.

## Phase-3-Erweiterung (EU AI Act Operationalisierung)

Board-nahe KPIs berücksichtigen zusätzlich die KI-Register-Posture:

- `ki_register_registered`
- `ki_register_planned`
- `ki_register_partial`
- `ki_register_unknown`

Diese Kennzahlen fließen in die Board-Markdown-Sektion ein und unterstützen die
Steuerung zwischen "bereits registriert", "in Vorbereitung" und "unklar/offen".

## API

`GET /api/admin/board-readiness/board-pack`

- Auth wie andere Admin-Routen (`LEAD_ADMIN_SECRET`).
- Antwort: `{ ok: true, board_pack }` mit `memo`, `attention`, `actions`, `markdown_de`, `meta` (Zeitstempel, Scope, Baseline-Hinweis, Priorisierungsregeln).

## Priorisierung (transparent)

Fest im Code dokumentiert (`BOARD_PACK_PRIORITIZATION_RULES_DE`):

1. Zuerst **Rot**, dann **Amber** (Grün fließt nicht in die Attention-Tabelle des Packs).
2. Innerhalb gleicher Ampel: **fehlender Owner** → **fehlender/veralteter Board-Report** → **Art. 9** → **Nachweis/Doku** → **GTM vs. Readiness**.

Keine KI-Bewertung; nur Text-Matching auf `missing_artefact_de` und `severity`.

## Ableitung des Aktionsregisters

- Pro priorisiertem Attention-Item (bis ca. 18 Zeilen, inkl. Dedupe): **operative Kurzsätze** (z. B. Owner setzen, Board-Report aktualisieren).
- **Owner:** in dieser Wave nur Platzhalter „Unbekannt – CCO/CISO zuweisen“, sofern die API keine verlässliche Person zuordnet (faktische Lücken bleiben sichtbar).
- **Horizont:** heuristisch (`now` / `this_quarter` / `next_quarter`) – z. B. Rot + Owner/Board eher **Jetzt**; GTM-Hinweise **dieses Quartal**.
- Zusätzlich: bei **roter Säule** auf Portfolio-Ebene eine Zeile **„Säule entzerren“** mit Referenz `PILLAR-<key>`.

## Markdown-Export

Enthält: Titel, Metadaten, Teil A–C, Markdown-Tabelle für Attention und Aktionsregister, Abschnitt **Priorisierungsregeln**, Disclaimer.

## UI

`/admin/board-readiness` → Abschnitt **Quarterly Board Pack** (über dem Wave-35-Briefing): Button **Board Pack erzeugen**, Vorschau Memo / Tabellen, Markdown mit Kopieren und `.md`-Download.

## Was vor dem Versand manuell bleibt

- Rechtschreibung, Tonalität, **rechtliche Einordnung** und Freigabe durch die Geschäftsführung bzw. Legal.
- **Owner** und **Termine** im Aktionsregister konkret benennen.
- Optional: Baseline nach Board-Termin speichern (Wave 35: `POST …/briefing/baseline`), damit das nächste Pack **Deltas** zeigt.

## Verwandte Doku

- `docs/board/wave34-board-readiness-dashboard.md` – Indikatoren und Datenquellen.
- `docs/board/wave35-board-readiness-briefing.md` – Briefing vs. Pack (Briefing = narrative Gliederung; Pack = Memo + Register + Tabellen-Markdown).
