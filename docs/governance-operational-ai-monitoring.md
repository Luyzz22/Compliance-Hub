# Operational AI Monitoring – SAP AI Core Events, Datenmodell & OAMI

**ComplianceHub** – Architektur- und Integrationsreferenz für **Laufzeit- und Post-Market-Signale** aus **SAP AI Core** (über **SAP BTP**), Anbindung an **KI-Register**, **KPI-Modell** und **Governance Maturity Lens** (Operational AI Monitoring Index, **OAMI**).

**Regulatorik (explizit):**

| Konzept | Norm / Artikel | Rolle in diesem Design |
|---------|----------------|-------------------------|
| Post-Market-Monitoring | **EU AI Act** Art. 72 ff. | Erfassung und Auswertung von Vorfällen und Überwachungssignalen nach Inverkehrbringen (Hochrisiko-Kontext). |
| Schwere Vorfälle / Meldewege | EU AI Act (Meldepflichten je nach Klassifizierung) | `event_type=incident` + `severity`; **keine** automatische Rechtsqualifikation in ComplianceHub. |
| Überwachung & Verbesserung | **ISO/IEC 42001** (AI-MS) | Laufzeitmetriken, Änderungskontrolle, Incident-Learning. |
| Incident Handling | **NIS2** | Erkennung, Reaktion, Dokumentation auf aggregierter Ebene. |
| Datenminimierung | **DSGVO** | Nur technische Metadaten und Aggregationen, **keine** Roh-Inhalte von Prompts/Outputs aus SAP. |

**Verwandte Dokumente:**

- [`governance-maturity-lens.md`](./governance-maturity-lens.md) – OAMI als dritte Säule neben Readiness und GAI.  
- [`governance-telemetry.md`](./governance-telemetry.md) – Workspace-Telemetrie (getrennt von Laufzeit-KI-Events).  
- [`governance-activity-index.md`](./governance-activity-index.md) – GAI.

---

## 1. Kanonisches Event-Modell (provider-neutral, SAP-first)

### 1.1 Envelope: `AiRuntimeEvent` (logisch / API-Ingest)

Alle eingespielten Laufzeit-Events werden in **eine** kanonische Form normalisiert (JSON), bevor sie persistiert werden.

| Feld | Typ | Pflicht | Beschreibung |
|------|-----|---------|--------------|
| `event_id` | string (UUID) | ja | Idempotenz-Schlüssel (von Quelle oder von ComplianceHub generiert). |
| `tenant_id` | string | ja | ComplianceHub-Mandant (RLS). |
| `ai_system_id` | string | ja | FK zu `ai_systems.id` (Register); Mapping aus SAP-Deployment/Resource-ID über Konfigurationstabelle. |
| `source` | string (enum) | ja | Ursprung, z. B. `sap_ai_core`, `sap_btp_event_mesh`, `manual_import`, `other_provider`. |
| `event_type` | string (enum) | ja | Siehe 1.2. |
| `severity` | string (enum) | empfohlen | `info`, `low`, `medium`, `high`, `critical` (einheitlich für Incidents und Metrik-Alarme). |
| `occurred_at` | string (ISO 8601 UTC) | ja | Zeitpunkt des Geschehens an der Quelle (nicht nur Ingress-Zeit). |
| `ingested_at` | string (ISO 8601 UTC) | ja | Zeitpunkt des Schreibens in ComplianceHub. |
| `metric_key` | string \| null | nein | Kanonischer KPI-Schlüssel (Alignment mit `AiKpiDefinitionDB.key` wo möglich), z. B. `drift_score`, `error_rate`, `safety_violation_count`. |
| `incident_code` | string \| null | nein | Stabiler Code aus SAP oder intern, z. B. `AICORE_DEPLOYMENT_FAILURE`, `THRESHOLD_BREACH_DRIFT`. |
| `value` | number \| null | nein | Aktueller Messwert (aggregiert). |
| `delta` | number \| null | nein | Änderung ggü. vorherigem Stand / Baseline. |
| `threshold_breached` | boolean \| null | nein | Explizit bei `metric_threshold_breach`. |
| `context` | object | nein | **Strikt whitelist** (siehe 1.3). |

**Nicht erlaubt im Payload:** Freitextbeschreibungen mit personenbezogenen Daten, Roh-Prompts, Roh-Outputs, vollständige Stack Traces mit Hostnamen von Endnutzern.

