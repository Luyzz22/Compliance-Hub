# WP-Prüfungsdokumentation – Board-Report Audit-Ready

**Blueprint-Dokumentation.** Beschreibung, wie **BoardReportAuditRecord** und **Export-Jobs** zusammen ein prüfungstaugliches Set an Nachweisen für EU AI Act, NIS2 und ISO 42001 bilden (Audit-Ready-Schicht ohne vollständiges DMS).

---

## 1. Ziel

- **Versionierung:** Jeder „Schnappschuss“ eines Board-Reports kann als Audit-Record abgelegt werden (inkl. Hash-Version des Report-Inhalts).
- **Referenzen auf Exporte:** Verknüpfung mit Export-Jobs (z. B. SAP BTP, DATEV-DMS) – welcher Report wurde wohin exportiert?
- **Prüfungsnachweis:** Für Wirtschaftsprüfer und Aufsicht: Nachvollziehbarer Ablauf „Report erzeugen → Audit-Record anlegen → Export in DMS/DATEV → Referenz im Prüfungsbericht“.

---

## 2. Bausteine

| Baustein | Beschreibung |
|----------|--------------|
| **Board-Report (JSON/Markdown)** | Aktueller AI-Governance-Report (KPIs, Compliance, Incidents, Supplier-Risiko, Alerts). |
| **BoardReportAuditRecord** | Eintrag mit report_generated_at, report_version (Hash), purpose, status (draft/final), linked_export_job_ids. |
| **Export-Jobs** | generic_webhook, sap_btp_http, datev_dms_prepared, … – versendeter Report an externe Systeme. |

Audit-Record + verknüpfte Export-Job-IDs = nachvollziehbarer Pfad „dieser Report, diese Version, exportiert in diese Systeme“.

---

## 3. Beispiel-Ablauf für WP / Prüfungsdokumentation

1. **Report generieren**  
   Nutzer oder System ruft den aktuellen Board-Report ab (GET Board-Report oder Markdown).

2. **Audit-Record anlegen**  
   `POST /api/v1/ai-governance/report/board/audit-records`  
   - Body: `purpose` (z. B. „NIS2 Board-Bericht Q1 2026“), `status` (draft/final), optional `linked_export_job_ids`.  
   - Response: Audit-Record mit `id`, `report_version`, `report_generated_at`, `created_at`, `created_by`.

3. **Export in DMS/DATEV**  
   `POST /api/v1/ai-governance/report/board/export-jobs`  
   - z. B. `target_system: datev_dms_prepared`, `callback_url`, optional `metadata` (Mandant, Aktenzeichen).  
   - Response: Export-Job mit `id`, `status` (sent/failed).

4. **Verknüpfung nachziehen (optional)**  
   Falls der Audit-Record vor den Export-Jobs angelegt wurde: Audit-Record kann bei Anlage die Liste `linked_export_job_ids` enthalten; bei späterer Anlage werden die erhaltenen Job-IDs in einem (ggf. aktualisierten) Ablauf in der Dokumentation referenziert.  
   GET Audit-Record by id liefert `linked_export_jobs` (aufgelöste Job-Details).

5. **Referenz im Prüfungsbericht**  
   WP kann Audit-Record-ID und ggf. Export-Job-IDs sowie report_version in der Prüfungsdokumentation anführen (EU AI Act, NIS2, ISO 42001 – Nachweis „Board-Report Version X am Datum Y exportiert in System Z“).

---

## 4. API-Überblick

| Methode | Endpoint | Kurzbeschreibung |
|---------|----------|------------------|
| POST | `/api/v1/ai-governance/report/board/audit-records` | Audit-Record für aktuellen Report anlegen (Version = Hash). |
| GET | `/api/v1/ai-governance/report/board/audit-records` | Liste (paginiert, filterbar nach status). |
| GET | `/api/v1/ai-governance/report/board/audit-records/{audit_id}` | Einzelrecord inkl. verknüpfter Export-Jobs. |

Alle Endpunkte tenant-isoliert, Auth wie bei den übrigen Board-Endpunkten.

---

## 5. Normbezug (EU AI Act, NIS2, ISO 42001)

- **EU AI Act:** High-Risk-Systeme, Governance-Reife – Board-Report und Audit-Record als Nachweis des Überblicks.  
- **NIS2:** Incident-/Supplier-Risiko-KPIs – Report-Version und Export in DMS/Archiv für Nachweisführung.  
- **ISO 42001:** AI-Managementsystem, Reifegrad – Audit-Record mit purpose und status für Prüfdokumentation.

Die Kombination aus Audit-Record (Version, Zeitpunkt, Zweck) und Export-Jobs (Wohin wurde exportiert?) bildet die Grundlage für eine prüfungstaugliche Dokumentation ohne vollständiges DMS/Freigabe-Workflow-System.

---

*Dokumentation: ComplianceHub Integration Blueprint – WP-Prüfungsdokumentation.*
