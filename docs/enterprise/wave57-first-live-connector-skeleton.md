# Wave 57 - First Live Connector Skeleton

## Chosen First Connector Archetype

Für Wave 57 wird bewusst **`generic_api`** als erster Live-Connector-Skeleton gewählt.

Begründung:

- schnellster, sicherer Start für produktionsnahe Ingestion-Pfade
- tenant-sicher und ohne Secrets testbar
- wiederverwendbare Architektur für spätere `sap_btp`, `sap_s4hana`, `datev`, `ms_dynamics`-Connectoren

## Architektur (minimal, produktionsorientiert)

Neue Runtime-Bausteine:

- `enterprise_connector_instances`
  - `connector_instance_id`, `tenant_id`, `source_system_type`
  - `connection_status`, `sync_status`
  - `last_sync_at`, `last_error`
  - `enabled_evidence_domains`
- `enterprise_connector_sync_runs`
  - Laufhistorie je manueller Sync
  - Ergebnisstatus, ingestete Records, Summary, Fehler
- `enterprise_connector_evidence_records`
  - normalisierte externe Evidenz-Datensätze
  - Domain + external record id + source/normalized payload

## Erster Ingestion-Flow (Narrow Scope)

Wave 57 ingestiert bewusst nur zwei Domains:

- `invoice`
- `approval`

Flow:

1. manueller Sync triggern
2. Input payload validieren (strukturierte Records)
3. in normierte Evidence-Records mappen
4. idempotent speichern (tenant + connector + domain + external id)
5. Sync-Run finalisieren
6. GoBD-Audit-Event für Trigger + Completion schreiben

## Interne APIs

- `GET /api/internal/enterprise/connector-runtime`
  - Instanzstatus + letztes Ergebnis
- `GET /api/internal/enterprise/connector-runtime/last-sync`
  - letzter Sync-Run
- `POST /api/internal/enterprise/connector-runtime/manual-sync`
  - manueller Trigger für den Skeleton-Sync

Alle Endpunkte sind tenant-scharf, RBAC-geschützt und auditierbar.

## UI / Admin View

Im Enterprise-Control-Center wird eine kompakte Runtime-Karte angezeigt:

- Connector-Typ
- Connection-/Sync-Status
- aktivierte Domains
- letzter Sync + letzter Fehler
- Link/Aktion zum manuellen Sync

## Security & Compliance

- keine Speicherung von Live-Secrets oder Credentials
- klare tenant boundaries
- nachvollziehbare Fehlermeldungen im Runtime-Status
- Audit-Trail für Sync-Aktionen

## Limitationen in Wave 57

- kein echter SAP-BTP-Transport/Token-Flow
- nur enger Domain-Scope (`invoice`, `approval`)
- initial manuell getriggerte Sync-Läufe (kein Scheduler)

## Path to SAP / DATEV / Dynamics

1. `generic_api`-skeleton auf echte connector adapter abstrahieren
2. pro Source-Type Auth-/Transport-Layer ergänzen (BTP/OAuth/SAP APIs)
3. weitere Evidence-Domains schrittweise aktivieren
4. scheduling + retry + dead-letter handling ergänzen
5. Monitoring/SLA in Control Center erweitern
