# Governance Activity Index (GAI)

**ComplianceHub** – Architektur- und Produktreferenz.  
Der **Governance Activity Index** misst **operative Nutzung von Governance-Oberflächen** (Telemetrie), nicht Modellgüte oder Einzelnutzer-Verhalten. Er ergänzt den **AI & Compliance Readiness Score** (strukturelle Reife) um einen **Nutzungs-/Operationalisierungs-Indikator**.

**Regulatorischer Rahmen:** DSGVO (Aggregation, keine PII), **ISO/IEC 42001** (AI-Managementsystem – Nachweis, dass Steuerungsprozesse **tatsächlich genutzt** werden), **ISO 27001** (Nutzung sicherheitsrelevanter Funktionen), **NIS2** (Überwachung/Steuerung digitaler Dienste), **EU AI Act** (Governance- und Dokumentationsprozesse im Alltag).

Siehe auch: [`governance-telemetry.md`](./governance-telemetry.md).

---

## 1. Ziele und Nicht-Ziele

| Ziel | Nicht-Ziel |
|------|------------|
| Erklärbare, monotone, **sättigende** Skala 0–100 | Machine Learning / individuelle User-Scores |
| Führungsgröße für Berater-Portfolio und Snapshots | Detailliertes Verhaltens-Tracking |
| Input für Readiness-Erklärung (LLM-Kontext) | Direkter Ersatz für den Readiness Score |
| Audit: dokumentierte Formel + Aggregat-only | „Gamification“ ohne Deckel |

---

## 2. Telemetrie-Inputs (Kanone)

Alle Auswertungen beziehen sich auf `usage_events` (bzw. gleichwertigen Log-Sink) mit den in der Telemetrie-Blueprint beschriebenen Payloads.

### 2.1 Relevante `event_type`-Werte

- `workspace_session_started` – Tages-Signal „Workspace aktiv“ (bereits 24h-Dedupe pro Event beim Schreiben; für **Distinct Days** siehe unten).
- `workspace_feature_used` – Nutzung definierter Governance-Features (`feature_name` in Payload).

### 2.2 Governance-`feature_name`-Menge (Kern-Set)

Für den GAI zählen nur Events mit `feature_name` in dieser Menge (UI- und API-Aliase explizit mappen):

| Kategorie | Erlaubte `feature_name`-Werte |
|-----------|-------------------------------|
| Playbook | `playbook_overview`, `ai_governance_playbook` |
| Cross-Regulation | `cross_regulation_summary`, `cross_regulation_dashboard` |
| Board / Reports | `board_reports_overview`, `board_report_detail` |
| KI-Register | `ai_system_detail` |
| Advisor | `advisor_governance_snapshot` |

**Implementierung:** zentrale Konstante `GAI_GOVERNANCE_FEATURE_NAMES: frozenset[str]` im Backend; bei neuen Features Product + Security Review, dann Erweiterung der Menge und dieses Dokuments.

### 2.3 Distinct-Activity-Days

**Problem:** `workspace_session_started` wird pro Tenant ggf. nur einmal pro 24h geschrieben → wenige Zeilen, aber „aktive Tage“ sind trotzdem sinnvoll.

**Definition *active day*:** Ein Kalendertag (UTC), an dem mindestens eines gilt:

- mindestens ein `workspace_session_started`, **oder**
- mindestens ein `workspace_feature_used` mit `feature_name ∈ GAI_GOVERNANCE_FEATURE_NAMES`.

So werden auch Tage erfasst, an denen nur Feature-Events ohne separates Session-Event vorkommen (z. B. rein API-getriebene Aufrufe).

---

## 3. Formel: Governance Activity Index (0–100)

**Fenster:** `window_days` ∈ `{30, 90}` (Standard für Anzeige: **90**; **30** für „letzter Monat“-Trend).

### 3.1 Rohgrößen (aggregiert, tenant-weit)

