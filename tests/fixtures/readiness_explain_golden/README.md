# Golden samples: Readiness-Explain (LLM JSON)

Diese Dateien sind **Referenz-JSONs** für `POST …/readiness-score/explain` (Modell-Output vor Parser).

- `response_a_basic.json` — niedrige strukturelle Reife (Score ~44, Level `basic`).
- `response_b_managed.json` — etablierte Basis (Score ~68, Level `managed`).
- `response_c_embedded.json` — hohe Reife (Score ~88, Level `embedded`).

**Regeln:** Nur erlaubte `level`-Enums; Freitext Deutsch; `operational_monitoring_explanation` hier `null` (Tests ohne OAMI-Kontext).

Bei Schema- oder Enum-Änderungen: Golden-Dateien und `tests/test_readiness_explain_golden_regression.py` anpassen.
