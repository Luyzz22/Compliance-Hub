# Wave 28 – Lead-Sync-Framework (GTM Downstream)

Ziel: Zuverlässiger, nachvollziehbarer Push von Lead-/Inquiry-Daten zu **n8n** und vorbereiteten **CRM-Abstraktionen** (HubSpot / Pipedrive als Stubs), getrennt vom Rohdatensatz `lead_inquiry` und vom Legacy-Inbound-Webhook (Wave 25).

## Überblick

- **Persistierte Sync-Jobs** pro Ziel (`LeadSyncJob`) mit Status, Versuchen, Idempotency-Key und optionalem Payload-Snapshot für stabile Retries.
- **Dispatcher** erzeugt Jobs bei Ingest (`POST /api/lead-inquiry`), verarbeitet Pending-Jobs mit Backoff und Dead-Letter nach N Versuchen.
- **Ops-Sicht** in der internen Lead-Inbox: Status pro Ziel, Fehler, manueller Retry.
- **Aktivitäts-Log** (`lead_ops`): `lead_sync_job_created`, `lead_sync_sent`, `lead_sync_failed`, `lead_sync_retried`, `lead_sync_dead_letter`.

Siehe auch: [Wave 25 – Lead-Routing](wave25-lead-routing-and-intake-governance.md), [Wave 27 – Dedup & Historie](wave27-lead-dedup-and-history.md), [Wave 26 – Lead-Inbox](wave26-internal-lead-inbox.md), [Wave 28.1 – HubSpot Upsert](wave28.1-hubspot-upsert.md).

## Job-Modell (`LeadSyncJob`)

| Feld | Bedeutung |
|------|-----------|
| `job_id` | UUID |
| `lead_id` | Verknüpfung zur Inquiry |
| `lead_contact_key` | Kontext für CRM-Upsert (E-Mail-Schlüssel) |
| `target` | `n8n_webhook` \| `hubspot` \| `hubspot_stub` \| `pipedrive_stub` |
| `payload_version` | z. B. `1.0` (Sync-Payload-Schema) |
| `status` | `pending` → `retrying` / `sent` / `failed` → ggf. `dead_letter` |
| `attempt_count` | Anzahl Versuche |
| `idempotency_key` | deterministisch (siehe unten) |
| `created_at` / `updated_at` | ISO |
| `last_attempt_at`, `last_error`, `last_http_status` | Observability |
| `next_retry_at` | Backoff |
| `mock_result` | strukturiertes Stub-Ergebnis (keine Secrets) |
| `payload_snapshot` | fixierter JSON-Payload pro Job (nur Server-Store, API redacted) |

Speicher: JSON-Datei (Standard `data/lead-inquiries/sync-jobs.json`), überschreibbar mit `LEAD_SYNC_JOBS_STORE_PATH` (z. B. für Vercel `/tmp/...`).

## Payload-Vertrag (`LeadSyncPayloadV1`, Schema `1.0`)

Snake_case, stabil für n8n/CRM:

- **Inquiry:** `lead_id`, `trace_id`, `created_at`, `source_page`, `segment`, `name`, `business_email`, `company`, `message`, `route` (Key, Queue, Priorität, SLA).
- **Kontakt-Rollup:** `lead_contact_key`, `lead_account_key`, `contact_inquiry_sequence`, `contact_first_seen_at`, `contact_latest_seen_at`, `contact_submission_count`, `duplicate_hint`.
- **Ops:** `triage_status`, `owner`, `pipeline_status`, `forwarding_status`.
- **Legacy-Hinweis:** `legacy_inbound_webhook_delivery` (`forwarded` \| `stored` \| `stored_forward_failed` \| `not_configured`).

Implementierung: `frontend/src/lib/leadSyncPayload.ts`, Typen: `frontend/src/lib/leadSyncTypes.ts`.

## Idempotency

```
computeLeadSyncIdempotencyKey(target, lead_id, payload_version, material_revision)
→ SHA-256-Prefix, Präfix `idem_`
```

Bei Ingest ist `material_revision` aktuell `ingest:<created_at_iso>` der Inquiry (immutable). **Gleicher Lead + gleiche Revision + gleicher Target** → gleicher Key → ein logischer Job pro Ziel (Dedup im Store über `idempotency_index`).

**Re-Sync bei inhaltlicher Änderung** (später): neue `material_revision` (z. B. `triage:<updated_at>`) erzeugt neuen Key und einen neuen Job – explizit, nicht „magisch“.

## Upsert-Semantik (konzeptionell)

Downstream wird modelliert als:

1. **Kontakt upserten** anhand Geschäfts-E-Mail / `lead_contact_key`.
2. **Inquiry / Notiz / Aktivität** anlegen oder anhängen.
3. **Letzte Sichtung / Sequenz** aktualisieren (`contact_latest_seen_at`, `contact_submission_count`, … im Payload).

Stubs (`hubspot_stub`, `pipedrive_stub`) mappen den Payload in ein lokales, strukturiertes `mock_result` (kein echter API-Call).

## Retry & Dead Letter

- Konstante `LEAD_SYNC_MAX_ATTEMPTS` (6): nach Überschreiten → `dead_letter`.
- Backoff zwischen Versuchen (Dispatcher).
- **Manueller Retry** (Admin): setzt Job auf `pending`, setzt Zähler zurück, verarbeitet sofort; Ops-Eintrag `lead_sync_retried`.

## Ziele (Connectors)

| Target | Aktivierung | Verhalten |
|--------|-------------|-----------|
| `n8n_webhook` | `LEAD_SYNC_N8N_URL` gesetzt; optional `LEAD_SYNC_N8N_SECRET` (Bearer) | HTTP POST mit JSON-Payload, Status/Errors am Job |
| `hubspot` | `HUBSPOT_ACCESS_TOKEN` | Echter HubSpot CRM-Sync (siehe [Wave 28.1](wave28.1-hubspot-upsert.md)) |
| `hubspot_stub` | `LEAD_SYNC_HUBSPOT_STUB=1` | Lokales Mock-Upsert + Notiz |
| `pipedrive_stub` | `LEAD_SYNC_PIPEDRIVE_STUB=1` | Lokales Mock-Upsert + Aktivität |

## APIs (intern)

- `GET /api/admin/lead-inquiries/[leadId]` – enthält `sync_jobs` (ohne `payload_snapshot`).
- `POST /api/admin/lead-inquiries/[leadId]/sync-retry` – Body `{ "job_id": "<uuid>" }`.
- `POST /api/admin/lead-sync/process` – Body optional `{ "limit": 25 }` – Worker/Cron zum Abarbeiten der Warteschlange (gleiche Auth wie Lead-Admin).

## Migration: Webhook-only → CRM-Sync

1. **Weiter** `LEAD_INBOUND_WEBHOOK_URL` für bestehende Automationen; das Sync-Payload-Feld `legacy_inbound_webhook_delivery` dokumentiert den Zustand.
2. **Parallel** `LEAD_SYNC_N8N_URL` setzen: n8n empfängt den strukturierten **Wave-28-Payload** und kann in CRMs schreiben (oder nur enrich/loggen).
3. Stubs aktivieren zum Testen der Pipeline ohne API-Keys.
4. Später: `hubspot_stub` / `pipedrive_stub` durch echte Connectors ersetzen (gleiche Job-/Payload-Schicht, andere `runLeadSyncConnector`-Zweige).

## Nicht-Ziele

- Keine vollständige CRM-Integrationsplattform.
- Keine Änderung des öffentlichen Kontaktformulars außerhalb der bestehenden Ingest-Pipeline.
