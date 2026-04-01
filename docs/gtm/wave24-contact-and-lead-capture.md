# Wave 24 – Kontakt, Lead-Capture & CTA-Architektur

**Ziel:** Von **mailto-first** zu **form-first** mit minimaler UI-Änderung; zuverlässigere Erfassung, Segmentierung für Sales-Triage, statement-sichere Begleittexte.

**Kanonische Homepage:** [complywithai.de](https://complywithai.de/)

---

## 1. Architektur (Überblick)

| Element | Pfad / Mechanismus |
| ------- | ------------------ |
| **Kontaktseite** | `GET /kontakt?quelle=<string>` – Next.js `frontend/src/app/kontakt/page.tsx` |
| **Formular** | Client: `frontend/src/components/contact/ContactLeadForm.tsx` |
| **Lead-POST** | `POST /api/lead-inquiry` – `frontend/src/app/api/lead-inquiry/route.ts` |
| **Telemetrie (leicht)** | `POST /api/marketing-event` – `frontend/src/app/api/marketing-event/route.ts` |
| **CTA mit Klick-Tracking** | `TrackedContactLink` – `frontend/src/components/contact/TrackedContactLink.tsx` |
| **URL-Helfer** | `contactPageHref(quelle)` – `frontend/src/lib/publicContact.ts` |
| **Segment-Enum & Limits** | `frontend/src/lib/leadCapture.ts` |
| **Fallback mailto** | `PUBLIC_CONTACT_MAILTO` / `PUBLIC_CONTACT_EMAIL` – weiterhin gültig |

---

## 2. Lead-Datenmodell (POST-Body)

| Feld | Pflicht | Beschreibung |
| ---- | ------- | ------------ |
| `name` | ja | Ansprechpartner |
| `work_email` | ja | Geschäftliche E-Mail |
| `company` | ja | Unternehmen / Kanzlei |
| `segment` | ja | `industrie_mittelstand` · `kanzlei_wp` · `enterprise_sap` · `sonstiges` |
| `message` | nein | Freitext (optional) |
| `source_page` | ja | Serverseitig aus Formular: Wert von Query `quelle` (Triage: Herkunft der Anfrage) |
| `company_website` | nein | **Honeypot** – muss leer bleiben |

**Routing heute:** Strukturierter **Server-Log** (`console.info` mit Präfix `[lead-inquiry]`) inkl. vollständiger geschäftlicher E-Mail für manuelle Bearbeitung / Monitoring.

**Optional:** `LEAD_INBOUND_WEBHOOK_URL` (Env) – POST derselben JSON-Nutzlast + `received_at` an CRM, Slack, Zapier o. Ä.

---

## 3. Was sich gegenüber Wave 23 ändert

| Vorher | Nachher |
| ------ | ------- |
| „Demo anfragen“ → direkt `mailto:` | Primär **`/kontakt?quelle=…`** mit Formular |
| Kein Segment | **Dropdown** Industrie / Kanzlei / Enterprise / Sonstiges |
| Keine serverseitige Erfassung | **API-Route** + optional Webhook |
| Kein Klick-Tracking | **`cta_click`** per `sendBeacon` / `fetch` (keine PII) |
| Footer „Kontakt“ → mailto | Footer **Link** zur Kontaktseite (`quelle=footer`) |

**Sekundärer Fallback:** Auf der Kontaktseite Button **„Stattdessen E-Mail öffnen“** (`mailto:`); bei Submit-Fehler Hinweis mit derselben Adresse.

---

## 4. `quelle`-Werte (Triage)

| `quelle` | Bedeutung |
| -------- | --------- |
| `home-hero` | Hero „Demo anfragen“ |
| `home-integrations` | Abschnitt Integrationen „Kontakt aufnehmen“ |
| `home-mid-cta` | Mid-Page-CTA „Demo anfragen“ |
| `footer` | Footer-Link „Kontakt“ |
| `kontakt-direct` | `/kontakt` ohne Query |
| `static-wave22-header` / `…-hero` / … | Statische HTML-Artefakte unter `website/` (absolute URL auf complywithai.de) |
| `one-pager-*` | `website/sales-one-pager.html` |

---

## 5. Telemetrie-Events (ohne PII)

| Event | Auslöser |
| ----- | -------- |
| `cta_click` | Klick auf `TrackedContactLink` |
| `lead_form_started` | Erste Interaktion mit Formularfeld |
| `lead_form_submit_attempt` | Submit |
| `lead_form_submitted` | HTTP 200 von `/api/lead-inquiry` |
| `lead_form_submit_error` | Validierungs- oder Netzwerkfehler |

Logs: `[marketing-event]` mit `event`, optional `cta_id`, `quelle`, `t`.

---

## 6. Compliance-Copy (Kurz)

- Formular: **unverbindlich**, **keine automatischen Verträge**, Erstkontakt **keine Rechtsberatung**.
- Erfolg: Rückmeldung in wenigen Werktagen, keine rechtsverbindliche Zusage.

Abgleich: `docs/gtm/compliance-statement-library-de.md`, `docs/gtm/tone_of_voice_de.md`.

---

## 7. Statische HTML-Dateien

`website/compliancehub-landing.html` und `website/sales-one-pager.html` verlinken CTAs per **absoluter URL** `https://complywithai.de/kontakt?quelle=…`, damit sie auch außerhalb des Next-Hostings funktionieren.

---

## 8. Erweiterungen (später)

- **CRM** (HubSpot, Pipedrive): Webhook oder serverseitiger Adapter statt nur Log.
- **Calendly / Terminlink** nach erfolgreichem Submit oder als zweite CTA.
- **Rate-Limiting** / CAPTCHA bei Missbrauch.
- **Double-Opt-In** nur wenn rechtlich/marketingseitig nötig (derzeit reine Geschäftsanfrage).
- **i18n** für `quelle`-Mapping in Reports.

---

*Wave 24 – form-first Kontakt, mailto sekundär.*

**Nachfolger:** [Wave 25 – Lead-Routing & Intake-Governance](./wave25-lead-routing-and-intake-governance.md) (Routing, JSONL-Persistenz, Webhook-Retries, Admin-API, Anti-Abuse) · [Wave 26 – Internes Lead-Inbox](./wave26-internal-lead-inbox.md) (`/admin/leads`, Triage, Ops-State).
