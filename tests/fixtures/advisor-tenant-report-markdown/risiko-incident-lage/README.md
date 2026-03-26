# Risiko- und Incident-Lage – Markdown-Goldens

Diese Dateien sind der **Abschnitt** `## Risiko- und Incident-Lage (NIS2/KRITIS)` wie von
`render_risiko_incident_lage_markdown_section` erzeugt (deterministisches Template).

| Datei | Profil |
|-------|--------|
| `case_c_outside_nis2_no_incidents.md` | Keine NIS2-Wichtig/Wesentlich-Einordnung, keine Vorfälle 90 Tage |
| `case_b_important_low_burden.md` | Wichtige Einrichtung, eine erfasste Vorfälle, Last mittel |
| `case_a_essential_kritis_high.md` | Wesentliche Einrichtung, KRITIS Energie, hohe Last, offene Vorfälle, Portfolio-Hinweis |

Vergleich in Tests mit normalisierten Zeilenenden (`rstrip` pro Zeile), analog zu
`tests/test_advisor_brief_golden_scenarios.py`.
