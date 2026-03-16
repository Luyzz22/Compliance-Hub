# DMS-Generic – Board-Report-Archivierung

**Blueprint-Dokumentation.** Beschreibt die perspektivische Anbindung von ComplianceHub an generische DMS-/Archiv-Systeme für die Ablage von AI-Governance-Board-Reports (NIS2-, EU-AI-Act-, ISO-42001-Dokumentation).

---

## 1. Ziel

Board-Reports sollen in Unternehmens-DMS oder Archiv-Systemen abgelegt werden können, z.B.:

- **Generische DMS-APIs** (REST): Dokument + Metadaten hochladen
- **Archiv-Connector** (z.B. SAP Archive Link, DATEV-DMS, branchenspezifische Lösungen)
- **Compliance-Nachweis:** NIS2, EU AI Act, ISO 42001 – Berichtszeitraum, Mandant, Normbezug eindeutig zuordenbar

Aktuell ist `target_system=dms_generic` im ComplianceHub als **Platzhalter** implementiert (Status `not_implemented`). Diese Doku dient als Vorlage für die spätere Integration.

---

## 2. Metadaten-Felder (Empfehlung für DMS)

Für die Ablage im DMS/Archiv sollten folgende Metadaten mitgeführt werden (siehe auch `docs/integration/dms-generic-board-report-metadata.json`):

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| **Mandant** | string | Tenant-ID (ComplianceHub `tenant_id`) – Zuordnung zum Unternehmen/Mandanten |
| **Berichtszeitraum** | string / von-bis | z.B. `last_12_months` oder explizit `berichtszeitraum_von` / `berichtszeitraum_bis` (Datum) |
| **Aktenzeichen** | string | Eindeutige Referenz (z.B. `AI-GOV-BR-2026-001`) für Ablage und Nachweis |
| **Normbezug** | array[string] | Relevante Normen: z.B. `EU AI Act`, `NIS2`, `ISO 42001`, `ISO 27001`, `DSGVO` |
| **Dokumenttyp** | string | z.B. `AI-Governance-Board-Report` |
| **Version** | string | Schema- oder Report-Version |
| **Job-ID** | string | UUID des Export-Jobs (Rückverfolgbarkeit) |
| **Erzeugungszeitpunkt** | string | ISO-8601 (generated_at) |

Diese Felder ermöglichen eine ordnungsgemäße Ablage und spätere Suche (z.B. „alle Board-Reports NIS2 für Mandant X im Jahr 2026“).

---

## 3. Perspektivischer Ablauf (dms_generic)

1. **ComplianceHub:** Nutzer löst Export mit `target_system=dms_generic` aus (ggf. mit Konfiguration: DMS-URL, Mandant, Aktenzeichen-Schema).
2. **Payload:** Wie bei sap_btp_http oder erweitert um DMS-spezifische Metadaten (Aktenzeichen, Normbezug, Berichtszeitraum).
3. **DMS-Connector:** Eigenes Modul oder Cloud-Integration-Flow ruft DMS-API auf (Dokument = Markdown oder PDF, Metadaten = obige Felder).
4. **Archiv:** Dokument wird mit Metadaten abgelegt; Compliance-Nachweis ist über Aktenzeichen und Normbezug abrufbar.

---

## 4. Normbezug (EU AI Act / NIS2 / ISO 42001)

Für die Board-Reports sind u.a. folgende Normen relevant; sie sollten im Metadaten-Feld **Normbezug** geführt werden:

- **EU AI Act** – High-Risk-KI-Systeme, Governance, Transparenz
- **NIS2** – Incident-Meldung, Lieferanten-Risiko, KRITIS
- **ISO 42001** – AI-Managementsystem, Reifegrad
- **ISO 27001** – Informationssicherheit (Querverweis)
- **DSGVO** – Datenschutz, DPIA bei High-Risk-KI

Damit können Berichte im DMS nach Norm und Zeitraum gefiltert werden.

---

## 5. Beispiel-Metadaten (JSON)

Siehe `docs/integration/dms-generic-board-report-metadata.json`: Enthält ein Beispiel für die Kombination aus ComplianceHub-Payload und DMS-Metadaten (Aktenzeichen, Mandant, Berichtszeitraum, Normbezug). Alle Werte sind Platzhalter – keine echten personenbezogenen Daten.

---

*Dokumentation: ComplianceHub Integration Blueprint – DMS Generic.*