| Symbol | Bedeutung |
|--------|-----------|
| \(D\) | Anzahl **Distinct Active Days** im Fenster (UTC), max. `window_days`. |
| \(F\) | Anzahl `workspace_feature_used` mit Kern-`feature_name`, **gecappt**: \(F_{\mathrm{eff}} = \min(F, F_{\max})\), z. B. \(F_{\max} = 120\) über 90 Tage (≈1,3/Tag). |
| \(K\) | Anzahl **unterschiedlicher** Kern-Features mit mindestens einem Hit im Fenster, \(K \in [0, K_{\max}]\), \(K_{\max} = 5\) (eine pro Kategorie-Gruppe oben, Zählung distinct `feature_name` nach Normalisierung). |
| \(S\) | Anzahl `workspace_session_started` im Fenster (Rohzahl; für Engagement). |
| \(E\) | **Engagement-Ratio** (gecappt): \(E_{\mathrm{raw}} = F_{\mathrm{eff}} / \max(S, 1)\), \(E = \min(E_{\mathrm{raw}}, E_{\max})\), z. B. \(E_{\max} = 4\). |

### 3.2 Teilscores (jeweils 0–1, sättigend)

Alle Teilfunktionen sind **monoton wachsend** und ** konkav/sättigend** (diminishing returns), um reines „Event-Spamming“ zu begrenzen.

1. **Tageskontinuität**  
   \[
   s_D = \sqrt{\frac{D}{\min(window\_days,\, D_{\mathrm{sat}})}} \wedge 1}
   \quad\text{mit } D_{\mathrm{sat}} = 20 \text{ (90d) bzw. } 8 \text{ (30d)}.
   \]

2. **Feature-Volumen (gecappt)**  
   \[
   s_F = \sqrt{\frac{F_{\mathrm{eff}}}{F_{\mathrm{sat}}}} \wedge 1
   \quad\text{z. B. } F_{\mathrm{sat}} = 60 \text{ (90d)}.
   \]

3. **Diversität**  
   \[
   s_K = \frac{K}{K_{\max}}.
   \]

4. **Engagement (ohne Division-by-zero; gecappt)**  
   \[
   s_E = \sqrt{\frac{E}{E_{\mathrm{sat}}}} \wedge 1
   \quad\text{z. B. } E_{\mathrm{sat}} = 2.
   \]

### 3.3 Gewichtung und Gesamtindex

\[
\mathrm{GAI}_{0\_1} = 0{,}35\, s_D + 0{,}25\, s_F + 0{,}30\, s_K + 0{,}10\, s_E
\]

\[
\mathrm{GAI} = \mathrm{round}(100 \cdot \mathrm{GAI}_{0\_1}) \in [0, 100].
\]

**Begründung der Gewichte:** Kontinuität und **Diversität** (Breite der Governance-Nutzung) schwerer als reines Volumen; Engagement nur leicht – verhindert Dominanz bei wenigen intensiven Tagen mit vielen Sessions.

### 3.4 Qualitative Stufen (Levels)

| Level | GAI-Bereich | Bedeutung (Kurz) |
|-------|-------------|------------------|
| **low** | 0–39 | Geringe oder sporadische Nutzung der Governance-Oberflächen. |
| **medium** | 40–69 | Regelmäßige Nutzung, teilweise Breite über Features. |
| **high** | 70–100 | Ausgeprägte, breite und kontinuierliche Governance-Aktivität. |

Levels sind **reine Schwellen** auf dem Index – keine separaten ML-Modelle.

---

## 4. Datenmodell (minimal)

### 4.1 Persistierte Aggregate (empfohlen)

Tabelle z. B. `tenant_governance_activity_index` (oder Prefix `gai_`):

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `tenant_id` | text, PK | Mandant |
| `window_days` | int, PK | 30 oder 90 |
| `value_0_100` | int | GAI |
| `level` | text | `low` \| `medium` \| `high` |
| `components_json` | jsonb | Optional: `{ "s_D", "s_F", "s_K", "s_E", "D", "F_eff", "K", "S" }` für Transparenz |
| `last_computed_at` | timestamptz | Berechnungszeitpunkt |

