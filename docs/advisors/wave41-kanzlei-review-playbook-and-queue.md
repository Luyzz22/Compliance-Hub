# Wave 41 – Kanzlei-Review-Playbook & Attention-Queue

Erweiterung der Advisor-Oberfläche um eine **leichte operative Schicht**: Kanzleien sehen, **welche Mandanten zuerst an der Reihe sind**, **warum**, und **welcher nächste Schritt** sinnvoll ist – plus ein **kurzes Review-Playbook** auf den Mandanten-bezogenen Admin-Seiten. **Kein** Workflow-Engine, **kein** Task-System; nur Ableitung aus bestehenden Portfolio- und Historien-Signalen.

## Attention-Queue

- **Ort:** `/admin/advisor-portfolio` (Kanzlei-Cockpit), rechts neben dem Playbook-Block.
- **Inhalt:** Liste der Mandanten, die **Queue-Kriterien** erfüllen, sortiert wie die Portfolio-Tabelle (**Attention-Score** absteigend, dann offene Punkte, dann Name).
- **API:** Feld `attention_queue` im Payload von `GET /api/internal/advisor/kanzlei-portfolio` (Payload-Version **`wave41-v1`**).

### Eintrittskriterien (regelbasiert)

Ein Mandant erscheint in der Queue, wenn der **Attention-Score mindestens 1** ist **und** mindestens eine der folgenden Bedingungen gilt:

| Bedingung | Bedeutung |
|-----------|-----------|
| API nicht lesbar | `api_fetch_ok === false` |
| Review überfällig / nie | `review_stale` (siehe Wave 40, typ. 90 Tage) |
| Export-Kadenz | `any_export_stale` (kein/junger Export, siehe Wave 40) |
| Board-/Statusbericht | `board_report_stale` |
| Viele Lücken ohne Export | `gaps_heavy_without_recent_export` (Schwelle offene Punkte + stale Export) |
| Viele offene Prüfpunkte | `open_points_count ≥ KANZLEI_MANY_OPEN_POINTS` (Standard 4) |
| Hohe Dringlichkeit | mindestens ein offener Punkt mit hoher Dringlichkeit |
| Rote Säule | mindestens eine Readiness-Säule rot |
| Kumuliert | Attention-Score **≥ 22** ohne eine der harten Bedingungen (fangt „viele kleine“ Signale ein) |

Implementierung: `frontend/src/lib/kanzleiAttentionQueue.ts` (`rowQualifiesForAttentionQueue`).

### „Warum jetzt?“ (`warum_jetzt_de`)

Bis zu **vier** kurze deutsche Sätze, priorisiert (technisch blockierend → Kadenz → Umfang → Ampel → Pilot). Sie fassen die **gleichen Signale** wie die Portfolio-Zeile zusammen, aber in **Lesesätzen** für die tägliche Arbeit – nicht identisch mit den technischen `attention_flags_de` der Tabelle.

### „Nächster Schritt“ (`naechster_schritt_de`)

Eine **einzige** empfohlene Maßnahme, aus einer **festen Prioritätskette** (z. B. zuerst API, dann „Export vor Gespräch“ bei schweren Lücken ohne frischen Export, dann Kadenz-Export, Board-Report, Review, Säulen-Fokus, Pilot-Baseline). **Keine** KI, **keine** Persistenz – bei erneutem Laden kann sich der Text ändern, wenn sich Daten geändert haben.

Implementierung: `naechsterSchrittForRow` in `kanzleiAttentionQueue.ts`.

## Review-Playbook (in der App)

Vier kurze Schritte (statisch), überall gleich:

1. **Status und Artefakte** – Ampel, überfällige Berichte/Exports, Historie.
2. **Offene Prüfpunkte** – nach Säule clustern, Gespräch vorbereiten.
3. **Export bei Bedarf** – Readiness oder DATEV-ZIP.
4. **Review abschließen** – Historie setzen, optional Notiz.

**Dynamische Zeilen** (optional): z. B. Anzahl offener Punkte, Alter des letzten Exports, Review-/Board-Signale – wenn Daten vorliegen (`KanzleiReviewPlaybookHelper` mit `snapshot`).

**Einsatzorte:**

| Seite | Variante |
|-------|----------|
| Kanzlei-Cockpit | Playbook + Queue |
| Mandanten-Export | Playbook + Snapshot + „Nächster Schritt“ wenn Portfolio-Zeile geladen |
| Board Readiness | Kompaktes Playbook + Verweis auf Cockpit/Mandanten-Export |

Komponente: `frontend/src/components/admin/KanzleiReviewPlaybookHelper.tsx`.

## Wöchentliche / monatliche Zyklen (Empfehlung)

- **Wöchentlich:** Queue von oben nach unten abarbeiten; pro Mandant Playbook durchgehen; Export ziehen wenn Kadenz oder DMS es braucht; **Review durchgeführt** setzen.
- **Monatlich:** Stichproben auch außerhalb der Queue (z. B. „grüne“ Mandanten mit wenig Punkten); Schwellen in `kanzleiReviewCadenceThresholds.ts` bei Bedarf anpassen.

## Siehe auch

- `docs/advisors/wave40-kanzlei-review-cadence-and-history.md`
- `docs/advisors/wave39-kanzlei-portfolio-cockpit.md`
- `frontend/src/lib/kanzleiPortfolioScoring.ts` (Attention-Score)
