# Golden fixtures: `operational_monitoring_explanation` (OAMI)

Vollständige Modell-JSON-Beispiele für den **Governance-Maturity-Explain**-Pfad, wenn OAMI-Kontext aktiv ist (`has_oami_context=True`). Zusammen mit `readiness_explanation` spiegeln sie die erwartete Struktur, erlaubten API-Enums (`low` \| `medium` \| `high`) und den deutschsprachigen Ton.

## Zweck

- **Regression:** Parser (`parse_and_validate_readiness_explain_response`) und Contract-Enums bleiben stabil.
- **Review:** Inhaltlich realistische Kurztexte für GRC-/Produkt-Reviews; bei Schema- oder Band-Änderungen Fixtures und Tests **gemeinsam** anpassen.

## Dateien

| Datei | Szenario | OAMI-Index (Beispiel) | API-`level` | DE-Label (UI) |
|-------|----------|------------------------|-------------|---------------|
| `response_low.json` | Kaum Monitoring-Signale, mehrere ungeklärte Vorfälle | ~28 | `low` | Niedrig |
| `response_medium.json` | Monitoring vorhanden, einige Incidents, größtenteils bearbeitet | ~55 | `medium` | Mittel |
| `response_high.json` | Kontinuierliche Beobachtung, wenige Incidents, schnelle Reaktion | ~85 | `high` | Hoch |

Die **Readiness**-Blöcke sind an die bestehenden Golden-Samples (`readiness_explain_golden`) angelehnt (Basis / Etabliert / Integriert), damit kombinierte End-to-End-Reviews ein konsistentes Bild erhalten.

**Mapping-Referenz (Index → Level):** `tests/fixtures/governance_maturity_oami_mapping_snapshot.json` bzw. `contract_full_oami_mapping_snapshot()` in `app/governance_maturity_contract.py`.

**Tests:** `tests/test_oami_explain_golden_regression.py`
