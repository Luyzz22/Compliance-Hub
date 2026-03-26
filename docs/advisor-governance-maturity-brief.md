# Advisor Governance-Maturity-Brief

## Kanonische Berater-Szenarien (A–D)

Für Regression und Qualitätssicherung sind **vier Profile** definiert (siehe `tests/fixtures/advisor-governance-maturity-brief/README.md`):

| ID | Readiness / GAI / OAMI | Konservatives Gesamt | Nutzen für den Berater |
|----|-------------------------|----------------------|-------------------------|
| **A** | basic / low / low | low | Grundlagen: Register, Steuerungsnutzung, Monitoring aufbauen |
| **B** | managed / high / low | low | Monitoring und Laufzeit-Signale nachziehen |
| **C** | embedded / medium / medium | medium | Nutzung verbreitern, Monitoring harmonisieren |
| **D** | embedded / high / high | high | Feintuning, Skalierung, kontinuierliche Überwachung |

- **JSON (Fake-LLM):** `tests/fixtures/advisor-governance-maturity-brief/scenario_{a,b,c,d}_llm.json`
- **Markdown-Goldens (Brief-Abschnitt):** `tests/fixtures/advisor-tenant-report-markdown/scenario_{a,b,c,d}_brief_section.md`
- **Snapshots (Readiness/GAI/OAMI-Zahlen):** `tests/advisor_brief_scenario_snapshots.py`

Die Auswertung entspricht dem **Board-Kern**: gleiche API-Enums (`basic`/`managed`/`embedded`, `low`/`medium`/`high`), konservatives Gesamtlevel als Minimum der Säulen. Der Berater-Brief ergänzt **Fokuslisten** und **Mandantentext**, ohne neue messbare Fakten neben dem Snapshot zu erfinden.

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

## Beispiel JSON – Szenario A (Grundlagen, Auszug)

Vollständige Datei: `tests/fixtures/advisor-governance-maturity-brief/scenario_a_llm.json`. Kurzfassung:

```json
{
  "recommended_focus_areas": [
    "Readiness: KI-Register und Rollen konsistent führen; offene Nachweise zu High-Risk-Systemen schließen.",
    "GAI: Steuerungsprozesse in der Plattform verankern (Reviews, Freigaben, dokumentierte Nutzung).",
    "OAMI: Mindestens für High-Risk-Systeme Monitoring und Incident-Runbooks vorbereiten."
  ],
  "suggested_next_steps_window": "nächste 90 Tage",
  "client_ready_paragraph_de": "Für die kommenden drei Monate empfehlen wir, die Grundlagen der KI-Governance zu schließen …"
}
```

Der Block `governance_maturity_summary` in derselben Datei wird beim Parsen an den Snapshot angeglichen; Enums und Zahlen im Export folgen der API, nicht dem rohen LLM-JSON.

## Beispiel JSON – Szenario B (Monitoring nachziehen, Auszug)

Datei: `scenario_b_llm.json`. Typische Fokuszeile:

```json
{
  "recommended_focus_areas": [
    "OAMI priorisieren: KPI-Zeitreihen, Incidents und Runbooks für High-Risk-Systeme ausbauen.",
    "Readiness-Lücken bei High-Risk parallel schließen, damit Monitoring auf saubere Stammdaten aufsetzt."
  ],
  "suggested_next_steps_window": "nächste 90 Tage"
}
```

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

Der Block wird von `render_advisor_governance_maturity_brief_markdown_section` erzeugt und in den Mandanten-Steckbrief sowie optional vor den KI-Snapshot-Markdown gesetzt.

**Referenz-Goldens pro Szenario:** `tests/fixtures/advisor-tenant-report-markdown/scenario_{a,b,c,d}_brief_section.md`

Beispiel (Szenario B, gekürzt — Monitoring-Schwerpunkt):

```markdown
## Governance-Reife – Kurzüberblick

**Gesamtbild (konservativ):** low

Struktur und Steuerungsnutzung sind gestärkt; das konservative Gesamtbild wird jedoch durch begrenztes Laufzeit-Monitoring nach unten gezogen. …

**Empfohlene Fokusbereiche**

- OAMI priorisieren: KPI-Zeitreihen, Incidents und Runbooks für High-Risk-Systeme ausbauen.
- Readiness-Lücken bei High-Risk parallel schließen, damit Monitoring auf saubere Stammdaten aufsetzt.

**Vorgeschlagener Zeithorizont:** nächste 90 Tage

Ihre organisatorische und prozessuale Steuerung ist auf einem guten Weg; sinnvoll ist jetzt, operatives Monitoring …
```

Älteres Beispiel (generischer Low-OAMI-Fall) zur Einordnung:

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
- `tests/test_advisor_brief_golden_scenarios.py` — Szenarien A–D: Fake-LLM-JSON, konservatives Level, Markdown-Goldens, Einbettung im Mandanten-Steckbrief.
- `tests/test_governance_maturity_contract.py::test_advisor_brief_json_schema_instructions_shape` — Contract-String.
- Legacy-Fixture: `tests/fixtures/advisor_governance_maturity_brief_golden/response_ok.json`.

## Siehe auch

- Portfolio-Priorität, Sortierung, Filter und Deep-Link in den Snapshot: [`advisor-portfolio-prioritization.md`](./advisor-portfolio-prioritization.md).
- NIS2/KRITIS/Incident-Aufstock der Priorität: [`advisor-priority-nis2-kritis.md`](./advisor-priority-nis2-kritis.md).
