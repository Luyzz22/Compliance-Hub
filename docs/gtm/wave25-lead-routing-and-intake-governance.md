# Wave 25 – Lead-Routing, Webhook-Vertrag & Intake-Governance

**Vorgänger:** [Wave 24 – Kontakt & Lead-Capture](./wave24-contact-and-lead-capture.md)  
**Kanonische Website:** [complywithai.de](https://complywithai.de/)

---

## 1. End-to-End-Flow

1. Nutzer öffnet `/kontakt?quelle=…` → Client setzt `form_opened_at` (Anti-Bot-Timing).
2. `POST /api/lead-inquiry` (Runtime **nodejs**):
   - IP-Rate-Limit (Sliding Window, pro Prozess)
   - Honeypot `company_website`
   - Zeitfenster `form_opened_at` (min. ca. 2,5 s, max. 3 h)
   - Validierung inkl. optional **nur geschäftliche Domains** (`LEAD_REQUIRE_BUSINESS_EMAIL=1`)
   - **Duplikat-Cooldown** pro E-Mail (5 Min., pro Prozess)
   - Routing: `determineLeadRoute(segment, company, message, source_page)`
   - Outbound-Payload `schema_version: "1.0"`
   - **Persistenz zuerst:** eine JSONL-Zeile `_kind: "lead_inquiry"`, Status `received`
   - **Webhook danach** (falls `LEAD_INBOUND_WEBHOOK_URL`): bis zu 3 Versuche, optional Bearer `LEAD_INBOUND_WEBHOOK_SECRET`
   - Ergebniszeile `_kind: "webhook_result"` (ok / Fehler)
3. Antwort an Client: `delivery` ∈ `forwarded` | `stored` | `stored_forward_failed` + ggf. `delivery_note_de`.

---

## 2. Routing-Logik (`determineLeadRoute`)

| Segment (Formular) | `route_key` (stabil) | Queue-Label (DE) | Priorität | SLA-Bucket |
| ------------------ | --------------------- | ---------------- | --------- | ---------- |
| `enterprise_sap` | `queue_enterprise_sap` | Enterprise / SAP – Solution & Integration | high | enterprise |
| `kanzlei_wp` | `queue_kanzlei_wp` | Kanzlei / WP – Beratung & Mandanten | normal | priority |
| `industrie_mittelstand` | `queue_industrie_mittelstand` | Industrie / Mittelstand – AI Act & NIS2 | normal | standard |
| `sonstiges` | Kontext-Keywords in Nachricht/Unternehmen/Quelle → ggf. SAP oder Kanzlei, sonst `queue_other` | Sonstiges / Qualifikation | low/normal/high | standard/priority/enterprise |

**Hinweis:** `sla_bucket` ist eine **interne Einordnung**, kein vertraglicher SLA.

---

## 3. Webhook-Payload (Contract v1.0 / v1.1)

Feldname im JSON (snake_case, stabil):

| Feld | Typ | Beschreibung |
| ---- | --- | ------------ |
| `schema_version` | `"1.0"` oder `"1.1"` | Version des Vertrags (neue Anfragen: **1.1**) |
| `lead_id` | UUID | Primärschlüssel der Anfrage |
| `trace_id` | UUID | Korrelation Logs / Webhook / Support |
| `timestamp` | ISO-8601 | Erzeugung des Payloads |
| `source_page` | string | Wert `quelle` |
| `segment` | enum | Formular-Segment |
| `name` | string | Ansprechpartner |
| `business_email` | string | geschäftliche E-Mail |
| `company` | string | Unternehmen / Kanzlei |
| `message` | string | Freitext (kann leer sein) |
| `route` | object | `route_key`, `queue_label`, `priority`, `sla_bucket` |

**Zusatz ab v1.1** (CRM-/Dedup-Vorbereitung, siehe [Wave 27](./wave27-lead-dedup-and-history.md)):

| Feld | Typ | Beschreibung |
| ---- | --- | ------------ |
| `lead_contact_key` | string | Stabiler Kontakt-Schlüssel (Hash der normalisierten E-Mail) |
| `lead_account_key` | string \| null | Optionale Firmen-/Domain-Gruppe |
| `contact_inquiry_sequence` | number | n-te Anfrage dieses Kontakts |
| `contact_first_seen_at` | ISO-8601 | Erste bekannte Anfrage |
| `contact_latest_seen_at` | ISO-8601 | Diese Anfrage |
| `duplicate_hint` | `none` \| `same_email_repeat` | Nur Hinweis, kein Merge |

Implementierung: `buildLeadOutboundPayload` in `frontend/src/lib/leadOutbound.ts`.

---

## 4. Persistenz

- **Standardpfad:** `frontend/data/lead-inquiries/store.jsonl` (lokal, nicht committed).
- **Vercel:** `/tmp/compliancehub-lead-inquiries.jsonl` (ephemeral – Webhook/CRM als Quelle der Wahrheit nutzen).
- **Override:** `LEAD_INQUIRY_STORE_PATH` (absoluter Pfad zu einer `.jsonl`-Datei).

Format: Append-only JSON Lines; Admin-API führt `lead_inquiry` + nachfolgende `webhook_result` pro `lead_id` grob zusammen.

---

## 5. Admin-Zugriff

- `GET /api/admin/lead-inquiries?limit=40`  
- Header: `Authorization: Bearer <LEAD_ADMIN_SECRET>`  
- Ohne gesetztes `LEAD_ADMIN_SECRET`: **404** (kein Leak der Existenz).

Antwort enthält gekürzte `message_preview` und volle Kontaktdaten – **nur intern**, nicht öffentlich verlinken.

**Weiterführung:** [Wave 26 – Internes Lead-Inbox](./wave26-internal-lead-inbox.md) (`/admin/leads`, Triage-Status, Session-Cookie, `ops-state.json`).

---

## 6. Spam / Missbrauch

| Maßnahme | Beschreibung |
| -------- | ------------ |
| Honeypot | Feld `company_website` (versteckt) |
| Zeit-Check | `form_opened_at` Server-seitig |
| IP-Limit | 12 Anfragen / 15 Min. / IP (pro Instanz) |
| E-Mail-Cooldown | Gleiche E-Mail: 5 Min. zwischen erfolgreichen Versuchen |
| Freemail optional | `LEAD_REQUIRE_BUSINESS_EMAIL=1` blockt gängige Consumer-Domains |

Verteilte Deployments: IP-Limit und E-Mail-Map sind **pro Node** – für harte Grenzen Redis / Edge Rate Limit ergänzen.

---

## 7. Telemetrie (stabil)

| Event (Client → `/api/marketing-event`) | Bedeutung |
| --------------------------------------- | --------- |
| `cta_click` | CTA mit `cta_id`, `quelle` |
| `lead_form_started` | Erste Formularinteraktion |
| `lead_form_submit_attempt` | Absenden |
| `lead_form_submitted` | Erfolg; optional `delivery` |
| `lead_form_submit_error` | Client-seitiger Fehler |
| `lead_form_rate_limited` | 429 / Duplikat |

Server-Logs: `[lead-inquiry]`, `[lead-webhook]`, `[marketing-event]` (strukturiertes JSON).

---

## 8. DSGVO / Aufbewahrung (Produkt-/Systemhinweise, keine Rechtsberatung)

- **Zweck:** Bearbeitung der Kontaktanfrage (Art. 6 Abs. 1 lit. b DSGVO).
- **Empfänger:** Betriebsteam Compliance Hub; Webhook-Empfänger laut Konfiguration (z. B. n8n, CRM).
- **Speicherung:** JSONL und/oder CRM; Dauer **betrieblich** zu definieren (Orientierung: Anfragen nach Abschluss der Bearbeitung **24–36 Monate** archivieren oder löschen, sofern keine gesonderten Aufbewahrungsgründe; final mit DSB abstimmen).
- **Betroffenenrechte:** Auskunft/Löschung über datenschutz@…-Prozess (Platzhalter – mit echter Adresse belegen).
- **Export:** Admin-API oder direkter Zugriff auf JSONL / CRM-Export.

Vollständige **Datenschutzerklärung** gehört auf die öffentliche Website; dieser Abschnitt dient der **internen** Abstimmung.

---

## 9. Umgebungsvariablen

| Variable | Zweck |
| -------- | ----- |
| `LEAD_INBOUND_WEBHOOK_URL` | Ziel-URL für Outbound-Payload |
| `LEAD_INBOUND_WEBHOOK_SECRET` | Optional: `Authorization: Bearer …` |
| `LEAD_INQUIRY_STORE_PATH` | Optional: Pfad zur JSONL-Datei |
| `LEAD_ADMIN_SECRET` | Bearer / Session-Login für Admin-API und `/admin/leads` |
| `LEAD_INQUIRY_OPS_PATH` | Optional: Pfad zu `ops-state.json` (Triage, Wave 26) |
| `LEAD_REQUIRE_BUSINESS_EMAIL` | `1` = Freemail-Domains ablehnen |

---

## 10. Erweiterungen

- HubSpot / Pipedrive: Webhook → n8n → CRM statt nur Log.
- **Supabase / Postgres** als zentraler Lead-Store statt JSONL.
- Zentrales Rate-Limiting (Upstash Redis).
- Signatur `X-Lead-Signature` (HMAC über Body) für Webhook-Verifier.

---

*Wave 25 – sales-operatives Intake mit Governance-Hygiene.*