### 1.2 `event_type` – Kanon + Regulatorik-Mapping

| `event_type` | Bedeutung | EU AI Act / ISO 42001 Zuordnung (fachlich) |
|--------------|-----------|---------------------------------------------|
| `incident` | Betriebsvorfall oder sicherheits-/sicherheitsrelevanter Zwischenfall an der KI-Laufzeit | **Post-Market-Monitoring**; ggf. Meldepflichten (qualifiziert extern); **NIS2** Incident Response |
| `metric_threshold_breach` | Messgröße hat definierten Schwellenwert überschritten (Drift, Fehlerquote, Safety-KPI) | **Leistungsüberwachung**, Robustheit, ISO 42001 **Überwachung und Messung** |
| `deployment_change` | Ausrollen, Rollback, neue Modellversion, Konfigurationsänderung | **Änderungsmanagement**, Konfigurationskontrolle; stützt EU AI Act **Dokumentation und Rückverfolgbarkeit** |
| `heartbeat` | Optional: „Monitoring aktiv“, Datenfreshness | Nachweis **kontinuierlicher Überwachung** (Metadaten-only) |
| `metric_snapshot` | Periodischer KPI-Punkt ohne Alarm | Befüllung von **KPI-Zeitreihen** im Register |

### 1.3 `context` – Whitelist (Beispiele)

Nur flache, technische Schlüssel (analog `workspace_telemetry`‑Denke):

- `environment` – z. B. `prod`, `staging` (enum/string, max. Länge).  
- `deployment_version` / `model_version` – technische Versions-ID (kein Freitext-Essay).  
- `region` – z. B. `eu-de`, `eu-central-1`.  
- `sap_resource_name` – technischer Ressourcenname (ohne personenbezogene Teile).  
- `correlation_id` – technische Korrelation zwischen SAP-Events.

Erweiterungen nur nach **Security + DPO** Review in zentraler Allowlist.

### 1.4 Cross-Regulation Graph (Einordnung)

Runtime-Events werden **nicht** als neue „Pflichten“ im Graph gespeichert, sondern:

- **Verknüpfung** über `ai_system_id` zu bestehenden Anforderungen (EU AI Act Art. 9–15, ISO 42001 A.8 Monitoring, NIS2 Art. 21/23) in **Reports** und **Board-Ansichten** als Evidenz-Typ `ai_runtime_event` / `operational_monitoring`.  
- Optionale Tabelle **Evidence-Link** (bestehendes Muster NormEvidence) kann auf aggregierte „Monitoring aktiv“-Nachweise zeigen.

---

## 2. Persistenzmodell (Postgres / Supabase)

### 2.1 Tabelle `ai_runtime_events`

| Spalte | Typ | Index | Beschreibung |
|--------|-----|-------|--------------|
| `id` | uuid, PK | PK | Intern. |
| `tenant_id` | text, NOT NULL | ja (composite) | RLS. |
| `ai_system_id` | text, NOT NULL, FK → `ai_systems.id` | ja | Register. |
| `event_id` | text, NOT NULL | UNIQUE (tenant_id, event_id) | Idempotenz. |
| `source` | text, NOT NULL | | |
| `event_type` | text, NOT NULL | ja | |
| `severity` | text | | |
| `occurred_at` | timestamptz, NOT NULL | ja | |
| `ingested_at` | timestamptz, NOT NULL | | |
| `metric_key` | text | | |
| `incident_code` | text | | |
| `value` | double precision | | |
| `delta` | double precision | | |
| `threshold_breached` | boolean | | |
| `payload_json` | jsonb | GIN optional | Nur kanonisiertes `context` + feste Felder, die nicht in Spalten liegen. |

**RLS:** `tenant_id` = aktueller Mandant; Advisor-Zugriff über bestehende Advisor-Policies.

### 2.2 Tabelle `ai_runtime_incident_summaries`

Materialisierte oder nächtlich aktualisierte **Aggregate** pro System und Fenster (Board-tauglich, weniger Zeilen).

| Spalte | Typ | Beschreibung |
|--------|-----|--------------|
| `id` | uuid, PK | |
| `tenant_id` | text | |
| `ai_system_id` | text, FK | |
| `window_start` | timestamptz | |
| `window_end` | timestamptz | |
| `incident_open_count` | int | |
| `incident_acknowledged_count` | int | |
| `incident_resolved_count` | int | |
| `critical_or_high_count` | int | |
| `mean_time_to_ack_hours` | float \| null | Nur wenn Zeitstempel ohne PII vorliegen. |
| `last_event_at` | timestamptz | |
| `computed_at` | timestamptz | |

