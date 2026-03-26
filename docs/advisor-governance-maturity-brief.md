# Advisor Governance-Maturity-Brief

## Beziehung zum Board-`GovernanceMaturitySummary`

| Artefakt | Rolle |
|----------|--------|
| **`GovernanceMaturitySummary`** (`app/governance_maturity_summary_models.py`) | Kanonischer Kern: Readiness-, GAI- und OAMI-Slice plus `overall_assessment` (Levels, Treiber, Kurztexte). Wird im Board-Report per LLM befüllt und an den **Mandanten-Snapshot** aus `GET …/governance-maturity` ausgerichtet (`align_governance_maturity_summary_to_snapshot`). |
| **`AdvisorGovernanceMaturityBrief`** (`app/advisor_governance_maturity_brief_models.py`) | **Spezialisierung:** enthält **dieselbe** verschachtelte Struktur `governance_maturity_summary` wie der Board-Kern und erweitert sie um Berater-Felder: `recommended_focus_areas`, `suggested_next_steps_window`, optional `client_ready_paragraph_de`. |

Die UI und Integrationen sollen **strukturierte Felder** (Enums, Listen) nutzen, nicht das Layout von LLM-Fließtext.

**JSON-Schema-Hinweise für das LLM:** `advisor_governance_maturity_brief_json_schema_instructions()` in `app/governance_maturity_contract.py` (Schema-Version `ADVISOR_GOVERNANCE_MATURITY_BRIEF_SCHEMA_VERSION`). Die Governance-Maturity-**Contract-Version** (`GOVERNANCE_MATURITY_CONTRACT_VERSION`) bleibt für Enums und Terminologie maßgeblich.

## Backend-Flow

- **Prompt:** `build_advisor_governance_maturity_brief_prompt(snapshot, board_summary | None)` — optionaler Board-Kern nur zur inhaltlichen Konsistenz, ohne neue Fakten.
- **Parse / Align:** `parse_advisor_governance_maturity_brief` → Kern wie beim Board an den Snapshot anbinden; Advisor-Felder aus JSON übernehmen (Listen gekappt wie im Contract).
- **LLM-Task:** `LLMTaskType.ADVISOR_GOVERNANCE_MATURITY_BRIEF` (Feature-Gate: `governance_maturity` + `llm_enabled`).
- **Fallback ohne LLM:** `build_fallback_advisor_governance_maturity_brief_parse_result` — heuristische `recommended_focus_areas`.
- **Einbindung:** Advisor-Portfolio (`governance_maturity_advisor_brief`), Mandanten-Snapshot-API, Markdown-Steckbrief (`render_tenant_report_markdown`), KI-Snapshot-Markdown (Präfix-Abschnitt vor LLM-Fließtext).

Hinweis: Ist `COMPLIANCEHUB_FEATURE_LLM_ENABLED` aktiv, kann pro Mandant im Portfolio **ein zusätzlicher LLM-Aufruf** für den Brief entstehen (Triaging). Ohne LLM nutzt das System den deterministischen Fallback.

## Beispiel JSON (Mandant mit niedrigem OAMI)

```json
{
  "governance_maturity_summary": {
    "readiness": {
      "score": 52,
      "level": "managed",
      "short_reason": "Register und Rollen sind angelegt; High-Risk-Lücken werden noch geschlossen."
    },
    "activity": {
      "index": 48,
      "level": "medium",
      "short_reason": "Steuerungsartefakte werden genutzt; Tiefe der Dokumentation variiert."
    },
    "operational_monitoring": {
      "index": 28,
      "level": "low",
      "short_reason": "Wenige belastbare Laufzeit-Signale im Fenster."
    },
    "overall_assessment": {
      "level": "low",
      "short_summary": "Konservatives Gesamtbild: operatives Monitoring begrenzt die Einordnung nach unten.",
      "key_risks": ["Laufzeit-Transparenz", "Nachweisbarkeit bei Incidents"],
      "key_strengths": ["Aktive Nutzung der Plattform für Steuerung"]
    }
  },
  "recommended_focus_areas": [
    "OAMI niedrig – Monitoring und Alarmierung für High-Risk-Systeme ausbauen",
    "Readiness – offene Essential-Controls bei High-Risk schließen"
  ],
  "suggested_next_steps_window": "nächste 90 Tage",
  "client_ready_paragraph_de": "Aus Sicht der KI-Governance empfehlen wir, operatives Monitoring und die offenen High-Risk-Nachweise in den nächsten drei Monaten zu priorisieren; wir unterstützen Sie gern bei der Umsetzung."
}
```

## Beispiel Markdown-Abschnitt (Steckbrief / Export)

Der Block wird von `render_advisor_governance_maturity_brief_markdown_section` erzeugt und in den Mandanten-Steckbrief sowie optional vor den KI-Snapshot-Markdown gesetzt:

```markdown
## Governance-Reife – Kurzüberblick

**Gesamtbild (konservativ):** low

Konservatives Gesamtbild: operatives Monitoring begrenzt die Einordnung nach unten.

**Empfohlene Fokusbereiche**

- OAMI niedrig – Monitoring und Alarmierung für High-Risk-Systeme ausbauen
- Readiness – offene Essential-Controls bei High-Risk schließen

**Vorgeschlagener Zeithorizont:** nächste 90 Tage

Aus Sicht der KI-Governance empfehlen wir, operatives Monitoring und die offenen High-Risk-Nachweise in den nächsten drei Monaten zu priorisieren; wir unterstützen Sie gern bei der Umsetzung.
```

## Tests

- `tests/test_advisor_governance_maturity_brief_parse.py` — Parse, Align, Fallback, Markdown, Prompt-Marker.
- `tests/test_governance_maturity_contract.py::test_advisor_brief_json_schema_instructions_shape` — Contract-String.
- Fixture: `tests/fixtures/advisor_governance_maturity_brief_golden/response_ok.json`.
