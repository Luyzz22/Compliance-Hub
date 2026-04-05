# Wave 42 – Kanzlei-Monatsreport / Sammelreport

Portfolio-weiter **Sammelbericht** für interne Kanzlei-Reviews, Partner-Termine und wiederkehrende Status-Mails – **kein** Board-Pack, **kein** Mandanten-Einzelreport. Fokus: **Ist-Zustand**, **Top-Aufmerksamkeit**, **grobe Veränderungen** seit einem gespeicherten Stichtag, **Handlungsschwerpunkte**.

## Report-Struktur (vier Abschnitte)

| Abschnitt | Inhalt |
|-----------|--------|
| **1) Portfolio-Überblick** | Anzahl Mandanten, Readiness-Verteilung, Zähler für überfällige Reviews/Exports/Board-Berichte, Summe offener Prüfpunkte, Größe der Attention-Queue |
| **2) Top-Aufmerksamkeit** | Die ersten *N* Einträge aus der bestehenden Attention-Queue (gleiche Priorisierung wie Wave 41) inkl. „Nächster Schritt“ |
| **3) Veränderungen seit Baseline** | Nur wenn **Baseline-Datei** existiert und **Vergleich** aktiv ist: verbesserte / zurückgefallene Readiness-Klasse, größere Bewegungen bei offenen Punkten (±2), Attention-Band, Ampel „schlechteste Säule“, Kadenz-Hinweise Review/Export |
| **4) Empfohlene Schwerpunkte** | Regelbasierte Bullet-Liste (EU AI Act, ISO 42001, NIS2, DSGVO, Export-/Review-Kadenz, API-Lesbarkeit, „viele Lücken ohne Export“) |

## API (intern, Lead-Admin)

| Methode | Pfad | Hinweise |
|---------|------|----------|
| `GET` | `/api/internal/advisor/kanzlei-monthly-report` | Wie andere Advisor-Routen: Session-Cookie oder Bearer/`?secret=` |

**Query-Parameter:**

| Parameter | Standard | Bedeutung |
|-----------|----------|-----------|
| `period` | aktueller Monat `YYYY-MM` | Nur **Beschriftung** in Report und beim Speichern der Baseline |
| `compare` | `1` (an) | `compare=0` schaltet Abschnitt 3 ab (Snapshot trotzdem nutzbar) |
| `update_baseline` | `0` | `update_baseline=1` **überschreibt** die Baseline-Datei mit dem **aktuellen** Portfolio-Snapshot |
| `top_n` | `10` | Anzahl Zeilen in Abschnitt 2 (3–25) |
| `kpi_window_days` | `90` | Wave 45: Fenster für KPI-Abschnitt 5 (7–365) |
| `kpi` | `1` | `kpi=0` schaltet Abschnitt 5 ab |

**Antwort:** `{ ok, report, markdown_de, baseline_updated }` – `report` ist strukturiertes JSON (`wave45-v1` inkl. optionalem Abschnitt 5), `markdown_de` für Kopieren in E-Mails oder Arbeitsmappen.

## Baseline & Change-Logik

- **Datei:** `data/kanzlei-monthly-report-baseline.json` (oder `KANZLEI_MONTHLY_REPORT_BASELINE_PATH`, auf Vercel unter `/tmp`).
- **Inhalt pro Mandant:** Readiness-Klasse, Attention-Score und **Band** (`low` &lt; 25, `medium` 25–54, `high` ≥ 55), offene Punkte, schlechteste Säulen-Ampel, Review-/Export-/Board-Stale-Flags, komplette Säulen-Ampeln.
- **Bewusst grob:** keine Einzel-Prüfpunkt-Historie, keine Zeitreihen-DB – nur **Snapshot vs. Snapshot**.
- **Typische Nutzung:** Monatsende Report erzeugen → **Baseline speichern** → nächsten Monat erneut Report mit Vergleich.

### Erkannte Änderungen (Auszug)

- Readiness: Reihenfolge `no_footprint` &lt; `early_pilot` &lt; `baseline_governance` &lt; `advanced_governance`.
- Offene Punkte: Meldung ab **Delta ±2**.
- Attention: Vergleich der **Bänder** (nicht jedes kleine Score-Ticken).
- Kadenz: Review/Export **von „im Zeitraum“ zu „stale“** und umgekehrt.
- Ampel: Verschlechterung/Verbesserung der **schlechtesten** Säule über alle vier Säulen.

Listen sind auf **12 Einträge** pro Kategorie begrenzt (Lesbarkeit).

## UI

- **Kanzlei-Cockpit** (`/admin/advisor-portfolio`): Block **„Monatsreport erstellen“**, Vorschau als Markdown, **Markdown kopieren**, Optionen Periode / Vergleich / Baseline speichern.

## Empfohlene Kadenz

- **Monatlich:** Report erzeugen, Markdown in interne Agenda; Baseline setzen wenn der Monat abgeschlossen ist.
- **Quartal:** Gleicher Ablauf mit Quartals-Label im Feld `period` (nur Label; Logik identisch).
- **Partner-Update:** Abschnitte 1–2 + Schwerpunkte reichen oft; Abschnitt 3 nur wenn Baseline gepflegt wird.

## Grenzen

- Kein PDF-Layout, keine Signatur, keine Archivierung im Produkt (Datei liegt auf dem Server/Filesystem).
- Ohne Baseline kein inhaltlicher **„Was hat sich geändert?“**-Teil – nur aktueller Querschnitt.
- API-Teilfehler pro Mandant können die Summen verzerren; `tenants_partial` im Portfolio bleibt sichtbar.

## Siehe auch

- `docs/advisors/wave45-advisor-kpis.md`
- `docs/advisors/wave44-partner-review-package.md`
- `docs/advisors/wave43-reminders-and-followups.md`
- `docs/advisors/wave41-kanzlei-review-playbook-and-queue.md`
- `docs/advisors/wave40-kanzlei-review-cadence-and-history.md`
