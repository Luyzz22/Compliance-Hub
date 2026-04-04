# Wave 35 – Board Readiness Briefing

Internes Hilfsmittel für **Quartals- oder Ad-hoc-Updates** an Board/Advisory: ein **strukturiertes Text-/Markdown-Gerüst**, gespeist aus dem bestehenden Board-Readiness-Dashboard (Wave 34). Kein Ersatz für juristische Prüfung oder vollständige Compliance-Berichte.

## Gliederung (Outline)

Die logische Struktur ist in Code als `BOARD_READINESS_BRIEFING_OUTLINE_DE` in `frontend/src/lib/boardReadinessBriefingTypes.ts` dokumentiert:

1. **Executive Summary** – Portfolio-Ampel, Säulen in Kurzform, optional Delta zur gespeicherten Baseline.
2. **Säulenüberblick** – EU AI Act, ISO 42001, NIS2, DSGVO: je bis zu drei Indikator-Zeilen (Ampel + Kennzahl, falls vorhanden).
3. **High-Risk / Attention Items** – Top-Auswahl aus dem Dashboard mit **Referenz-IDs** (`HR-AI-…`, `TENANT-…`, `GTM-…`).
4. **GTM vs. Governance** – Heuristiken zum 30-Tage-Fenster (z. B. qualifizierte Nachfrage bei dominanter Pilot-Readiness).
5. **Nächste Governance-Prioritäten** – bis zu drei Vorschläge mit **Owner-Platzhalter** und Zeithorizont (manuell zu verfeinern).

## API

| Methode | Pfad | Zweck |
|--------|------|--------|
| `GET` | `/api/admin/board-readiness/briefing` | Liefert `briefing` (JSON: `sections`, `markdown_de`, `delta_bullets_de`, `meta_de`). Nutzt aktuelle Board-Readiness-Berechnung und optional `data/board-readiness-briefing-baseline.json`. |
| `POST` | `/api/admin/board-readiness/briefing/baseline` | Speichert eine **Baseline** (Ampeln + Attention-Zähler) für **Delta-Hinweise** beim nächsten Briefing. |

Auth wie andere Admin-Routen: Session über `LEAD_ADMIN_SECRET` (siehe Lead-Inbox).

Baseline-Pfad: `data/board-readiness-briefing-baseline.json` oder `BOARD_READINESS_BRIEFING_BASELINE_PATH` (z. B. `/tmp` auf Vercel).

## UI

Auf `/admin/board-readiness`:

- Button **„Board Readiness Briefing erzeugen“** (lädt `GET …/briefing`).
- Darstellung der **Abschnitte und Bullets** zum Überfliegen.
- **Markdown** in einem Textfeld (copy-paste) plus **Kopieren** und **Download** als `.md`.

## Nutzung für Decks oder Memos

1. Dashboard aktualisieren, Briefing erzeugen.
2. Optional **Baseline speichern** nach einem Board-Termin, damit das nächste Briefing **Änderungen** in Kurzform nennt.
3. Markdown in Google Docs, Notion, oder Folien **manuell** einteilen (Titel pro Abschnitt = Folie oder Memo-Kapitel).
4. Referenz-IDs nutzen, um in ComplianceHub dieselben Mandanten/Systeme zu öffnen (Pfade siehe Attention-Tabelle im Dashboard).

## Grenzen und Caveats

- **Keine automatischen Rechtsfolgen** – nur Fakten, Lücken und Vorschläge aus vorhandenen API-Signalen.
- **Heuristiken** (GTM vs. Governance, Prioritäten) sind **Startpunkte**; Owner, Termine und Formulierung sind extern zu finalisieren.
- **Baseline** ist bewusst schlank (Ampeln + Zähler), keine tiefe Versionshistorie – für echte Trendanalyse später erweiterbar.
- Sprache der Generierung: **Deutsch**, board-tauglich knapp; redaktionelle Feinarbeit bleibt beim Menschen.

## Implementierung

| Teil | Pfad |
|------|------|
| Typen & Outline | `frontend/src/lib/boardReadinessBriefingTypes.ts` |
| Generierung & Markdown | `frontend/src/lib/boardReadinessBriefingGenerate.ts` |
| Baseline-Store | `frontend/src/lib/boardReadinessBriefingSnapshotStore.ts` |
| API Briefing | `frontend/src/app/api/admin/board-readiness/briefing/route.ts` |
| API Baseline | `frontend/src/app/api/admin/board-readiness/briefing/baseline/route.ts` |
| UI | `frontend/src/components/admin/BoardReadinessBriefingPanel.tsx` (eingebunden in `BoardReadinessClient`) |

Siehe ergänzend: `docs/board/wave34-board-readiness-dashboard.md` (Datenquellen der Indikatoren).