**Hinweis:** Keine User-IDs, keine Roh-Event-IDs in der Aggregat-Tabelle nötig; `components_json` nur für Support/Debug und interne Audits.

### 4.2 Optional: Zeitreihe für Sparkline

Tabelle `tenant_gai_daily` oder wöchentliche Snapshots: `(tenant_id, bucket_date, gai_90d_rolling)` – **on-demand** berechenbar aus `usage_events` ohne Dauer-Speicher, oder nächtlich materialisiert.

---

## 5. Berechnungsservice (Skizze)

### 5.1 Signatur

```python
def compute_governance_activity_index(
    session: Session,
    tenant_id: str,
    *,
    window_days: int = 90,
    as_of: datetime | None = None,
) -> GovernanceActivityIndexResult:
    ...
```

### 5.2 `GovernanceActivityIndexResult` (Pydantic)

- `tenant_id: str`
- `window_days: int`
- `value_0_100: int`
- `level: Literal["low", "medium", "high"]`
- `components: GovernanceActivityIndexComponents` (optional öffentlich für „Warum dieser Score?“)
- `computed_at: datetime`
- `source: Literal["usage_events"]` (für spätere Log-Pipeline: `structured_log_replay`)

### 5.3 Datenbezug (`usage_events`)

**Aktueller Stand (Code):** `UsageEventTable.payload_json` ist **Text** – robuste Variante:

1. SQL: Zeilen mit `tenant_id`, `created_at_utc >= since`, `event_type IN (...)`.
2. Python: `json.loads` pro Zeile, Extraktion von `feature_name` aus Payload.

**Skalierung:** Bei großem Volumen: Migration zu **JSONB** + Index `((payload_json->>'feature_name'))` nur nach Privacy-Review; oder **nächtliche Aggregation** in `tenant_governance_activity_index`.

**Pseudo-SQL (wenn JSONB):**

```sql
-- Distinct active days (vereinfacht)
SELECT COUNT(DISTINCT (created_at_utc::date))
FROM usage_events
WHERE tenant_id = :tid
  AND created_at_utc >= :since
  AND (
    event_type = 'workspace_session_started'
    OR (event_type = 'workspace_feature_used'
        AND payload->>'feature_name' = ANY(:gai_features))
  );
```

### 5.4 Idempotenz / Cache

- API liest bevorzugt **letzte Zeile** `last_computed_at` wenn &lt; 1h alt (konfigurierbar).  
- Invalidierung bei Bedarf: TTL oder „compute on read“ für kleine Tenants.

---

## 6. Integration: Readiness Score

### 6.1 Rolle des GAI

- Der **Readiness Score** bleibt primär **strukturell** (Setup, Coverage, KPIs, Gaps, Reporting).  
- Der **GAI** ist ein **zusätzlicher, weicher** Indikator: **„Wird das Instrument auch bedient?“**

### 6.2 Vorschlag: Modifier (cap, nicht dominierend)

- Berechne bestehenden Score \(R \in [0,100]\) unverändert.  
- Berechne GAI \(G\).  
- **Angezeigter kombinierter Score (optional, nur UI/Explain):**  
  \[
  R_{\mathrm{adj}} = \mathrm{round}\bigl( R + \alpha \cdot (G - 50) \bigr) \quad \text{geclampt auf } [0,100],\ \alpha \approx 0{,}15.
  \]  
  Bei \(G=50\) keine Änderung; max. ±7,5 Punkte – **GAI gamet den Score nicht**.

**Alternative (konservativer):** GAI **nicht** in die Zahl mischen, sondern nur als **zweite KPI** und in der Erklärung ausgeben (empfohlen für erste Release).

### 6.3 Readiness-Explain (LLM)

`ReadinessScoreExplainResponse` / Prompt-Kontext erweitern um strukturierte Felder:

- `governance_activity_index: int`, `governance_activity_level: str`  
- Kurztext-Vorlage: *„Nutzungsindikator Governance (GAI): {value}/100 ({level}) – misst Nutzung von Playbook, Cross-Regulation, Board-Reports und KI-Register in den letzten {window_days} Tagen, ohne Einzelnutzer auszuwerten.“*

