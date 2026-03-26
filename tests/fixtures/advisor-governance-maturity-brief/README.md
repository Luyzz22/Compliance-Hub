# Advisor Governance-Maturity-Brief – kanonische Szenarien (Golden)

Die JSON-Dateien `scenario_*_llm.json` simulieren **rohe LLM-Antworten** (ein JSON-Objekt). Beim Parsen werden `score` / `index` / `level` im Block `governance_maturity_summary` an den jeweiligen **Mandanten-Snapshot** angeglichen (`align_governance_maturity_summary_to_snapshot`); Fokuslisten, Zeithorizont und `client_ready_paragraph_de` werden aus dem JSON übernommen.

| ID | Profil (Readiness / GAI / OAMI) | Konservatives Gesamt-Level | Berater-Fokus (Kurz) |
|----|----------------------------------|----------------------------|----------------------|
| **A** | basic / low / low | low | Grundlagen: Register, Nutzung der Steuerung, Monitoring aufbauen |
| **B** | managed / high / low | low | Struktur und Nutzung stärker; **operatives Monitoring nachziehen** |
| **C** | embedded / medium / medium | medium | Reife insgesamt solide; **Nutzung vertiefen**, Monitoring weiter ausbauen |
| **D** | embedded / high / high | high | Hohe Reife; **Feintuning, Skalierung**, kontinuierliche Überwachung |

## Metriken (repräsentativ, je Szenario)

### A – „Grundlagen aufbauen“
- Readiness-Score **35**, Level **basic**
- GAI-Index **32**, Level **low**
- OAMI-Index **30**, Level **low** (aktiv, 90-Tage-Fenster)

### B – „Monitoring nachziehen“
- Readiness **58**, **managed**
- GAI **78**, **high**
- OAMI **34**, **low**

### C – „Nutzung verbreitern“
- Readiness **82**, **embedded**
- GAI **55**, **medium**
- OAMI **52**, **medium**

### D – „Feintuning & Skalierung“
- Readiness **90**, **embedded**
- GAI **82**, **high**
- OAMI **76**, **high**

## Markdown-Goldens

Die zugehörigen erwarteten Export-Fragmente (nur Abschnitt „Governance-Reife – Kurzüberblick“) liegen unter:

`tests/fixtures/advisor-tenant-report-markdown/scenario_*_brief_section.md`

Sie werden gegen die Ausgabe von `render_advisor_governance_maturity_brief_markdown_section` nach Parse + Align verglichen (Tests normalisieren Zeilenenden und trailing whitespace).
