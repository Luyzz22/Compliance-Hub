# Wave 26 – Internes Lead-Inbox (Triage ohne CRM)

**Vorgänger:** [Wave 25 – Lead-Routing & Intake-Governance](./wave25-lead-routing-and-intake-governance.md)

---

## 1. Warum diese Inbox existiert

- **Zielgruppe:** Gründer, frühe Sales, Advisor-/Partner-Team.
- **Problem:** JSONL und Logs sind für tägliche Triage unpraktisch.
- **Lösung:** Eine **schlanke interne Oberfläche** unter `/admin/leads` mit Liste, Filtern, Detail und einfachen Status-/Notiz-Aktionen.
- **Kein CRM:** Keine Pipelines, Deals oder Marketing-Automation – nur **Sichtbarkeit und operative Einordnung**, bis ggf. HubSpot/Pipedrive/Salesforce angebunden wird.

---

## 2. Was sich vom CRM unterscheidet

| Aspekt | Lead-Inbox (Wave 26) | Typisches CRM |
| ------ | -------------------- | ------------- |
| Zweck | Triage, Owner, kurze Notizen, Webhook-Retry | Pipeline, Forecast, Kampagnen |
| Daten | Lokal `ops-state.json` + bestehende JSONL | Zentrale CRM-Datenbank |
| Skalierung | Wenige bis einige Dutzend Leads pro Woche | Großvolumen, Teams |
| Rechtliches | Interne Verarbeitungshinweise (Wave 25) | Zusätzliche CRM-Verträge/AVV |

---

## 3. Oberfläche und Endpunkte

| Pfad / Methode | Beschreibung |
| -------------- | ------------ |
| `GET /admin/leads` | Inbox-UI (Server: `LEAD_ADMIN_SECRET` muss gesetzt sein, sonst Hinweis) |
| `POST /api/admin/session` | Body `{ "secret": "<LEAD_ADMIN_SECRET>" }` → httpOnly Session-Cookie |
| `DELETE /api/admin/session` | Cookie löschen (nur mit gültiger Session) |
| `GET /api/admin/lead-inquiries` | Liste inkl. Triage-Felder; Query-Filter: `triage_status`, `segment`, `source_page`, `forwarding_status`, `limit` |
| `GET /api/admin/lead-inquiries/[leadId]` | Einzelansicht (volle Nachricht, Aktivität) |
| `PATCH /api/admin/lead-inquiries/[leadId]` | `triage_status`, `owner`, `internal_note` |
| `POST /api/admin/lead-inquiries/[leadId]/retry-webhook` | Erneuter Webhook-Versuch (wenn `LEAD_INBOUND_WEBHOOK_URL` gesetzt) |

**Auth (einheitlich mit Wave 25):** Bearer `Authorization: Bearer <LEAD_ADMIN_SECRET>`, optional `?secret=` (nur falls nötig), oder **Session-Cookie** nach `POST /api/admin/session`.

---

## 4. Statusmodell

### 4.1 Pipeline / Speicher (JSONL, unverändert Wave 25)

- `received` → nach Webhook ggf. `forwarded` oder `failed` (Zusammenführung aus `lead_inquiry` + `webhook_result`).

### 4.2 Triage (intern, `ops-state.json`)

| Status | Bedeutung (intern) |
| ------ | ------------------ |
| `received` | Neu, noch nicht eingeordnet (Default) |
| `triaged` | Erste Sichtung erledigt |
| `contacted` | Kontaktaufnahme erfolgt |
| `qualified` | Passt strategisch / nächste Schritte klar |
| `closed_won_interest` | Abschluss- oder Pilot-Interesse |
| `closed_not_now` | Aktuell kein Bedarf |
| `spam` | Spam oder ungültig |

Keine CRM-„Stages“ – bei Bedarf später CRM-Sync statt weitere Status in der Hub-App.

---

## 5. Persistenz

- **Leads (Inbound):** weiterhin JSONL (`store.jsonl`), siehe Wave 25.
- **Ops / Triage:** `frontend/data/lead-inquiries/ops-state.json` (lokal), auf Vercel standardmäßig unter `/tmp/...` (ephemeral).
- **Override:** `LEAD_INQUIRY_OPS_PATH` für absoluten Pfad zu `ops-state.json`.
- **Aktivität:** Array pro Lead in `ops-state.json` (Kürzung bei sehr langen Historien technisch begrenzt, z. B. 120 Einträge).

---

## 6. Audit / Aktivität

Append-only Logik auf Dateiebene: bei Änderungen werden Einträge wie `triage_status_changed`, `owner_set`, `internal_note_updated`, `forward_retried` mit Zeitstempel gespeichert. Kein Event-Sourcing, aber **nachvollziehbare Spur** für interne Reviews.

---

## 7. Sortierung und Filter

- **Standard-Sortierung:** Zuerst „Aufmerksamkeit“ (`forwarding_status === failed` **oder** `triage_status === received`), danach **`created_at` absteigend**.
- **Filter:** Triage-Status, Segment, Quelle (Substring), Weiterleitung (`ok` / `failed` / `not_sent`).

---

## 8. Sicherheit und Roadmap

**Heute (Wave 26):**

- Shared Secret + httpOnly Session; keine öffentliche Verlinkung; `robots: noindex` auf `/admin/*`.
- UI und APIs geben bei fehlendem `LEAD_ADMIN_SECRET` kein Funktionsleck preis (404 bzw. Hinweis auf der Seite).

**Später (Skizze):**

- **SSO** (Azure AD / SAP IAS) für interne Rollen.
- **OPA / policy-as-code** oder zentrales IAM: z. B. nur Gruppe `internal-sales` darf Lead-PII lesen; Trennung von „Marketing-Telemetrie“ und „Lead-PII“.
- **Auditing** in unveränderlichem Store (z. B. Append-Only-Tabelle in Postgres) statt nur JSON-Datei.

---

## 9. Migration zu CRM

1. Webhook (Wave 25) bleibt **Quelle der Wahrheit** für Downstream-Systeme.
2. n8n mappt Payload auf HubSpot/Pipedrive/Salesforce-Felder.
3. Inbox kann parallel laufen für **manuelle** Fälle oder schrittweise abgeschaltet werden, wenn CRM die Triage übernimmt.
4. Optional: Supabase/Postgres als einheitlicher Lead-Store statt JSONL + `ops-state.json`.

---

**Nachfolger:** [Wave 27 – Lead-Dedup & Kontakt-Historie](./wave27-lead-dedup-and-history.md) (`lead_contact_key`, Historie in der Inbox, Webhook 1.1).

---

*Wave 26 – operative Lead-Triage für DACH-B2B, bewusst klein gehalten.*
