# Berater-Portfolio: Priorisierung und Filter

Diese Notiz richtet sich an **Berater** und Product/UX. Sie beschreibt die regelbasierte Priorität, die Standard-Sortierung und die Filter auf der Advisor-Portfolio-Seite – ohne versteckte Scores.

## Prioritätsstufen (Hoch / Mittel / Niedrig)

Die API berechnet pro Mandant ein **Prioritäts-Bucket** und einen kurzen deutschen Erklärungstext (`advisor_priority_explanation_de`). Die Logik ist deterministisch und orientiert sich an:

- **Readiness-Level** (Basis / Etabliert / Integriert), ggf. abgeleitet aus EU-AI-Act-Readiness, wenn kein Readiness-Score geliefert wird.
- **GAI** (Governance Activity Index) und **OAMI** (Operational AI Monitoring Index) auf Niedrig / Mittel / Hoch.
- **Reife-Szenario-Hinweis A–D**, sofern die Kennzahlen exakt einem Golden-Szenario entsprechen.

### Regeln (Kurzfassung)

| Priorität | Typische Situation |
|-----------|-------------------|
| **Hoch** | Szenario **A** oder **B**, oder Readiness noch Basis/Etabliert **und** OAMI fehlt bzw. ist niedrig (vorsichtige Annahme). |
| **Niedrig** | Szenario **D** oder alle drei Säulen auf hohem Niveau (integriert + hohes GAI + hohes OAMI). |
| **Mittel** | Alles dazwischen, z. B. solide Readiness aber noch Luft bei GAI oder OAMI. |

Fehlen **GAI und OAMI** komplett, bleibt die Priorität bewusst **neutral mittel** mit erklärendem Text (keine Überinterpretation).

## Szenario A–D (Zuordnung)

Die Zuordnung zu A–D folgt den **Golden-Fixtures** (exakte Muster). Liegt keine exakte Übereinstimmung vor, ist `maturity_scenario_hint` leer; die Priorität kommt dann aus den allgemeinen Regeln oben.

## UI: Spalten und Badges

| Spalte | Inhalt |
|--------|--------|
| **Priorität** | Badge „Hoch“ (dezentes Rosé), „Mittel“ (Bernstein), „Niedrig“ (Slate). Optional **Sz. A–D** darunter. **Tooltip** = API-Begründung. |
| **Schwerpunkt** | Kompaktes Tag (z. B. „Monitoring“, „Readiness“) aus `primary_focus_tag_de`. **Tooltip** = erster Eintrag aus `recommended_focus_areas`, falls vorhanden. |

Link **Snapshot anzeigen** enthält `?highlight=governance-maturity`, damit im Governance-Snapshot der **Reife-Brief** sanft in den Fokus rutscht und kurz hervorgehoben wird.

## Sortierung und Filter

- **Standard-Sortierung:** höchste Berater-Priorität zuerst (`advisor_priority_sort_key`), danach **Mandantenname** aufsteigend.
- **Schnellfilter „Aufbau / Monitoring“:** hohe Priorität oder Szenario A/B.
- **Schnellfilter „Optimierung“:** niedrige Priorität oder Szenario D.
- **Regulatorik:** NIS2-relevant · KRITIS-Sektor gepflegt · Vorfälle in 90 Tagen (siehe [advisor-priority-nis2-kritis.md](./advisor-priority-nis2-kritis.md)).
- **Säulen-Fokus:** Readiness · Governance-Aktivität (GAI) · Monitoring (OAMI) – filtert nach Heuristik/Schwerpunkt und Levels.
- **Szenario:** Dropdown A–D.
- **Nur hohe Priorität:** schmale Liste für das nächste Beratungsfenster.

## Pseudo-Tabelle (Beispiel-Portfolio)

| Mandant | Regulatorik | Priorität | Schwerpunkt | GAI | OAMI | Kurzlogik für den Berater |
|---------|-------------|-----------|-------------|-----|------|---------------------------|
| Alpha GmbH | NIS2 wesentl. | Hoch · Sz. A | Readiness | Niedrig | Niedrig | Grundlagen zuerst |
| Beta AG | KRITIS, Vorfälle | Hoch · Sz. B | Monitoring | Hoch | Niedrig | Monitoring + Meldewege |
| Gamma SE | — | Mittel | Nutzung | Mittel | Mittel | Einzelhebel gezielt |
| Delta KG | — | Niedrig · Sz. D | Governance | Hoch | Hoch | Pflege / Optimierung |

*(Screenshot: in der Produkt-Doku ergänzen, sobald UI final freigegeben ist.)*

## Verwandte Dokumente

- Struktur und Felder des **Governance-Maturity-Briefs**: [advisor-governance-maturity-brief.md](./advisor-governance-maturity-brief.md).
- Backend-Implementierung: `app/services/advisor_portfolio_priority.py`, Anreicherung in `app/services/advisor_portfolio.py`.
