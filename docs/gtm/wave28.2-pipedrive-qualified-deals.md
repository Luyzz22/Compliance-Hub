# Wave 28.2 – Pipedrive: qualifizierte Deals (schmaler Vertriebspfad)

## Rolle im Stack

- **HubSpot** bleibt das **breitere** System für Kontakt, Historie und Website-Inquiries (Wave 28.1).
- **Pipedrive** ist ein **optionaler Ausführungs-Layer** für **qualifizierte Verkaufschancen** (Pipeline/Deal), kein zweites „System of Truth“ für jeden Lead.

Wenn beide Ziele aktiv sind, laufen **HubSpot-Jobs für alle** eingehenden Leads (so konfiguriert), **Pipedrive-Jobs nur**, wenn die untenstehenden **Qualifikationsregeln** erfüllt sind.

## Aktivierung

| Variable | Bedeutung |
|----------|-----------|
| `PIPEDRIVE_API_TOKEN` | API-Token; wenn gesetzt, Ziel `pipedrive` in `getEnabledLeadSyncTargets()`. |
| `PIPEDRIVE_DEFAULT_PIPELINE_ID` | **Pflicht** (numerisch): Pipeline für neue Deals. |
| `PIPEDRIVE_DEFAULT_STAGE_ID` | **Pflicht** (numerisch): Start-Stage in dieser Pipeline. |
| `PIPEDRIVE_DEFAULT_OWNER_ID` | Optional: numerischer User/Owner für Person (Create) und Deal. |
| `PIPEDRIVE_ALLOW_ORG_CREATE` | `1`: bei fehlendem exakten Organisations-Treffer Organisation anlegen; sonst nur Match. |

Der **Stub** `pipedrive_stub` bleibt über `LEAD_SYNC_PIPEDRIVE_STUB=1` für Tests; echtes Pipedrive nutzt Ziel `pipedrive`.

## Qualifikations-Gate (explizit)

Ein Lead ist **nur dann** für einen Pipedrive-Deal-Sync vorgesehen, wenn **alle** zutreffen:

1. **Geschäfts-E-Mail** vorhanden und plausibel (enthält `@`).
2. **Kein Spam:** `triage_status !== "spam"`.
3. **Qualifiziert:** `triage_status === "qualified"`.
4. **Zusätzlich mindestens eines:**
   - **Firma** mit ausreichend belastbarem Namen (nicht leer/Platzhalter wie „n/a“, „test“, …), oder
   - **Segment** `enterprise_sap` oder `kanzlei_wp`, oder
   - **Owner** in der Inbox gesetzt (nicht leer).

Implementierung: `frontend/src/lib/pipedriveDealEligibility.ts` (`isLeadPipedriveDealEligible`).

**Warum nicht jeder Lead ein Deal wird:** Pipedrive soll **Pipeline-Rauschen** vermeiden; Roh-Anfragen und frühe Triage-Stufen bleiben bei HubSpot/Inbox.

## Wann wird ein Job erzeugt?

- Beim **öffentlichen Ingest** (`POST /api/lead-inquiry`): Pipedrive wird in der Sync-Schleife **übersprungen**, solange das Gate nicht erfüllt (typisch: Triage noch `received`).
- Nach **Admin-PATCH** (Triage, Owner, …): `enqueuePipedriveDealSyncIfEligible` legt bei erfülltem Gate einen Job an und verarbeitet ihn direkt danach (best effort).

## Idempotency & Deal-Dedup

- **Job-Idempotency:** `computeLeadSyncIdempotencyKey("pipedrive", lead_id, …, pipedrive_deal:{lead_id})` — **ein Job pro Lead-Inquiry** (`lead_id`).
- **Fresh Payload:** Der Connector lädt vor der Ausführung **aktuelle** Triage/Owner/Segment aus der Inbox (wie bei Bedarf auch HubSpot später denkbar); das verhindert veraltete Deal-Daten nach Ops-Änderungen.
- **Deal-Dedup:** Deal-Titel enthält den Marker `CH-LID:{lead_id}`. Gesucht wird unter `GET /deals?person_id=…` nach einem Deal, dessen Titel den Marker enthält; **Update** statt zweitem Deal.

**Grenze:** Wenn der Marker im Titel in Pipedrive manuell entfernt wird, kann ein zweiter Deal entstehen.

## Person & Organisation

- **Person:** Suche per `itemSearch` (Person), dann exakter Abgleich der E-Mail; sonst **Create** mit Name, E-Mail, optional `org_id` und `owner_id` (nur beim Anlegen).
- **Update bestehender Person:** nur **leeren Namen** füllen — keine Organisation/Owner überschreiben.
- **Organisation:** Suche per `itemSearch` (Organization), **exakter** Name-Match nach Nachladen des Datensatzes; bei Mehrdeutigkeit **keine** Verknüpfung; optional **Create** mit `PIPEDRIVE_ALLOW_ORG_CREATE=1`.
- **Schwache Firmennamen:** wie bei HubSpot konservativ — kein Org-Match/Create für Platzhalter.

## Deal-Inhalt

- Titel: `CH-LID:{lead_id} | {Firma oder Name oder E-Mail} · {segment}` (gekürzt).
- Deal verknüpft mit Person und optional Org; Pipeline/Stage aus Env.
- **Notiz** am Deal mit Nachricht-Auszug, Quelle, Route, Owner (Inbox), Triage, `trace_id`, `lead_id`, Kontakt-Sequenz / `duplicate_hint`.

## Retries & Dead Letter

- Gleiches Muster wie HubSpot: `retryable` im Connector-Ergebnis; **nicht retry-fähig** (z. B. fehlende Pipeline/Stage, Token, harte 400er) → **schneller Dead Letter** über den Dispatcher.

## Admin-UI

- Hinweiszeile **„Pipedrive-Deal möglich“** mit deutscher Begründung.
- Tabelle **CRM / Deal-Referenz** mit Pipedrive **Person / Org / Deal**-IDs bei erfolgreichem Sync.
- Schnellaktion **„Qualifiziert (Pipedrive)“** setzt Triage auf `qualified` (weitere Bedingungen des Gates ggf. über Firma/Segment/Owner).

Siehe auch: [Wave 28 – Lead-Sync-Framework](wave28-lead-sync-framework.md), [Wave 28.1 – HubSpot](wave28.1-hubspot-upsert.md).
