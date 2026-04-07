# Wave 58 – Connector Sync Jobs & Failure Handling

Enterprise-grade operational layer on top of the Wave 57 generic API connector skeleton: explicit sync lifecycle, retries, failure categories, and operator-facing APIs/UI.

## Sync lifecycle (sync run)

Each execution is a row in `enterprise_connector_sync_runs` with `sync_status` (API field `sync_status` on `ConnectorSyncResult`, values = lifecycle):

| State | Meaning |
| --- | --- |
| `queued` | Run angelegt, Verarbeitung noch nicht gestartet (aktuell im HTTP-Flow unmittelbar in `running`). |
| `running` | Aktive Synchronisation. |
| `succeeded` | Alle empfangenen fachlichen Datensätze wurden normalisiert und idempotent gespeichert. |
| `partial_success` | Mindestens ein Datensatz normalisiert, aber es gab Verwerfungen (z. B. Mapping/Domäne). |
| `failed` | Lauf abgeschlossen ohne belastbaren Erfolg oder abgebrochen wegen Blocker (z. B. Quelle nicht erreichbar). |
| `cancelled` | Reserviert für künftige Abbruchpfade. |

Zusätzlich persistiert (tenant-isoliert):

- `started_at_utc`, `finished_at_utc`, `duration_ms`
- `records_received`, `records_normalized`, `records_rejected` (Kompatibilität: `records_ingested` = normalisierte, gespeicherte Datensätze)
- `failure_category`, `last_error`, deutschsprachige `summary_de`, strukturierte `details_json`
- `retry_of_sync_run_id` für Retry-Linie

## Retry-Semantik

- **Retry-Endpoint:** `POST /api/internal/enterprise/connector-runtime/retry-sync` mit optionalem Body `{ "sync_run_id": "<id>" }`. Ohne ID wird der letzte abgeschlossene Lauf mit `failed` oder `partial_success` gewählt.
- **RBAC:** wie manueller Sync — `MANAGE_ONBOARDING_READINESS`.
- **Audit:** `enterprise_connector.sync.retry_triggered` plus bestehendes `sync.completed` mit Outcome und Metadaten.
- **Sicheres Retry:** Nach transienten Fehlern (z. B. Quelle degradiert) Retry nach Behebung der Ursache. Bei `payload_validation` mit `details_json.safe_retry: false` ist in erster Linie Datenkorrektur nötig, bevor ein erneuter Lauf Sinn ergibt.

## Idempotenz

Evidence-Zeilen sind über `(tenant_id, connector_instance_id, evidence_domain, external_record_id)` eindeutig. Wiederholtes Verarbeiten derselben externen ID **aktualisiert** die bestehende Zeile (gleicher Mandant), erzeugt **keine** zweite Evidence-Row.

## Fehlerkategorien (`failure_category`)

| Kategorie | Typische Ursache | Operator-Fokus |
| --- | --- | --- |
| `auth_config` | Zugangsdaten, Endpoint, Secret/Rotation | Integration/Security |
| `source_unavailable` | Wartung, Netz, Degradierung | Infrastruktur, Zeitfenster |
| `payload_validation` | Schema, Pflichtfelder, ungültige Domäne | Datenlieferant, Mapping |
| `normalization_mapping` | Feld-Mapping, Regeln | Integration + Fach |
| `internal_processing` | Unerwarteter interner Fehler | Plattform/Support |

Deutschsprachige Kurztexte und **nächster Schritt** werden pro Lauf in `operator_next_step_de` ausgeliefert.

## APIs (internal, Tenant-Header)

| Methode | Pfad | Zweck |
| --- | --- | --- |
| GET | `/connector-runtime` | Status inkl. `health` und letztem Lauf |
| GET | `/connector-runtime/health` | Kompakter Health-Snapshot |
| GET | `/connector-runtime/last-sync` | Letzter Lauf (wie bisher, erweitertes Schema) |
| GET | `/connector-runtime/sync-runs?limit=` | Historie |
| GET | `/connector-runtime/latest-failure` | Neuester **failed**-Lauf oder `null` |
| POST | `/connector-runtime/manual-sync` | Manueller Lauf |
| POST | `/connector-runtime/retry-sync` | Retry failed/partial |

## Control Center

Neuer Abschnitt **Integrationen & Connectoren** erscheint nur bei **materialen** Signalen (z. B. letzter Lauf fehlgeschlagen/teilweise, Verbindung nicht produktiv, hängender `running`-Lauf > 15 Minuten). Kein Dauer-Alarm bei sauberem Betrieb.

## Operator-Leitlinie

1. Sync-Verlauf und letzte **Fehlerkategorie** in Onboarding Readiness prüfen.  
2. **Nächster Schritt** aus `operator_next_step_de` befolgen.  
3. Bei transienten Quellenfehlern nach Stabilisierung **Retry** nutzen.  
4. Evidence-Anzahl im Health-Snapshot als grobe **Ingestions-Lage** nutzen (kein Ersatz für Quellen-Audit).

## Migration

Additive Spalten auf `enterprise_connector_sync_runs`: siehe `m20260410_enterprise_connector_sync_run_wave58`.

Legacy `sync_status`/`success` in älteren Zeilen wird beim Lesen als `succeeded` normalisiert.
