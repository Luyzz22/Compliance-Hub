# Governance-Maturity: Copy- und API-Vertrag (Backend ↔ Frontend)

Ziel: **stabile Enums**, **nachvollziehbare LLM-Ausgaben** und **ein gemeinsames Vokabular** mit dem Board-UI — ohne dass Backend und Frontend auseinanderlaufen.

**Single source of truth (Backend, maschinenlesbar):** `app/governance_maturity_contract.py`  
**Spiegel Frontend (TS-Typen):** `frontend/src/lib/governanceMaturityTypes.ts`  
**Deutsche UI-Texte:** `frontend/src/lib/governanceMaturityDeCopy.ts`  
**Menschliche Begriffstabelle:** `docs/governance-maturity-copy-de.md`

---

## 1. Contract-Version

| Feld | Wert | Zweck |
|------|------|--------|
| `GOVERNANCE_MATURITY_CONTRACT_VERSION` | siehe `governance_maturity_contract.py` | Wird in LLM-Prompts (`Explain-Contract-Version`) und Tests gesnapshottet. Bei Änderung am JSON-Schema oder an erlaubten Enums **Version erhöhen** und Frontend/Docs/Tests anpassen. |

---

## 2. Enum-Definitionen (API)

Diese Strings sind die **einzigen** erlaubten Werte in strukturiertem JSON (`level`-Felder) und in REST-Payloads für die genannten Konzepte.

### 2.1 AI & Compliance Readiness

| API (`level`) | Bedeutung (fachlich) | DE-Label (nur UI) |
|---------------|----------------------|-------------------|
| `basic` | Strukturelle Reife niedrig; viele Setup- / Coverage-Lücken | Basis |
| `managed` | Etablierte Governance-Strukturen, mittlere Reife | Etabliert |
| `embedded` | Hohe strukturelle Verankerung über Dimensionen hinweg | Integriert |

**Python:** `ReadinessLevelApi`, Tuple `READINESS_API_LEVELS`, Map `READINESS_LEVEL_DE`.

### 2.2 Governance-Aktivität (GAI) & Operatives Monitoring (OAMI)

| API (`level`) | Bedeutung (fachlich) | DE-Label (nur UI) |
|---------------|----------------------|-------------------|
| `low` | Signal niedrig / wenig Aktivität bzw. wenig sichtbare Laufzeitdaten | Niedrig |
| `medium` | Mittlere Ausprägung | Mittel |
| `high` | Starke Ausprägung | Hoch |

**Python:** `GovernanceActivityLevelApi`, `OperationalMonitoringLevelApi` (gleiche Werte), `INDEX_API_LEVELS`, `INDEX_LEVEL_DE`.

---

## 3. Abbildung: numerisch → Enum → DE-Label

### 3.1 Readiness Score (0–100) → `level`

Der **autoritative** Level-Wert für APIs und Explain-Ausrichtung kommt aus dem Readiness-Service (`ReadinessScoreResponse.level`).  
Zur **Dokumentation** der üblichen Bänder (wie im Score-Service):

| Score (ganzzahlig 0–100) | Typischer API-Level |
|---------------------------|---------------------|
| &lt; 45 | `basic` |
| 45–69 | `managed` |
| ≥ 70 | `embedded` |

Hilfsfunktion (Tests/Docs): `derive_readiness_level_from_score(score)` im Contract-Modul — **nicht** zur Überschreibung des serverseitigen Levels im Explain-Flow verwenden.

### 3.2 GAI / OAMI (0–100 Index)

Es gibt **keinen** zweiten „numerischen Level-Typ“ im Contract: der Index (0–100) und das API-Level (`low`/`medium`/`high`) werden in den **jeweiligen Services** aus der Datenlage abgeleitet. Das Contract-Modul definiert nur **Enums und Labels** sowie Parser `normalize_index_level`.

### 3.3 DE-Labels

| API | DE (muss mit `governanceMaturityDeCopy` übereinstimmen) |
|-----|--------------------------------------------------------|
| `basic` | Basis |
| `managed` | Etabliert |
| `embedded` | Integriert |
| `low` | Niedrig |
| `medium` | Mittel |
| `high` | Hoch |

---

## 4. JSON-Schema (LLM Output): Readiness Explain

Antwort **ein** JSON-Objekt, kein Markdown. Felder:

### 4.1 `readiness_explanation` (Pflicht, sofern JSON gültig)

| Feld | Typ | Regeln |
|------|-----|--------|
| `score` | int 0–100 | Wird serverseitig an Snapshot angeglichen (Anti-Drift). |
| `level` | string | Nur `basic` \| `managed` \| `embedded`. Ungültige Werte → Log + Fallback auf Snapshot-Level. |
| `short_reason` | string | Deutsch, kurz. |
| `drivers_positive` | string[] | max. 5 Einträge, je ≤ 200 Zeichen (`EXPLAIN_LIST_*`). |
| `drivers_negative` | string[] | wie oben (Maßnahmen / Risiken). |
| `regulatory_focus` | string | Kurz, z. B. Bezug EU AI Act / NIS2 / ISO 42001/27001. |