### 2.3 Anbindung an `ai_system_kpi_values`

- **Inkrementell:** Bei `metric_snapshot` oder `metric_threshold_breach` mit `metric_key` → Upsert in `ai_system_kpi_values` (bestehendes Periodenmodell), `source = 'sap_ai_core'` (oder Enum-Erweiterung).  
- **Incidents:** Zähler-KPIs (z. B. `incidents_open_count`) aus `ai_runtime_incident_summaries` oder On-the-fly Aggregation für Dashboards.  
- **Kein** automatisches Überschreiben manueller KPIs ohne Regel (z. B. `source`-Priorität konfigurierbar).

---

## 3. Operational AI Monitoring Index (OAMI)

### 3.1 Ziel

Pro **`ai_system_id`** und aggregiert pro **`tenant_id`**: ein **0–100** Index mit Level **`low` | `medium` | `high`**, der **Datenabdeckung**, **Incident-Handling** und **KPI-Stabilität** abbildet – **ohne** Black-Box-ML.

### 3.2 Teilscores (0–1, sättigend) – Systemebene

Fenster z. B. **30 / 90 Tage** (`window_days`).

| Teil | Messgröße | Skizze |
|------|-----------|--------|
| **Freshness** \(s_F\) | Letztes `occurred_at` oder `heartbeat` jünger als \(T_1\) Tage | 1.0 wenn ≤3d, linear bis 0 bei ≥14d ohne Signal |
| **Coverage** \(s_C\) | Anteil der „überwachten“ Metrik-Slots mit ≥1 Snapshot im Fenster / erwartete Slots (aus Konfig) | Sättigung bei 100% |
| **Incident hygiene** \(s_I\) | Verhältnis resolved+acknowledged zu eröffnet; Strafe für offene `high/critical` über SLA | Monoton, cap |
| **Stability** \(s_S\) | Anzahl `metric_threshold_breach` / `critical` incidents, normalisiert und gedeckelt | Höhere Stabilität = weniger Breaches |

Beispiel-Gewichtung (kalibrierbar):

\[
\mathrm{OAMI}_{0\_1}^{\mathrm{(sys)}} = 0{,}25\, s_F + 0{,}25\, s_C + 0{,}35\, s_I + 0{,}15\, s_S
\]

\[
\mathrm{OAMI}^{\mathrm{(sys)}} = \mathrm{round}(100 \cdot \mathrm{OAMI}_{0\_1}^{\mathrm{(sys)}})
\]

**Level:** wie GAI: 0–39 low, 40–69 medium, 70–100 high – oder an KPI-Schwellen für Hochrisiko-Systeme gekoppelt (Policy).

### 3.3 Tenant-Aggregation

- **Einfach:** Mittelwert über Systeme mit `risk_level` in Scope (z. B. high + limited).  
- **Risikogewichtet:** Gewicht \(\propto\) EU-AI-Act-Risikoklasse / internem `criticality`.  
- **Minimum-Regel:** „Tenant-OAMI darf nicht höher als X sein, wenn ein Hochrisiko-System `OAMI_sys < Y`“ – optional für konservative Board-Darstellung.

### 3.4 Kein Datenfluss = expliziter Status

Wenn **keine** BTP/AI-Core-Anbindung: `operational_monitoring.status = not_configured`, Index `null`, Narrativ aus Maturity Lens.

---

## 4. Integration Governance Maturity Lens & APIs

### 4.1 Einordnung

| Säule | Inhalt |
|-------|--------|
| Readiness | Struktur |
| GAI | Nutzung ComplianceHub |
| **OAMI** | **Laufzeitrealität** SAP AI Core / ähnliche Quellen |

### 4.2 `GET /api/v1/ai-systems/{ai_system_id}/monitoring-index`

**Response (Skizze):**

```json
{
  "ai_system_id": "…",
  "tenant_id": "…",
  "window_days": 90,
  "operational_monitoring_index": 62,
  "level": "medium",
  "components": {
    "freshness": 0.85,
    "coverage": 0.6,
    "incident_hygiene": 0.55,
    "stability": 0.58
  },
  "source_status": "active",
  "last_runtime_event_at": "2026-03-20T10:00:00Z",
  "computed_at": "2026-03-25T12:00:00Z"
}
```

