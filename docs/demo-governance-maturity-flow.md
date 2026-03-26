# Demo/Pilot: Governance Maturity Lens (Readiness + GAI + OAMI)

Ziel: In **10–15 Minuten** CISO-, Board- oder Advisor-Demo die **drei Säulen** zeigen: strukturelle **Readiness**, Nutzung der Plattform (**GAI**), und **operative KI-Überwachung** (**OAMI**). Alle Daten sind **synthetisch**, ohne echte Kundendaten.

Verwandte Runbooks:

- [`runtime-events-oami-operations-runbook.md`](./runtime-events-oami-operations-runbook.md) – Logs, ENV, Einzelskript Runtime-Events.  
- [`governance-operational-ai-monitoring.md`](./governance-operational-ai-monitoring.md) – OAMI-Fachspezifikation.  
- [`governance-activity-index.md`](./governance-activity-index.md) – GAI-Formel.

---

## 1. Kanonische Demo-Szenarien (Narrativ)

### Szenario A – Industrie-SME („Predictive Maintenance + Vision“)

| Aspekt | Inhalt |
|--------|--------|
| **Kontext** | Fertigung mit **SAP S/4HANA** und **SAP AI Core** (Demo-Erzählung); Fokus Hochrisiko **Qualitätskontrolle Vision** und **Arbeitssicherheit**. |
| **AI-Systeme** | Mind. zwei **high** (Anhang III), dazu **limited** / **low** (RAG, PM) – aus Template `industrial_sme`. |
| **NIS2** | Hochrisiko-Systeme mit Incident-/Lieferketten-KPIs; Actions zu **Art. 21** verknüpft. |
| **Cross-Reg** | EU AI Act **Art. 9, 11, 12** über Demo-Controls; ISO **42001** im Setup-Payload; Wizard-Schritte gesetzt. |
| **KPIs** | `incident_rate_ai`, `drift_indicator` Zeitreihen; Board-KPIs aus Register. |
| **Ziel-Signal** | **Readiness** eher **Managed** (Lücken sichtbar). **GAI** **mittel bis mittel-hoch** (8 Tage Telemetrie). **OAMI** **mittel** (Heartbeats, Snapshots, einige Incidents/Breaches, alles idempotent). |

**API-Template-Key:** `industrial_sme`  
**CLI-Preset:** `mittelstand-ag` → `demo-mittelstand-ag`

### Szenario B – Advisor / Kanzlei-Portfolio

| Aspekt | Inhalt |
|--------|--------|
| **Kontext** | Steuerberatung / GRC-Beratung mit **mehreren** Demo-Mandanten unterschiedlicher Branche. |
| **Umsetzung** | Zwei Mandanten seeden, z. B. `demo-mittelstand-ag` (`industrial_sme`) und `demo-grc-consulting` (`tax_advisor`); Advisor-Link optional mit `advisor_id` beim Seed. |
| **Story** | Im **Advisor-Portfolio** unterschiedliche Readiness- und Setup-Fortschritte vergleichen; pro Mandant **Governance Maturity** (API) und **Snapshot** mit OAMI-Block. |

**API-Template-Keys:** `tax_advisor`, `industrial_sme`  
**CLI-Preset:** `grc-consulting` → `demo-grc-consulting`

---

## 2. Provisionierung (Reihenfolge)

### Voraussetzungen

- `COMPLIANCEHUB_DEMO_SEED_TENANT_IDS` enthält die Ziel-`tenant_id`.  
- `COMPLIANCEHUB_DEMO_SEED_API_KEYS` gesetzt; Feature **demo_seeding** an.  
- Optional: KPI-Definitionen und Cross-Reg-Katalog (CLI/API-Seed ruft `ensure_*` auf).

### Schritt A – Kern-Demo-Daten

**API** (wie bisher):

```http
POST /api/v1/demo/tenants/seed
x-api-key: <demo-seed-key>
{"template_key": "industrial_sme", "tenant_id": "demo-mittelstand-ag"}
```

**CLI:**

