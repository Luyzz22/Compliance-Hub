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

Der Index (0–100) und das API-Level (`low` / `medium` / `high`) werden in den **jeweiligen Services** aus der Datenlage abgeleitet. Das Contract-Modul definiert **Enums, Labels**, Parser `normalize_index_level` sowie **Dokumentations-Bänder** für OAMI (Regression).

**OAMI-Index → API-Level** (wie `operational_monitoring_index._level_from_index`; Snapshot: `contract_full_oami_mapping_snapshot()`):

| Index (ganzzahlig 0–100) | Typischer API-Level |
|--------------------------|---------------------|
| &lt; 40 | `low` |
| 40–69 | `medium` |
| ≥ 70 | `high` |

Hilfsfunktion (Tests/Docs): `derive_oami_level_from_index(index)` — **nicht** zur Überschreibung des serverseitigen OAMI-Levels im Explain-Flow verwenden.

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

### 4.3 Golden Samples (Referenz-JSON für Tests & Reviews)

Unter `tests/fixtures/readiness_explain_golden/` liegen **drei** vollständige Modell-Response-Beispiele (ohne Markdown), die die erwartete Struktur und erlaubte Enums illustrieren:

| Datei | Szenario | Score (Beispiel) | `level` (API) | DE-Label (UI) |
|-------|----------|------------------|---------------|---------------|
| `response_a_basic.json` | Viele strukturelle Lücken | ~44 | `basic` | Basis |
| `response_b_managed.json` | Etablierte Basis, Restarbeiten | ~68 | `managed` | Etabliert |
| `response_c_embedded.json` | Hohe Reife, Feintuning | ~88 | `embedded` | Integriert |

**Feldinhalt (für GRC- und Engineering-Reviews):**

- **`short_reason`:** 1–3 Sätze Einordnung ohne erfundene Stufen-Synonyme; beschreibt Ursachen auf Deutsch.
- **`drivers_positive`:** kurze Bullet-Sätze zu vorhandenen Stärken (max. 5 Einträge à ≤ 200 Zeichen).
- **`drivers_negative`:** priorisierte Maßnahmen / Lücken (gleiche Limits).
- **`regulatory_focus`:** ein Satz Bezug zu EU AI Act, NIS2, ISO/IEC 42001/27001 — ohne Paragraphenzitate.

Die Dateien sind **canonical fixtures** für `tests/test_readiness_explain_golden_regression.py`. Bei Schema- oder Enum-Änderungen: Golden-Dateien und Tests **gemeinsam** anpassen (bewusster Review).

**Beispiel (Auszug Sample A — vollständig siehe Fixture):**

```json
{
  "readiness_explanation": {
    "score": 44,
    "level": "basic",
    "short_reason": "…",
    "drivers_positive": ["…"],
    "drivers_negative": ["…", "…"],
    "regulatory_focus": "…"
  },
  "operational_monitoring_explanation": null
}
```

### 4.4 Golden Samples: OAMI-Block (`operational_monitoring_explanation`)

Unter `tests/fixtures/oami-explain/` liegen **drei** vollständige Beispiele mit **Readiness- und OAMI-Block** (ohne Markdown). Sie spiegeln Niedrig/Mittel/Hoch beim operativen Monitoring und die erlaubten Index-Level-Enums.

| Datei | Szenario (kurz) | OAMI-Index (Beispiel) | `level` (API) | DE-Label (UI) |
|-------|-----------------|------------------------|---------------|---------------|
| `response_low.json` | Kaum Daten, ungeklärte Vorfälle | ~28 | `low` | Niedrig |
| `response_medium.json` | Monitoring sichtbar, einige Incidents | ~55 | `medium` | Mittel |
| `response_high.json` | Kontinuierliche Beobachtung, wenige Incidents | ~85 | `high` | Hoch |

**Regression der Index-Bänder:** `tests/fixtures/governance_maturity_oami_mapping_snapshot.json` muss `contract_full_oami_mapping_snapshot()` entsprechen (siehe Abschn. 9).

**Tests:** `tests/test_oami_explain_golden_regression.py` (inkl. kombinierter Readiness+OAMI-Strukturtest und Fallback bei ungültigem OAMI-`level`).

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
| Enums, Labels, Limits, Version, `contract_full_mapping_snapshot()`, `contract_full_oami_mapping_snapshot()`, `derive_oami_level_from_index` | `app/governance_maturity_contract.py` |
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
6. **Tests:** `tests/test_governance_maturity_contract.py`, `tests/test_readiness_explain_structured.py`, `tests/test_readiness_explain_prompt.py`, `tests/test_readiness_explain_golden_regression.py`, `tests/test_oami_explain_golden_regression.py` anpassen.
7. **Fixtures:** `tests/fixtures/governance_maturity_mapping_snapshot.json`, `tests/fixtures/governance_maturity_oami_mapping_snapshot.json`, `tests/fixtures/readiness_explain_golden/*.json` und `tests/fixtures/oami-explain/*.json` bei Band- oder Golden-Änderungen aktualisieren.

---

## 9. Tests (Referenz)

- **Mapping-Dateien:** `governance_maturity_mapping_snapshot.json` ≡ `contract_full_mapping_snapshot()`; `governance_maturity_oami_mapping_snapshot.json` ≡ `contract_full_oami_mapping_snapshot()` (CI bricht bei Drift).
- **Golden-Regression Readiness:** `tests/test_readiness_explain_golden_regression.py` — Parser, Snapshot-Ausrichtung, erlaubte Keys, Whitespace-Toleranz, Prompt-Struktur (Version + Mandantenfakten).
- **Golden-Regression OAMI:** `tests/test_oami_explain_golden_regression.py` — OAMI-Block, DE-Label-Konsistenz, ungültiges `level` → Server-Fallback, kombinierter Readiness+OAMI-Check.
- **Contract:** `contract_mapping_for_tests()` / Readiness-Bänder vs. `derive_readiness_level_from_score`; OAMI-Bänder vs. `derive_oami_level_from_index` und Abgleich mit `operational_monitoring_index._level_from_index`.
- **Prompt:** alle API-Werte und DE-Labels aus den Maps; keine parallele Hardcode-Liste.
- **Parser:** ungültige `level`-Strings, fehlende Blöcke (`test_readiness_explain_structured.py`).

Demo-Script: `docs/demo-board-ready-walkthrough.md`.

---

## 10. Optional: LLM-Smoke (nicht in CI)

Vor größeren Releases kann ein **manueller** Lauf gegen ein echtes Modell die JSON-Treue prüfen (nur in Nicht-Produktion, mit gültigen API-Keys):

1. Mandanten-DB mit bekanntem Readiness-Snapshot wählen.
2. `explain_readiness_score(session, tenant_id, snapshot)` aufrufen (oder HTTP `POST …/readiness-score/explain` mit Tenant-Header).
3. Rohantwort: ein JSON-Objekt ohne Markdown; `readiness_explanation.level` ∈ `{basic, managed, embedded}`.
4. Logs / Export für menschliche Kurzreview (Tonfall DE, keine wilden Stufenlabels).

**Hinweis:** Kein separates Skript-Pflicht — wer automatisieren will, kann ein kleines `python -c "…"` oder ein internes Notebook nutzen, das `build_readiness_explain_prompt` + Router nur bei gesetzten Keys ausführt.
