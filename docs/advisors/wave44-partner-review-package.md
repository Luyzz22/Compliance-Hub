# Wave 44 – Kanzlei Partner-Review-Paket

Kompaktes **Portfolio-Artefakt** für interne Partnerrunden, vierteljährliche Mandanten-Steuerung und wiederkehrende Portfolio-Reviews. Es ist weder ein Mandanten-Einzeldossier noch ein Board-/Gründungs-Pack.

## Paketstruktur

| Teil | Inhalt |
|------|--------|
| **A – Portfolio-Überblick** | Mandantenzahl, Readiness-Verteilung, Zähler für überfällige Reviews/Exporte/Board-Berichte, Summe offener Prüfpunkte, Größe der Attention-Queue, offene Reminder (gesamt, heute/überfällig, Kalenderwoche). |
| **B – Top Attention-Mandanten** | Die ersten *N* Einträge der bestehenden Attention-Queue (typisch 5–10) mit **Warum jetzt?** und **Nächster Schritt** – identisch zur Cockpit-Logik (Wave 41). |
| **C – Veränderungen seit letzter Periode** | Nutzt dieselbe **Monats-Baseline** wie der Kanzlei-Monatsreport (`data/kanzlei-monthly-report-baseline.json` bzw. `KANZLEI_MONTHLY_REPORT_BASELINE_PATH`): Verbesserungen, Verschlechterungen/Mehrlast, neu dringlicher (Attention-Eskalation + Kadenz-Hinweise). Ohne Baseline ist dieser Block erklärend leer. |
| **D – Empfohlene Prioritäten** | Kurze, aggregierte Handlungsempfehlungen für den nächsten Monat/Quartal (gleiche Fokus-Heuristik wie Monatsreport Abschnitt 4). |

## API

- **`GET /api/internal/advisor/partner-review-package`**
  - Auth: wie andere Advisor-Interna (`LEAD_ADMIN_SECRET` + Lead-Admin-Cookie).
  - Query:
    - `compare=0` – kein Vergleich mit Baseline (Teil C ohne Inhalt außer Hinweis).
    - `top_n` – Anzahl Top-Mandanten in Teil B (3–15, Standard 8).
    - `format=markdown` – Antwort als **Markdown-Datei** (`Content-Disposition: attachment`) statt JSON.
  - JSON-Antwort: `partner_review_package` (strukturiert), `markdown_de`, kompaktes `meta`.

## Priorisierung (transparent)

Reihenfolge und Inhalte leiten sich aus bestehenden Signalen ab (keine neue „Black Box“):

1. **Review-Kadenz** – überfälliges oder fehlendes Kanzlei-Review (Historie Wave 40) erhöht Dringlichkeit und fließt in Attention-Score, Queue und Auto-Reminder (Wave 43).
2. **Export-Kadenz** – Readiness-Export / DATEV-ZIP zu alt oder nie erfasst; gleiche Schwellen wie Portfolio (`KANZLEI_ANY_EXPORT_MAX_AGE_DAYS` etc.).
3. **Hohe Lückenlast** – viele offene Prüfpunkte, hohe Dringlichkeit, „viele Punkte ohne frischen Export“ (Gap-Heavy-Regel).
4. **Säulen-Ampeln** – rot/gelb/grün je Pillar; rote Säule qualifiziert für Queue und Fokustexte.
5. **Überfällige Reminder** – offene Reminder mit Fälligkeit heute oder in der Vergangenheit werden im Überblick ausgewiesen.
6. **Attention-Queue** – Sortierung nach Score, dann offenen Punkten, dann Label (Mandant); Details in `docs/advisors/wave41-kanzlei-review-playbook-and-queue.md`.

Die API liefert zusätzlich `meta.prioritization_rationale_de` als Kurzliste für Partner.

## Abgrenzung

| Artefakt | Zweck |
|----------|--------|
| **Partner-Review-Paket (Wave 44)** | Ein **Sitzungs-Paket** für Partner/Steuerung: Überblick, Top-Fälle, Delta seit Baseline, Prioritätenliste. |
| **Monatsreport (Wave 42)** | Periodischer Sammelreport inkl. optionaler Baseline-Pflege; ähnliche Datenbasis, anderer Fokus (Periode, Report-Schema). |
| **Mandanten-Readiness-Export / DATEV-Bundle** | **Pro Mandant** – Detail für Akte und Mandantengespräch. |
| **Board-Pack / Board-Readiness** | **Vorstand/Organ** – anderes Publikum und Tiefe. |

## Nutzung in der Kanzlei

- **Partner-Meeting:** Teil A + B in 10–15 Minuten durchgehen; Teil D als To-do-Backlog für die kommenden Wochen.
- **Quartals-Review:** Baseline zuvor setzen (Monatsreport „Baseline speichern“ oder gleiche Datei), dann Paket mit `compare=1` erzeugen – Teil C liefert die Delta-Narrative.
- **Laufende Steuerung:** Häufiger als Monatsreport; Markdown in Wiki/Teams/Notion kopieren.

## Siehe auch

- `docs/advisors/wave43-reminders-and-followups.md`
- `docs/advisors/wave42-kanzlei-monatsreport.md`
- `docs/advisors/wave41-kanzlei-review-playbook-and-queue.md`