```bash
python scripts/seed_demo_tenant.py --preset mittelstand-ag
# oder
python scripts/seed_demo_tenant.py --tenant-id demo-x --template industrial_sme --display-name "Demo AG"
```

Der Kern-Seed legt u. a. AI-Register, Klassifikationen, NIS2-KPI-Zeilen, Policies, Actions, Evidenzen, Cross-Reg-Controls, KPI-Werte, Board-Reports, Setup-Payload an.

### Schritt B – Governance-Maturity-Layer (GAI + OAMI)

Wird **automatisch** nach erfolgreichem `POST .../demo/tenants/seed` ausgeführt (gleiche Transaktions-Session-Kette wie im Code).

Manuell nachziehen (z. B. Mandant hatte schon AI-Systeme und vollständiger Seed liefert **409**):

```http
POST /api/v1/demo/tenants/governance-maturity-layer
x-api-key: <demo-seed-key>
{"tenant_id": "demo-mittelstand-ag"}
```

**CLI:** `seed_demo_tenant.py` ruft den Layer **immer** am Ende auf (auch wenn der Kern-Seed übersprungen wurde).

Der Layer:

1. Schreibt **usage_events** (Sessions + `workspace_feature_used` mit Governance-Features) – **idempotent** über einen Anker-Event.  
2. Schreibt synthetische **ai_runtime_events** für bis zu **zwei** Hochrisiko-Systeme (`synthetic_demo_seed`, stabile IDs).  
3. Aktualisiert **Incident-Summaries** (90-Tage-Fenster).  
4. Berechnet **Tenant-OAMI** und **persistiert** den Snapshot.

### Readiness / GAI / OAMI „rechnen“

- **Readiness:** wird bei `GET .../readiness-score` **on-the-fly** aus Mandantendaten berechnet – kein separater Job.  
- **GAI:** aus `usage_events` im gewählten Fenster (Standard 90 Tage in Governance Maturity).  
- **OAMI:** on-read und/oder Snapshot nach Layer (siehe oben).

---

## 3. Demo-Ablauf (10–15 Minuten)

1. **Workspace / Mandant wählen** – Banner „Demo (read-only)“; keine produktiven Writes.  
2. **Board → AI Compliance Board-Report** – Readiness-Karte (**Managed** o. ä.); vorgefertigte **Demo-Reports** ansehen („Demo-Report ansehen“); OAMI-Texte im generierten Report, sofern Report neu erzeugt (in Demo oft nur Lesen).  
3. **EU AI Act / KI-Register** – Hochrisiko-Systeme, Lücken (Supplier-Register, Logging).  
4. **Cross-Regulation** – Art. 9/11/12-Coverage, Gaps.  
5. **Governance Maturity (API)** – `GET /api/v1/tenants/{id}/governance-maturity`: Readiness + GAI + `operational_ai_monitoring` mit Erklärung.  
6. **Advisor** – Portfolio und Mandanten-Snapshot mit Readiness + OAMI-Kurztext (falls Advisor-Features aktiv).  
7. **CISO-Takeaway** – Post-Market-Monitoring (EU AI Act), Betriebsüberwachung (ISO 42001), Nachvollziehbarkeit (NIS2) – alles auf **Demo-Daten** bezogen.

---

## 4. Technische Kurzreferenz

| Komponente | Ort / Endpoint |
|------------|----------------|
| Kern-Seed | `app/services/demo_tenant_seeder.py`, `POST /api/v1/demo/tenants/seed` |
| GAI + Runtime + OAMI-Layer | `app/services/demo_governance_maturity_seed.py`, `POST .../governance-maturity-layer` |
| Synthetische Runtime-Specs | `app/services/demo_synthetic_runtime_events.py` |
| Einzelsystem-Runtime (CLI) | `scripts/seed_synthetic_ai_runtime_events.py` |

**Demo-Mandanten:** Runtime-**API-Ingest** bleibt **gesperrt** (403); Daten nur über Seed/Skripte.

---

*Version: 1.0 – abgestimmt auf ComplianceHub Demo-Seeding und Governance-Maturity-API.*
