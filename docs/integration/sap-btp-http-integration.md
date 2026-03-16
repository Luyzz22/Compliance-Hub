# SAP BTP HTTP / Cloud Integration – Board-Report-Export

**Blueprint-Dokumentation.** Beschreibt die Anbindung des ComplianceHub Board-Reports an SAP BTP HTTP-Inbound bzw. SAP Cloud Integration (iFlow) für NIS2-/EU-AI-Act-/ISO-42001-Reporting.

---

## 1. Use-Case

ComplianceHub erzeugt einen **AI Governance Board Report** (JSON + Markdown) mit KPIs, Compliance-Übersicht, Incidents und Supplier-Risiken. Dieser Report soll in SAP-Umgebungen weiterverarbeitet werden können:

- **SAP Cloud Integration (iFlow):** HTTP-Inbound-Adresse wird als `callback_url` beim Export-Job angegeben. ComplianceHub sendet den Report per POST an diese URL.
- **Weiterverarbeitung:** z.B. Ablage in DMS, S/4HANA-Dokumentenmanagement, Archiv oder Weiterleitung an Verantwortliche.

Der Export wird über **Export-Jobs** mit `target_system=sap_btp_http` ausgelöst. Es wird ein stabiles Payload-Schema und ein erkennbarer Header verwendet.

---

## 2. Payload-Schema (sap_btp_http)

ComplianceHub sendet einen **HTTP POST** mit JSON-Body. Alle Angaben sind Aggregat-/Systemdaten, keine personenbezogenen Daten.

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `tenant_id` | string | Mandanten-ID im ComplianceHub |
| `report_period` | string | Berichtszeitraum, z.B. `last_12_months` |
| `markdown` | string | Vollständiger Board-Report als Markdown (für PDF/Word/DMS) |
| `report_metadata` | object | Zusatzinfos zum Report |
| `report_metadata.job_id` | string | UUID des Export-Jobs |
| `report_metadata.generated_at` | string | ISO-8601-Zeitstempel der Report-Erzeugung |
| `report_metadata.period` | string | Identisch zu `report_period` |

Beispiel siehe `docs/integration/sap-btp-board-report-payload.json`.

---

## 3. Header

ComplianceHub setzt einen festen Header, damit die Integration in BTP eindeutig erkennbar ist:

| Header | Wert | Bedeutung |
|--------|------|-----------|
| `Content-Type` | `application/json` | JSON-Body |
| `X-ComplianceHub-Integration` | `sap_btp_http` | Kennzeichnung für SAP BTP HTTP-Inbound |

In SAP Cloud Integration kann anhand von `X-ComplianceHub-Integration: sap_btp_http` der Sender und das erwartete Schema identifiziert werden.

---

## 4. Erwartung aus Sicht von BTP (Inbound)

- **Methode:** POST  
- **Body:** JSON (siehe Payload-Schema)  
- **Authentifizierung:** Vom Aufrufer (ComplianceHub) abhängig. Aktuell sendet ComplianceHub keinen eigenen Auth-Header; die Inbound-Adresse kann in BTP z.B. per API Key, Basic Auth oder IP-Whitelist geschützt werden.  
- **Antwort:** HTTP 2xx bei Erfolg; bei 4xx/5xx wertet ComplianceHub den Job als „failed“ und speichert die Fehlermeldung.

---

## 5. Beispiel-iFlow-Skizze (Text)

1. **Eingang:** HTTP-Inbound (POST), z.B. `/api/board-report` oder von Cloud Integration bereitgestellte URL.
2. **Header-Prüfung:** Optional Prüfung auf `X-ComplianceHub-Integration: sap_btp_http`.
3. **Payload parsen:** JSON-Body auslesen (`tenant_id`, `report_period`, `markdown`, `report_metadata`).
4. **Weiterverarbeitung (Beispiele):**
   - **DMS:** Markdown oder daraus erzeugtes PDF in Dokumentenmanagement ablegen (Aktenzeichen, Mandant, Berichtszeitraum aus `report_metadata`).
   - **S/4HANA:** Dokument in S/4HANA Document Management Service ablegen, verknüpft mit Mandant/Organisation.
   - **E-Mail/Teams:** Report als Anhang oder Link an feste Empfänger (z.B. CISO, Aufsicht).
5. **Antwort:** HTTP 200 (oder 201) mit optionalem Body (z.B. `{"received": true, "document_id": "..."}`).

---

## 6. Beispiel-Payload abrufen (DEV/Docs)

In Nicht-Produktions-Umgebungen kann ein Beispiel-Payload ohne echten Job abgerufen werden:

```http
GET /api/v1/ai-governance/report/board/export-payload-example?target_system=sap_btp_http
```

Erforderlich: gleiche Authentifizierung wie für andere Board-Endpunkte (z.B. `x-api-key`, `x-tenant-id`). In Produktion (`COMPLIANCEHUB_ENV=production`) ist der Endpoint deaktiviert (404).

---

*Dokumentation: ComplianceHub Integration Blueprint – SAP BTP HTTP.*
