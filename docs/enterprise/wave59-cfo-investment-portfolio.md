# Wave 59 – CFO Investment Portfolio

## Zweck

Das CFO Investment Portfolio verdichtet vorhandene Enterprise-Signale zu einer
nachvollziehbaren Reihenfolge für Governance- und Connector-Investitionen:

- Welche Initiative ist entscheidungsreif?
- Welche Initiative muss zuerst validiert oder sequenziert werden?
- Wo verhindern Blocker oder fehlende Finance-Inputs eine belastbare Freigabe?

Die Funktion ist eine Entscheidungshilfe. Sie erteilt keine Budgetfreigabe und erzeugt
keine Finanzprognose.

## Deterministisches Modell

Jede Initiative verwendet vier sichtbare Faktoren:

| Faktor | Baseline-Gewicht |
| --- | ---: |
| Strategischer Wert | 30 % |
| Risikowirkung | 30 % |
| Ausführungssicherheit | 25 % |
| Kapitaleffizienz | 15 % |

Die Faktoren werden aus dem bestehenden Connector-Candidate-Scoring abgeleitet. Es gibt
keine Blackbox und keinen LLM-Aufruf.

## Entscheidungsklassen

- `fund_now`: hoher Portfolio-Score, belastbare Ausführungssicherheit, begrenzte Blocker
- `sequence`: attraktiv, aber in eine belastbare Delivery-Reihenfolge einzuordnen
- `validate`: Value-Hypothese, Readiness oder Finance-Input zuerst bestätigen
- `hold`: aktuell zu hohe Blocker oder bestehende `not_now`-Einordnung

## Finanzielle Grenzen

- Investment-Envelopes (`small|medium|large`) sind relative Komplexitätsbänder.
- Es werden keine Euro-Werte, Einsparungen oder vermiedenen Schäden erfunden.
- Jede Initiative bleibt `requires_finance_input=true` und `is_financial_estimate=false`.
- Finance Owner, Euro-Korridor und Capex-/Opex-Behandlung sind verbindliche Funding Gates.

## API und UI

- `GET /api/internal/enterprise/investment-portfolio`
- optional `include_markdown=true`
- tenant-scharf und nach Least Privilege über `view_executive_dashboard` geschützt
- Board-UI: `/board/investment-portfolio`

Die UI bietet kontrollierte Szenario-Linsen. Diese gewichten dieselben vier Faktoren neu,
speichern nichts und ändern keine Baseline- oder Freigabeentscheidung.
