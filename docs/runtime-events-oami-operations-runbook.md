# Runbook: AI-Runtime-Events, Ingest & OAMI (Betrieb)

Kurzanleitung für Betrieb und Piloten. Detaillierte Fachspezifikation: [`governance-operational-ai-monitoring.md`](./governance-operational-ai-monitoring.md).

## 1. Feature-Flags (ENV)

| Variable | Default (Code) | Wirkung |
|----------|----------------|---------|
| `COMPLIANCEHUB_FEATURE_GOVERNANCE_MATURITY` | `true` | Schaltet `GET .../governance-maturity` (Readiness + GAI + OAMI-Block). Bei `false`: HTTP 403. |

Weitere Flags (Board, Advisor-Snapshot, Readiness) bleiben wie in `app/feature_flags.py` dokumentiert; für OAMI im Board ist u. a. der Board-Report-Flag relevant.

## 2. Wichtige API-Pfade

| Methode | Pfad | Zweck |
|---------|------|--------|
| `POST` | `/api/v1/ai-systems/{ai_system_id}/runtime-events` | Batch-Ingest (Header `X-Tenant-Id` o. ä. wie in eurer Auth). |
| `POST` | `/api/v1/tenants/{tenant_id}/ai-systems/{ai_system_id}/runtime-events` | Alias mit explizitem Mandanten im Pfad. |
| `GET` | `/api/v1/ai-systems/{ai_system_id}/monitoring-index` | OAMI pro System (`window_days` Query, typisch 30/90). |
| `GET` | `/api/v1/tenants/{tenant_id}/operational-monitoring-index` | Tenant-OAMI. |
| `GET` | `/api/v1/tenants/{tenant_id}/governance-maturity` | Readiness + GAI + `operational_ai_monitoring`. |

**Idempotenz Ingest:** eindeutig über `(tenant_id, source, source_event_id)` in der Datenbank; Duplikate im Batch werden ebenfalls übersprungen.

**Demo-Mandanten (`tenants.is_demo`):** API-Ingest für Runtime-Events ist **gesperrt** (HTTP 403). Daten nur über kontrolliertes Seeding (siehe unten).

## 3. Logging (grep / Log-Aggregator)

Alle Meldungen über den Standard-Logger; Präfix im Log-Text zur einfachen Filterung:

### `runtime_events_ingest`

Pro abgeschlossenem Ingest (nach Commit oder bei leerem Insert ohne Commit):

```
runtime_events_ingest tenant_id=<id> ai_system_id=<id> inserted=<n> skipped_duplicate=<n> rejected_invalid=<n> kpi_updates=<n>
```

- Keine Roh-Payloads; nur Zähler und IDs.
- Hohe `rejected_invalid` bei stabilem Volumen: Integrations- oder Mapping-Fehler prüfen (Katalog `app/runtime_event_catalog.py`).

### `oami_compute`

Nach Tenant-OAMI-Berechnung:

- Ohne Events im Fenster:  
  `oami_compute tenant_id=<id> window_days=<n> systems_scored=0 index=0 persist=<true|false>`
- Mit Daten:  
  `oami_compute tenant_id=<id> window_days=<n> systems_scored=<n> index=<0-100> persist=<true|false>`

`persist=true` schreibt/aktualisiert den Tenant-Snapshot (Warm-Cache für Reports).

## 4. Synthetische Demo-Daten (idempotent)

**Nur** für Demos/Piloten mit klarem Mandat; nicht für Produktions-Echtdaten.

```bash
# Aus Projektroot, virtuelle Umgebung aktivieren
python scripts/seed_synthetic_ai_runtime_events.py --tenant-id <TENANT_ID> --system-id <AI_SYSTEM_ID>
```

- `--dry-run`: keine DB-Änderung, nur Ausgabe „would insert …“.
- Quelle in der DB: `synthetic_demo_seed`; stabile `source_event_id`-Muster → **erneutes Ausführen überspringt** vorhandene Zeilen.
- Nach Commit: optionaler Aufruf `compute_tenant_operational_monitoring_index` mit `persist_snapshot=True` (siehe Skript-Ende).

Voraussetzung: `ai_systems`-Zeile existiert und gehört zum angegebenen `tenant_id`.

## 5. Schnell-Checkliste bei Incidents

1. Letzte `runtime_events_ingest`-Zeile für betroffenen `tenant_id` / `ai_system_id`: `inserted` vs. `rejected_invalid`.
2. Integrations-Client: `event_type`, `severity`, `source`, `metric_key` / `incident_code` gegen Katalog.
3. OAMI „0 / low“ mit `systems_scored=0`: erwartbar ohne Events im Fenster; Erklärungsobjekt in API prüfen.
4. Demo-Mandant: kein API-Ingest erwarten; Seeding-Pfad nutzen.

## 6. Verwandte Dateien

| Thema | Pfad |
|-------|------|
| Validierung & Enums | `app/runtime_event_catalog.py` |
| Ingest & Incident-Refresh | `app/services/runtime_events_ingest.py` |
| JSON-Minimierung `extra` | `app/services/runtime_event_sanitize.py` |
| Demo-Ingest-Sperre | `app/services/runtime_events_demo_guard.py` |
| OAMI + Snapshots | `app/services/operational_monitoring_index.py` |
| Deutsche Kurzerklärung (ohne LLM) | `app/services/oami_explanation.py` |

---

*Letzte Ausrichtung: OAMI-Pipeline, Governance Maturity, Board/Advisor; bei Abweichungen Code als Quelle der Wahrheit nutzen.*
