# Wave 39 – Mehrmandanten-Kanzlei-Cockpit

Interne **Portfolio-Übersicht** für **Steuerberater, Wirtschaftsprüfer und GRC-Berater**: alle **gemappten Mandanten** (wie Board Readiness) in **einer Tabelle**, mit Fokus auf die Frage **„Welcher Mandant braucht jetzt Kanzlei-Aufmerksamkeit?“** – ohne zusätzliches „Executive-Dashboard“-Design.

## Zielnutzer

- Kanzlei-Teams, die **viele Mandanten** in ComplianceHub begleiten.
- Advisor- und CS-Interna, die **Check-ins, Exporte und Nachsteuerung** planen.

## Wo finden?

- **UI:** `/admin/advisor-portfolio`
- **API:** `GET /api/internal/advisor/kanzlei-portfolio`
- **Auth:** wie Mandanten-Export / Board Readiness (`LEAD_ADMIN_SECRET` + Session über Lead-Inbox).

## Spalten (kompakt)

| Spalte | Inhalt |
|--------|--------|
| Mandant | Anzeigename aus GTM-Map, technische `tenant_id`, optional dominantes Segment (30-Tage-Leads) |
| Readiness | Wave-33-Klasse (`early_pilot` … `advanced_governance`) + Mini-Ampeln je Säule |
| Fokus-Säule | Säule mit den **gewichtet dringlichsten offenen Prüfpunkten**; ohne offene Punkte: **schlechteste Säule** aus Board-Readiness-Ampel |
| Bericht | **Überfällig**, wenn Hochrisiko-Systeme existieren und der Mandanten-/Board-Report nicht im Frischefenster liegt (wie Wave 37) |
| Offen | Anzahl **offener Prüfpunkte** (`computeMandantOffenePunkte`), in Klammern Anzahl **hoch** |
| Signale | Kurzliste **Kanzlei-Hinweise** (Export-Stale, Bericht, viele Punkte, Pilot-Baseline, API) + numerischer **Attention-Score** |
| Letzter Export / Review | Aus optionaler Datei `data/advisor-portfolio-touchpoints.json` (siehe unten); sonst **—** |
| Aktionen | Links zu **Mandanten-Export-UI** (mit `client_id`), **ZIP-Bundle-API**, **Board Readiness** |

## Filter

- **Readiness-Klasse** (alle oder eine Klasse).
- **Säule:** Mandanten, bei denen diese Säule **nicht grün** ist **oder** die Fokus-Säule der offenen Punkte entspricht.
- **Nur überfälliger Mandantenbericht.**
- **Viele offene Punkte** (Schwelle aus Payload, Standard **4**).

## Priorisierung (Sortierung)

Serverseitig absteigend nach **Attention-Score**, dann nach **Anzahl offener Punkte**, dann alphabetisch nach Mandantenbezeichnung.

Score (vereinfacht): gewichtet **hohe** vs. **mittlere** Prüfpunkte, **überfälliger Bericht**, **kein Export** im konfigurierten Zeitraum, **Pilot/Baseline**, **API nicht lesbar**, plus Zuschläge für **rote/gelbe Säulen**. Obergrenze 999 für stabile Darstellung.

**Export-Stale:** kein Eintrag `last_export_iso` **oder** älter als **45 Tage** (Konstante `KANZLEI_EXPORT_STALE_DAYS` im Code).

## Touchpoints (optional)

Datei **`data/advisor-portfolio-touchpoints.json`** (oder `ADVISOR_PORTFOLIO_TOUCHPOINTS_PATH`), Schema:

```json
{
  "entries": [
    {
      "tenant_id": "mein-mandant-001",
      "last_export_iso": "2026-03-15T10:00:00.000Z",
      "last_review_iso": "2026-03-20T14:00:00.000Z",
      "note_de": "Quartals-Check geplant"
    }
  ]
}
```

Keine automatische Befüllung in Wave 39: Kanzlei trägt manuell nach (oder späterer Hook nach Export).

## Aggregation (zentrale Logik)

- **Gemeinsame Mandanten-Ladung** mit Board Readiness: `loadMappedTenantPillarSnapshots` in `boardReadinessAggregate.ts` (eine API-Runde pro Mandant wie zuvor).
- **Portfolio-Zeilen:** `computeKanzleiPortfolioPayload` in `kanzleiPortfolioAggregate.ts`.
- **Offene Punkte / Säule:** `computeMandantOffenePunkte` + `pillarCodeForOpenPoint` in `tenantBoardReadinessGaps.ts`.

## Nutzung in wiederkehrenden Mandanten-Reviews

1. Cockpit laden, nach **höchstem Score** oben arbeiten.
2. **ZIP** oder **Readiness-Export** für den Mandanten ziehen und im DMS ablegen; optional Touchpoints-Datei pflegen.
3. **Board Readiness** für Portfolio-Ampel und Briefing nutzen; Cockpit für **operative Priorenliste** je Mandant.

## Unterschied zu Wave 37 / 38 / Board Readiness

| Wave | Fokus |
|------|--------|
| 37 | Ein Mandant, narrativer Export |
| 38 | Ein Mandant, ZIP-Arbeitspaket |
| 34–36 | Board-/Portfolio-Ampeln, Segmente, Pack |
| **39** | **Tabellarische Mehrmandanten-Priorität** für Kanzlei-Alltag |

## Siehe auch

- `docs/advisors/wave40-kanzlei-review-cadence-and-history.md` – Export-Historie, Review-Kadenz und verschärfte Attention-Regeln (ersetzt die reine Touchpoints-Datei für neue Installationen).
- `docs/advisors/wave37-mandant-readiness-export.md`
- `docs/advisors/wave38-datev-export-bundle.md`
- `docs/board/wave34-board-readiness-dashboard.md`
