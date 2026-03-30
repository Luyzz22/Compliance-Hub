# Advisor tenant report – E2E golden scenarios

End-to-end fixtures for the **Markdown Steckbrief** pipeline: Governance-Maturity-Brief (after `apply_drilldown_alignment_to_brief`), **Risiko-/Incident-Lage**, and **System- und Lieferanten-Drilldown**.

| Ordner | Zweck |
|--------|--------|
| `safety_dominant_case/` | Managed Readiness, mittleres GAI/OAMI, Laufzeit-Drilldown mit Safety-Treiber (System A) und Availability-Treiber (System B); NIS2 wichtige Einrichtung, hohe Incident-Last im Risiko-Abschnitt. |
| `benign_low_case/` | Basic/low/low Maturity, sehr wenige Laufzeit-Incidents; Fokus Monitoring-Abdeckung, Drilldown-Text „wenige Incidents“, kein System-Fokus im Mandantenabsatz. |

**Tests:** `tests/test_advisor_report_e2e_safety_dominant.py`

Änderungen an `apply_drilldown_alignment_to_brief`, `render_risiko_incident_lage_markdown_section`, `build_incident_system_supplier_drilldown_section` oder `render_tenant_report_markdown` sollten gegen diese Szenarien geprüft werden; bei bewussten Textanpassungen die erwarteten `.md`-Fragmente und `expected_assertions.json` mitaktualisieren.
