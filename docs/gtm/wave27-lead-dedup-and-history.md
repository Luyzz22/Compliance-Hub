# Wave 27 – Lead-Identität, Dedup-Hinweise & Kontakt-Historie

**Vorgänger:** [Wave 26 – Internes Lead-Inbox](./wave26-internal-lead-inbox.md)

---

## 1. Ziel

- Wiederholte Anfragen **derselben Person** (gleiche geschäftliche E-Mail) sollen **sichtbar gruppiert** werden, ohne Anfragen zu **löschen oder still zusammenzuführen**.
- **CRM/n8n** können später an stabilen Schlüsseln und Sequenzen andocken, ohne dass Compliance Hub ein CRM wird.

---

## 2. Dedup-Regeln (konservativ)

| Schlüssel | Herkunft | Verwendung |
| --------- | -------- | ----------- |
| `lead_contact_key` | `ct_v1_` + SHA-256 über normalisierte E-Mail (`email\|…`) | **Primär:** gleiche Person = gleicher Key |
| `lead_account_key` | `ac_v1_co_` + Hash des normalisierten Firmennamens, oder `ac_v1_dom_` + Domain (wenn Firma leer und keine Consumer-Domain) | **Sekundär:** Kontext „gleiche Organisation“, **kein** automatischer Kontakt-Merge |

- **Normalisierung E-Mail:** trim, lowercase.
- **Normalisierung Firma:** trim, lowercase, Whitespace zusammenziehen, trailing Satzzeichen entfernt.
- **Consumer-Domains** (gmail, web.de, …): für `lead_account_key` keine reine Domain-Gruppe, wenn keine sinnvolle Firma – vermeidet falsche Firmen-Dubletten bei Privatmail.

**Prinzip:** Lieber „Hinweis“ und manuelle Verknüpfung als aggressiver Merge.

---

## 3. Jede Einreichung bleibt eigener Datensatz

- JSONL: weiterhin **eine Zeile** `lead_inquiry` pro Formular-Submit (**immutable** Inhalt).
- Webhook: jede Einreichung erzeugt einen eigenen Payload mit eigener `lead_id` / `trace_id`.
- Zusätzlich werden **Snapshot-Felder** gesetzt (auch in `outbound`):

| Feld | Bedeutung |
| ---- | --------- |
| `schema_version` | `1.1` für neue Anfragen (ältere Zeilen können `1.0` bleiben) |
| `lead_contact_key` | Stabiler Kontakt-Schlüssel |
| `lead_account_key` | Optional, Account-/Firmen-Gruppierung |
| `contact_inquiry_sequence` | Laufnummer dieser Person (1, 2, 3, …) |
| `contact_first_seen_at` | Erste bekannte Anfrage dieses Kontakts |
| `contact_latest_seen_at` | Zeitpunkt **dieser** Anfrage |
| `duplicate_hint` | `none` \| `same_email_repeat` (nur bei wiederholter E-Mail) |

Lesende APIs leiten fehlende Wave-27-Felder bei **alten** Zeilen aus `business_email` / Firma **nach** (Retrofit beim Merge).

---

## 4. Gruppierte Kontakt-Historie (Inbox)

- Liste: Rollup über **gesamten** Store (`readAllLeadRecordsMerged`) pro `lead_contact_key`:
  - `contact_submission_count`
  - `contact_has_unresolved_repeat` (mehr als eine Anfrage **und** mindestens eine mit Aufmerksamkeit: Triage `received` oder Weiterleitung `failed`)
  - `other_contacts_on_same_account` (Anzahl **weiterer** Kontakt-Keys unter gleichem `lead_account_key`)
- Detail: `GET /api/admin/lead-inquiries/[leadId]` liefert `contact_history` (chronologische Timeline derselben E-Mail).

**Filter (Query):**

- `repeated_contacts=1` – nur Kontakte mit mehr als einer Submission.
- `unresolved_repeated=1` – wiederholt **und** mindestens eine offene Aufmerksamkeit in der Gruppe.

---

## 5. Ops / Audit (Wave 26+27)

Neue oder erweiterte Aktivitäten:

| Aktion | Wann |
| ------ | ---- |
| `contact_repeat_detected` | Zweite und jede weitere Anfrage gleicher E-Mail (nach Persist) |
| `possible_duplicate_noted` | Gleiche Account-Gruppe, aber **anderer** Kontakt-Key (Hinweis, kein Merge) |
| `manual_related_leads_updated` | Manuelle Verknüpfung zu anderen `lead_id` |
| `duplicate_review_updated` | Status `none` / `suggested` / `confirmed` |

**PATCH** (intern): `manual_related_lead_ids` (max. 20 UUIDs, müssen existieren), `duplicate_review`.

---

## 6. CRM / n8n Sync (Vorbereitung, kein vollständiger Sync)

Webhook-Body (`schema_version` **1.1**) enthält u. a.:

- `lead_id` – diese Einreichung
- `lead_contact_key` – stabiler Kontakt in Downstream-Systemen
- `lead_account_key` – optionale Firmen-/Domain-Gruppe
- `contact_inquiry_sequence` – wie viele Anfragen diese E-Mail bisher hatte (inkl. dieser)
- `contact_first_seen_at` / `contact_latest_seen_at` – Zeitfenster für Deduplizierungs-Logik im CRM

Empfohlene spätere Muster:

- **HubSpot / Pipedrive:** Kontakt anhand `lead_contact_key` oder abgeleiteter E-Mail; **Deal/Aktivität** pro `lead_id` oder pro Sequenz.
- **n8n:** Branch nach `duplicate_hint` und `contact_inquiry_sequence`, z. B. andere Slack-Queue ab der zweiten Anfrage.

---

## 7. Grenzen & Skalierung

- Rollups lesen die **gesamte** JSONL pro Admin-Request – für Gründer-/Sales-Volumen gedacht, nicht für sehr große Stores.
- Persistenz ephemer auf Vercel unverändert: **CRM/Webhook** bleibt Quelle der Wahrheit für längerfristige Historie.

---

*Wave 27 – additive Identität und Historie ohne CRM-Komplexität.*