### 4.3 `GET /api/v1/tenants/{tenant_id}/governance-maturity` (Erweiterung)

Block `operational_ai_monitoring` statt nur Placeholder:

```json
"operational_ai_monitoring": {
  "status": "active",
  "index": 58,
  "level": "medium",
  "window_days": 90,
  "systems_with_low_index": 2,
  "last_computed_at": "2026-03-25T12:00:00Z"
}
```

### 4.4 Narrative Tags (ergänzend zu Maturity Lens)

| Tag-ID | Bedingung (vereinfacht) |
|--------|-------------------------|
| `operational_monitoring_not_configured` | Keine BTP-Quelle |
| `operational_monitoring_strong` | Tenant-OAMI ≥ 70 |
| `operational_monitoring_gap` | Readiness hoch, OAMI niedrig |
| `runtime_incidents_attention` | Offene high/critical > 0 |

Kombination mit bestehenden Tags (z. B. `structurally_strong_low_usage`) für **Board-Satzbausteine**.

---

## 5. SAP BTP / SAP AI Core – Integrationsmuster

### 5.1 Option A: Event-getrieben (empfohlen skalierbar)

1. **SAP Integration Suite / Event Mesh** oder AI Core **Webhooks** (HTTPS) → **dedizierter Ingest-Endpoint** in ComplianceHub (`POST /api/v1/integrations/sap-ai-core/events`) mit **mTLS oder OAuth2** Client-Credentials (BTP → ComplianceHub).  
2. **Transformation** in Kanon-Schema (Mapping-Tabelle `sap_resource_id` → `ai_system_id`, `tenant_id`).  
3. Schreiben in `ai_runtime_events` + optional **async** KPI-Update.

**Vorteil:** Nahezu Echtzeit, gut für Incidents.

### 5.2 Option B: Geplanter Abruf (n8n / Job)

1. **n8n** (self-hosted, DSGVO-konform betrieben) mit **SAP BTP Destination** Service: periodischer GET auf AI Core Monitoring APIs.  
2. Normalisierung und **signierter** Callback an ComplianceHub Ingest-API oder direkter DB-Write durch vertrauenswürdigen Worker (nicht empfohlen ohne API).

**Vorteil:** Einfacher Start ohne Event-Mesh.

### 5.3 Sicherheit & Minimierung

- **Secrets** nur in BTP / ComplianceHub Secret Store; keine Keys im Frontend.  
- **Tenant-Isolation:** Mapping-Config pro Mandant; keine globalen SAP-IDs ohne Zuordnung.  
- **Daten:** nur numerische/enum Felder laut Schema; **Redaction** bei Quellen, die mehr liefern.  
- **Audit:** Ingest-Logs ohne Payload-Inhalt oder nur gehashter `event_id`.

### 5.4 Architektur (Board-tauglich)

```text
[SAP AI Core] → [BTP: Event Mesh / Integration / n8n] → [ComplianceHub Ingest API]
                                                      → ai_runtime_events
                                                      → KPI upsert
                                                      → OAMI compute
                                                      → governance-maturity API
```

---

## 6. Implementierungs-Phasen

| Phase | Inhalt |
|-------|--------|
| **P0** | DDL `ai_runtime_events`, Ingest-API, manuelle Test-Events, System-OAMI Read-API. |
| **P1** | `ai_runtime_incident_summaries` Job, Tenant-OAMI, `governance-maturity` erweitert. |
| **P2** | BTP Destination + erste Event-Quelle; Mapping-UI für SAP→Register. |
| **P3** | Board/Advisor UI, Evidence-Links im Cross-Reg-Report. |

---

## 7. Verwandte Code-Pfade (Ist-Zustand)

| Bereich | Datei / Tabelle |
|---------|-----------------|
| AI-Systeme | `app/models_db.py` → `AISystemTable` |
| KPI-Werte | `AiKpiDefinitionDB`, `ai_system_kpi_values` |
| Workspace-Telemetrie (getrennt) | `app/services/workspace_telemetry.py` |

---

*Version: 1.0 – Spezifikation für SAP AI Core Post-Market-Signale und OAMI; Implementierung nur nach Security/DPO-Freigabe für konkrete SAP-Payloads.*
