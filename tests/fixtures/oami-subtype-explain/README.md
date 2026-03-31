# Golden fixtures: OAMI + `event_subtype` (S1–S3)

Synthetische Szenarien für **Tests, Regression und Demo-Skripte**: gleiche Gewichtungslogik wie Produktion (`app/oami_subtype_weights.py`, `operational_monitoring_index._components_from_agg`).

## Szenarien

| ID | Datei | Fokus | Erwarteter Index (Referenz) | Level |
|----|--------|------|----------------------------|--------|
| **S1** | `scenario_s1_safety_heavy.json` | Wenige Incidents, Schwerpunkt **safety_violation** + hohe Schwere | 65 | `medium` |
| **S2** | `scenario_s2_availability_heavy.json` | Mehr Incidents, überwiegend **availability_incident**, niedrigere Schwere | 60 | `medium` |
| **S3** | `scenario_s3_benign_low.json` | Wenige **other_incident**, viele leichte **performance_degradation**-Breaches, schwache Freshness/Coverage | 37 | `low` |

## Inhalt pro JSON

- **`oami_aggregate`**: Eingaben für `_components_from_agg` (ohne `last_occurred_at`; stattdessen **`last_event_age_days`** relativ zu einer festen `now` in den Tests).
- **`expected`**: `operational_monitoring_index`, `level` (API-Enum).
- **`readiness_explain_llm_json`**: Vollständiges Envelope wie vom Readiness-Explain-LLM (inkl. `operational_monitoring_explanation`) – für Parser-Regression.
- **`oami_enrichment`**: Optionale Server-Anreicherung (`safety_related_incidents_90d`, …) wie im Explain-Flow.
- **`governance_maturity_fragment`**: Kurztexte für Board/Berater (S1/S2), inhaltliche Keywords für Tests.
- **`presenter_script_de`**: Satz für Live-Demo (siehe `docs/demo-board-ready-walkthrough.md`).

**Hinweis:** Fließtexte dürfen sich leicht ändern; Tests prüfen **Schema/Enums**, **Index/Level** und **Schlüsselwörter** (z. B. „Sicherheit“, „Verfügbarkeit“), nicht wortgleiche Sätze.

## Verwandte Fixtures

- Allgemeine OAMI-Explain-Goldens ohne Subtype-Fokus: `tests/fixtures/oami-explain/`.
- Contract-Version: `GOVERNANCE_MATURITY_CONTRACT_VERSION` in `app/governance_maturity_contract.py`.

## Tests

`tests/test_oami_subtype_explain_golden.py`
