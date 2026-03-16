# AI-Governance – Norm-Nachweise (EU AI Act / NIS2 / ISO 42001)

**Blueprint-Dokumentation.** Beschreibt, wie Board-Reports und Audit-Records über
`NormEvidenceLink` explizit mit Norm-Referenzen (EU AI Act, NIS2, ISO 42001)
verknüpft werden – als Nachweis gegenüber Prüfern und Aufsicht.

---

## 1. NormEvidenceLink – Datenmodell

Jeder NormEvidenceLink stellt einen Nachweisbezug zwischen einem
`BoardReportAuditRecord` und einer konkreten Norm-Referenz her:

- `framework` – z. B. `EU_AI_ACT`, `NIS2`, `ISO_42001`
- `reference` – z. B. `"Art. 9"`, `"Annex III-1"`, `"ISO 42001 6.2"`
- `evidence_type` – z. B. `"board_report"`, `"export_job"`, `"other"`
- `note` – Kurzbeschreibung, warum dieser Audit-Record als Nachweis taugt

---

## 2. Beispiel – EU AI Act

**Use-Case:** Art. 9 – Risikomanagementsystem für High-Risk-KI.

- `framework`: `EU_AI_ACT`
- `reference`: `"Art. 9"`
- `evidence_type`: `"board_report"`
- `note`: „Board-Report enthält konsolidierte Risiko-KPIs,
  High-Risk-Systeme und Governance-Alerts gemäß Art. 9.“

Der verknüpfte `BoardReportAuditRecord` referenziert eine konkrete Version des
Board-Reports (inkl. Hash), optional mit Exporten in DMS/DATEV.

---

## 3. Beispiel – NIS2

**Use-Case:** NIS2 Art. 21 – Incident-Management & Business Continuity.

- `framework`: `NIS2`
- `reference`: `"Art. 21"`
- `evidence_type`: `"board_report"`
- `note`: „Board-Report enthält Incident-Overview und Supplier-Risiko-Auswertung
  gemäß NIS2 Art. 21.“

---

## 4. Beispiel – ISO 42001

**Use-Case:** ISO 42001 – Abschnitt 6.2 (Ziele der Organisation).

- `framework`: `ISO_42001`
- `reference`: `"ISO 42001 6.2"`
- `evidence_type`: `"board_report"`
- `note`: „Board-KPIs und Alerts spiegeln AI-Governance-Ziele und
  Monitoring der Zielerreichung wider.“

---

## 5. Flow: Board-Report → Audit-Record → NormEvidenceLinks

1. **Board-Report generieren**  
   AI-Governance-Board-Report (JSON/Markdown) wird erzeugt.

2. **Audit-Record anlegen**  
   `POST /api/v1/ai-governance/report/board/audit-records`  
   – speichert einen Snapshot (inkl. Hash-Version) des Reports.

3. **Optional: Export-Jobs**  
   Export in DMS/SAP BTP/DATEV (`datev_dms_prepared`) für Archivierung.

4. **NormEvidenceLinks anlegen**  
   `POST /api/v1/ai-governance/report/board/audit-records/{audit_id}/norm-evidence`  
   – je Norm-Referenz ein oder mehrere Links (Framework, Reference, Evidence-Type, Note).

5. **Abfrage für Prüfer/Aufsicht**  
   `GET /api/v1/ai-governance/norm-evidence?framework=EU_AI_ACT&reference=Art.9`  
   – liefert alle Audit-Records und zugehörigen Evidenzen für diese Norm-Referenz.

---

*Dokumentation: ComplianceHub – AI-Governance Norm-Evidence Mapping.*