### 4.2 `operational_monitoring_explanation` (optional)

| Wert | Bedeutung |
|------|-----------|
| `null` | Kein OAMI-Kontext oder nicht relevant. |
| Objekt | Nur wenn Laufzeit-/OAMI-Kontext in den Fakten vorhanden ist. |

| Feld | Typ | Regeln |
|------|-----|--------|
| `index` | int \| null | 0–100 oder null. |
| `level` | string \| null | Nur `low` \| `medium` \| `high` oder null. Ungültig → Log + Fallback aus Server-OAMI-Level wenn möglich. |
| `recent_incidents_summary` | string | Deutsch, kurz. |
| `monitoring_gaps` | string[] | max. 5 × 200 Zeichen. |
| `improvement_suggestions` | string[] | max. 5 × 200 Zeichen. |

**Maschinelle Schema-Beschreibung für Prompts:** `readiness_explain_json_schema_instructions()` im Contract-Modul.

---

## 5. Regeln für LLM-Output

1. **Nur erlaubte Enum-Werte** in allen `level`-Feldern (englische API-Strings).
2. **Sprache:** Freitextfelder **Deutsch**; keine erfundenen Stufenbezeichnungen (kein „fortgeschritten“ statt `managed`/`embedded`).
3. **Keine neuen Labels** für Readiness/GAI/OAMI; regulatorisch nur der **standardisierte Kurzkontext** aus `regulatory_context_standard()`.
4. **Fakten:** Keine erfundenen Mandanten, Systeme oder Zahlen außerhalb des übergebenen JSON-Fakten-Blocks.
5. **Version:** Prompt enthält `Explain-Contract-Version` und Terminologie-Version — bei Schema-Änderungen Version bumpen.

---

## 6. Implementierung (Backend)

| Baustein | Datei / Funktion |
|----------|------------------|
| Enums, Labels, Limits, Version | `app/governance_maturity_contract.py` |
| Prompt-Zusammenbau (nur Contract + Fakten) | `app/services/readiness_explain_prompt.py` → `build_readiness_explain_prompt` |
| LLM-Aufruf | `app/services/readiness_score_explain.py` → `explain_readiness_score` |
| Parse / Validierung / Fallback | `app/services/readiness_explain_structured.py` → `parse_readiness_explain_llm_json`, `parse_and_validate_readiness_explain_response` |
| API-Modelle | `app/readiness_score_models.py` → `ReadinessScoreExplainResponse`, … |

**Fallback bei Parse-/Validierungsfehlern:** Rohtext oder `interpretation` als `explanation`; strukturierte Felder nur bei erfolgreicher Extraktion des `readiness_explanation`-Blocks (siehe Code).

---

## 7. Frontend-Konsum

- **Labels:** immer aus `governanceMaturityDeCopy` + Parsern (`parseReadinessLevel` / `parseIndexLevel` in TS) anhand der **API-Strings** aus der API.
- **KI-Text:** Inhalte aus `short_reason`, Listen, `regulatory_focus`, OAMI-Feldern anzeigen; Level-Zahlen **nicht** doppelt „übersetzen“, wenn `level` bereits gesetzt ist.

---

## 8. Change Management (Checkliste)

1. **Contract-Modul:** Enums / `READINESS_LEVEL_DE` / `INDEX_LEVEL_DE` / `EXPLAIN_LIST_*` / `readiness_explain_json_schema_instructions()` anpassen.
2. **`GOVERNANCE_MATURITY_CONTRACT_VERSION` erhöhen.**
3. **Dieses Dokument** + `docs/governance-maturity-copy-de.md` + ggf. `readiness-score.md` aktualisieren.
4. **Frontend:** `governanceMaturityTypes.ts`, `governanceMaturityDeCopy.ts`, `api.ts` DTOs.
5. **Pydantic:** `readiness_score_models.py` (Listenlängen, Literals).
6. **Tests:** `tests/test_governance_maturity_contract.py`, `tests/test_readiness_explain_structured.py`, `tests/test_readiness_explain_prompt.py` und Mapping-Snapshot anpassen.

---

## 9. Tests (Referenz)

- Contract- und Mapping-Snapshot: `contract_mapping_for_tests()`
- Prompt enthält alle API-Werte und DE-Labels aus den Maps (keine parallele Hardcode-Liste in Tests).
- Parser: gültige Golden-JSONs, ungültige `level`-Strings, fehlende Blöcke.

Demo-Script: `docs/demo-board-ready-walkthrough.md`.
