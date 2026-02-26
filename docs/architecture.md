# Architecture Blueprint – Enterprise SaaS

## 1. Product Topology

1. Document Intake Layer  
   Input: XRechnung, ZUGFeRD, Vertrags‑PDFs  
   Capability: Format‑Erkennung, EN‑16931‑Validierung, Metadaten‑Extraktion.

2. Compliance Orchestration Layer  
   Rule‑ und AI‑Entscheidungen für DSGVO, GoBD und E‑Rechnung.  
   Human‑in‑the‑Loop‑Approval‑Queue für personenbezogene Daten.

3. Audit & Trust Layer  
   Hash‑basierter, unveränderbarer Event‑Log.  
   Zeitgestempelte Evidence‑Pakete für Betriebsprüfungen.

4. Integration Layer  
   DATEV‑Export, ERP/CRM‑Connectoren, Webhooks und n8n‑Flows.

## 2. Reference Runtime (MVP)

- API: FastAPI unter `app.main:app`.
- Rule Engine: Python‑Service `app.services.compliance_engine`.
- UI: Statisches Dashboard in `app/static`.
- Persistence: In‑Memory für MVP, Ziel: PostgreSQL + WORM‑Archiv.

## 3. Enterprise-SaaS-Prinzipien

- Mandantenfähiges Design (Tenant ID in allen Kernobjekten).
- Immutable Audit Trails mit SHA‑256‑Hash.
- Region‑Pinning für DACH‑Mandanten (Frankfurt‑Region).
- Human‑Approval‑Gates bei sensiblen Verarbeitungen.

