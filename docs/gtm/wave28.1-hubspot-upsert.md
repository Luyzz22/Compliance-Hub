# Wave 28.1 – HubSpot Upsert (erster echter CRM-Pfad)

Ziel: End-to-end Sync von Website-Leads nach **HubSpot** über das bestehende `LeadSyncJob`-Framework, ohne generische CRM-Abstraktion. Fokus auf **Korrektheit, Nachvollziehbarkeit und konservative Updates**.

Siehe auch: [Wave 28 – Lead-Sync-Framework](wave28-lead-sync-framework.md).

## Aktivierung

| Variable | Bedeutung |
|----------|-----------|
| `HUBSPOT_ACCESS_TOKEN` | Private-App- oder OAuth-Token (CRM). **Wenn gesetzt**, wird das Sync-Ziel `hubspot` aktiviert (zusätzlich zu optionalen Stubs/n8n). |
| `HUBSPOT_DEFAULT_OWNER_ID` | Optional: numerische HubSpot-Owner-ID; wird nur gesetzt, wenn am Kontakt noch kein Owner gesetzt ist. |
| `HUBSPOT_PIPELINE_HINT` | Optional: freier Text, wird in die **Notiz** geschrieben (kein Deal-Pipeline-Mapping in dieser Welle). |
| `HUBSPOT_ALLOW_COMPANY_CREATE` | Wenn `1`: bei fehlendem exakten Firmen-Treffer wird eine **neue** Company mit dem Formular-Firmennamen angelegt und verknüpft. Standard: **aus** (nur Match, kein Create). |
| `HUBSPOT_PROPERTY_CONTACT_KEY` | Optional: **interner** Name eines benutzerdefinierten Kontakt-Felds für `lead_contact_key` (Portal muss Property kennen). |
| `HUBSPOT_PROPERTY_ACCOUNT_KEY` | Optional: Custom Property für `lead_account_key`. |
| `HUBSPOT_PROPERTY_SEGMENT` | Optional: Custom Property für Segment. |
| `HUBSPOT_PROPERTY_SOURCE_PAGE` | Optional: Custom Property für Quell-URL/Pfad. |
| `HUBSPOT_PROPERTY_LATEST_INQUIRY_AT` | Optional: Custom Property für `contact_latest_seen_at` (ISO-String). |

Ohne gültiges Token gibt es **keinen** `hubspot`-Job. Der Stub `hubspot_stub` bleibt über `LEAD_SYNC_HUBSPOT_STUB=1` unverändert testbar.

## Kontakt-Upsert

- **Match:** Suche per `email` (EQ, normalisiert kleingeschrieben).
- **Neu:** `POST /crm/v3/objects/contacts` mit `email`, `firstname` / `lastname` (Name aus Formular: erster Token = Vorname, Rest = Nachname; leerer Name → Platzhalter-Vorname), optional `company` (Standard-HubSpot-Kontaktfeld), optional `hubspot_owner_id`.
- **Bestehend:** `PATCH` nur mit **konservativen** Ergänzungen: `firstname`, `lastname`, `company`, `hubspot_owner_id` und optionale Custom Properties werden **nur gesetzt, wenn das Feld in HubSpot derzeit leer ist**. Bereits gepflegte CRM-Daten werden nicht überschrieben.

Segment, Quellseite, Keys und Zeitstempel liegen standardmäßig in der **Notiz**; optional zusätzlich in Custom Properties, wenn die Env-Variablen gesetzt sind und die Properties im Portal existieren (sonst 400 → nicht retry-fähig).

## Firma (Company)

- Nur wenn der Firmenname **nicht** als schwach eingestuft wird (sehr kurz oder Platzhalter wie „n/a“, „test“, …).
- **Suche:** exakter `name` EQ auf Companies.
- **Ein Treffer:** Kontakt mit Company verknüpfen (`contact_to_company`).
- **Kein Treffer:** Standardmäßig **kein** Anlegen; Ergebnis `company_association: skipped_no_match`. Mit `HUBSPOT_ALLOW_COMPANY_CREATE=1`: Company anlegen und verknüpfen.
- **Mehrere Treffer / unsicher:** keine Zuordnung; `skipped_ambiguous`.

## Notiz pro Inquiry (Idempotenz)

- Jede Website-Inquiry (`lead_id`) erzeugt höchstens **eine** HubSpot-Notiz pro erfolgreichem Sync-Lauf.
- Inhalt: Nachricht, `source_page`, `segment`, Route/SLA, Triage, `trace_id`, `lead_id`, Kontakt-Sequenz/Rollup, `duplicate_hint`, optional Pipeline-Hinweis.
- **Marker:** `COMPLIANCEHUB_LEAD_INQUIRY_ID:{lead_id}` steht im HTML-Body der Notiz.
- **Retry:** Vor dem Anlegen werden bis zu **40** mit dem Kontakt assoziierte Notizen per Batch-Read geprüft. Enthält eine Notiz den Marker, wird **keine** zweite Notiz erstellt (`note_action: skipped_existing`).

**Grenze:** Kontakte mit sehr vielen Notizen und weniger als 40 zugeordneten (oder Marker außerhalb der zuletzt geladenen Assoziationen) sind theoretisch fehleranfällig; für typische Inbound-Leads ist das akzeptabel.

## Lokales Sync-Ergebnis (`mock_result`)

Nach Erfolg speichert der Job u. a.:

- `system: "hubspot"`
- `contact_id`, optional `company_id`
- `note_id`, `note_action` (`created` | `skipped_existing`)
- `company_association` (siehe oben)
- `synced_at`, optional `pipeline_hint`

Die interne Lead-Inbox zeigt diese Werte in der Spalte **HubSpot-Referenz**.

## Retry / Dead Letter

- Der Connector setzt `retryable` auf **false** u. a. bei: 401/403, typischen 400-Validierungsfehlern, fehlenden Properties, 404.
- **429** und **5xx** sowie Netzwerk/Timeout: **retry-fähig** (Backoff im Dispatcher).
- Bei `retryable === false` landet der Job **sofort** im Dead Letter (ohne alle Versuche zu verbrauchen).

## Bewusste Einschränkungen

- Kein generisches CRM-Interface; nur HubSpot-API-Aufrufe in `hubspotLeadSyncConnector.ts`.
- Kein Deal-Stage-Mapping; `HUBSPOT_PIPELINE_HINT` ist nur Dokumentation in der Notiz.
- Keine Domänen-basierte Company-Suche (nur exakter Name, optional Create).
- Zwei parallele Ziele `hubspot` und `hubspot_stub` erzeugen **zwei** Jobs pro Lead (unterschiedliche `idempotency_key`); in Produktion in der Regel nur eines aktivieren.