**Systemhinweis für das Modell:** GAI misst **Prozessnutzung** laut ISO-42001-Sinn, **keine** Modellperformance; niedriger GAI bedeutet nicht automatisch niedrige Compliance, kann auf wenig Login oder Batch-API-Nutzung hindeuten.

---

## 7. Integration: Advisor Portfolio & Snapshot

### 7.1 Advisor Portfolio (Tabellen-Spalte)

- Spalte **„Governance-Aktivität“**: Badge **3 Farben** (`low`=grau/amber, `medium`=blau, `high`=grün) + Tooltip mit **GAI 0–100** und Fenster „90 Tage“.  
- Optional: zweite Zeile klein **„30d-Trend ↑/→/↓“** aus Vergleich `GAI_30` vs. vorheriger Bucket (ohne Chart-Pflicht).

### 7.2 Advisor Governance Snapshot

- Abschnitt **„Operative Governance-Nutzung“**:  
  - große Zahl **GAI (90d)** + Level-Label  
  - **Sparkline** der letzten 13 Wochen (wöchentlicher Durchschnitt oder Rolling-GAI), falls materialisiert; sonst Text *„Keine Zeitreihe – nur Aktualwert.“*  
- Verknüpfung zur Telemetrie-Doku für Enterprise-Kunden (transparenz).

### 7.3 API-Erweiterung (skizziert)

- `GET /api/v1/tenants/{tenant_id}/governance-activity-index?window_days=90`  
- Advisor-Analog: `GET /api/v1/advisors/.../tenants/.../governance-activity-index` (gleiche Payload, RLS/Advisor-Link prüfen).

---

## 8. Governance, Audit, Datenschutz

| Aspekt | Umsetzung |
|--------|-----------|
| **Transparenz** | Diese Datei + `components_json` optional in API für berechtigte Rollen. |
| **DSGVO** | Nur Mandanten-Aggregate; keine personenbezogenen Telemetrie-Felder (siehe Telemetry-Blueprint). |
| **ISO 42001** | GAI = Nachweis **Nutzung** von AI-Governance-Prozessen, nicht Eignung der KI-Modelle. |
| **Nicht trivial gamen** | Caps auf \(F\), \(E\), Wurzel-Sättigung, hohes Gewicht auf **Diversität** \(K\). |
| **Revision** | Änderungen an Gewichten/Schwellen **Versionsdatum** in diesem Dokument + Changelog. |

---

## 9. Implementierungs-Reihenfolge (empfohlen)

1. Konstante `GAI_GOVERNANCE_FEATURE_NAMES` + `compute_governance_activity_index` + Unit-Tests (fixturierte `usage_events`).  
2. Persistenz `tenant_governance_activity_index` + Read-Path in Tenant-Readiness-Explain.  
3. Advisor Portfolio Spalte + Snapshot-Abschnitt.  
4. Optional: JSONB/Index oder Nacht-Job bei Last-Problemen.

---

## 10. Verwandte Artefakte

| Artefakt | Pfad |
|----------|------|
| Telemetrie-Blueprint | [`docs/governance-telemetry.md`](./governance-telemetry.md) |
| Usage Events Repo | `app/repositories/usage_events.py` |
| Readiness-Modelle | `app/readiness_score_models.py` |
| Readiness-Service / Explain | `app/services/readiness_score_service.py`, `readiness_score_explain.py` |
| Governance Maturity Lens (Readiness + GAI + OAMI-Roadmap) | [`docs/governance-maturity-lens.md`](./governance-maturity-lens.md) |
| Operational AI Monitoring (SAP AI Core, OAMI) | [`docs/governance-operational-ai-monitoring.md`](./governance-operational-ai-monitoring.md) |

---

*Version: 1.0 – GAI als fachliche Spezifikation; Abweichungen im Code nur nach explizitem Architektur-Update dieses Dokuments.*
