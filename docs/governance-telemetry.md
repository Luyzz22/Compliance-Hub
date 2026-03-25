# Governance Telemetry – Enterprise Observability Blueprint

**ComplianceHub** – interne Referenz für GRC, Security und Engineering.  
Ziel: **einheitliche, auditierbare Nutzungssignale** ohne Personenbezug (EU AI Act, NIS2, ISO 27001/27701, ISO 42001, DSGVO-Minimierung).

---

## 1. Leitprinzipien

| Prinzip | Umsetzung |
|--------|-----------|
| **Keine PII** | Keine Namen, E-Mails, Freitexte, IP-Adressen in Workspace-Payloads. Nur `tenant_id`, Enums, technische IDs, Routen-Pfade. |
| **Eine Senke** | `emit_workspace_event` → Tabelle `usage_events` (+ optional eine Zeile strukturiertes App-Log bei `COMPLIANCEHUB_WORKSPACE_TELEMETRY_STRUCTURED_LOG=1`). |
| **Whitelist** | Zusatzfelder nur aus erlaubter Schlüsselliste; String-Werte müssen dem Regex für technische IDs/Keys entsprechen. |
| **Best effort** | Schreibfehler brechen API-Requests nicht. |
| **Multi-Tenant** | `tenant_id` immer setzen; Advisor-Pfade ergeben `actor_type=advisor`. |

---

## 2. Kanonisches Event-Modell (JSON)

### 2.1 Gespeicherte / geloggte Payload-Struktur

Alle Workspace-Events werden als **flaches JSON-Objekt** persistiert (Felder aus `build_workspace_event_body` plus **eingemischte** Whitelist-Felder – es gibt **kein** verschachteltes Objekt `extra` in der Datenbank).

**Pflichtfelder (immer vorhanden):**

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `event_type` | string | Kanonisch: `workspace_session_started`, `workspace_feature_used`, `workspace_mutation_blocked` |
| `tenant_id` | string | Mandanten-ID (RLS-Key). |
| `workspace_mode` | string | `production` \| `demo` \| `playground` (aus Server-Telemetrie-Kontext). |
| `actor_type` | string | `tenant` \| `advisor` \| `system` \| `unknown` – abgeleitet u. a. aus Request-Pfad. |
| `timestamp` | string | ISO 8601 UTC, z. B. `2026-03-25T12:00:00Z` |

**Häufige optionale Felder:**

| Feld | Typ | Beschreibung |
|------|-----|--------------|
| `result` | string | z. B. `success`, `forbidden_demo_readonly` |
| `feature_name` | string | Semantischer Feature-Key (snake_case, siehe Abschnitt 4). |
| `route` | string | OpenAPI-Routen-Template oder Pfad (zyklusarm). |
| `method` | string | HTTP-Methode in Großbuchstaben, z. B. `GET`, `POST`. |

**Optionale Dimensionen (Whitelist – erscheinen auf **Top-Level** der Payload, wenn gesetzt und valid):**

`action_id`, `ai_system_id`, `audit_record_id`, `classification_id`, `control_id`, `evidence_id`, `export_job_id`, `framework_key`, `job_id`, `report_id`, `requirement_id`, `route_name`, `surface`, `template_key`

- **`route` (Backend)** = API-Routen-Template aus dem Request.  
- **`route_name` (Client/Proxy)** = UI-Pfad-Konvention, z. B. `/tenant/cross-regulation-dashboard` – für Dashboards „welche Oberfläche wurde genutzt?“.

### 2.2 Logische vs. kanonische `event_type`-Namen

| Logisch (Dokumentation) | Kanonisch im Code / DB |
|-------------------------|-------------------------|
| Session gestartet | `workspace_session_started` |
| Feature genutzt | `workspace_feature_used` |
| Mutation blockiert (Demo/RO) | `workspace_mutation_blocked` |

---

## 3. Wo Events entstehen (Backend)

| Event | Auslöser | Typische Integration |
|-------|-----------|----------------------|
| `workspace_session_started` | `GET /api/v1/workspace/tenant-meta` | Dedupe (z. B. 24h) pro Tenant/Event-Typ; belegt aktive Workspace-Session aus Sicht Telemetrie. |
| `workspace_feature_used` | `GET /api/v1/workspace/feature-used?feature_key=…` (+ optionale Query-Parameter) **oder** direkte `log_workspace_feature_used`-Aufrufe in relevanten API-Handlern | Feature-Nutzung; Server setzt `workspace_mode`, `actor_type`, `route`. |
| `workspace_mutation_blocked` | `demo_tenant_guard` bei blockierter schreibender Operation | `result=forbidden_demo_readonly`; zeigt durchgesetzten Read-only-Modus. |

**Hilfsfunktionen (Python):**

- `build_workspace_event_body(...)` – baut die kanonische Payload-Dict.  
- `emit_workspace_event(session, event_type, tenant_id, workspace_mode=…, actor_type=…, …)` – schreibt über `log_usage_event`.  
- `log_workspace_feature_used`, `log_workspace_session_started`, `log_workspace_mutation_blocked` – fachliche Wrapper in `workspace_telemetry.py`.

### 3.1 Beispiel: Feature mit `ai_system_id` und `framework_key`

```python
from app.demo_tenant_guard import workspace_mode_for_telemetry
from app.services import usage_event_logger
from app.services import workspace_telemetry

# Innerhalb eines FastAPI-Handlers mit session, tenant_id, request:
workspace_telemetry.emit_workspace_event(
    session,
    usage_event_logger.WORKSPACE_FEATURE_USED,
    tenant_id,
    workspace_mode=workspace_mode_for_telemetry(session, tenant_id),
    actor_type=workspace_telemetry.actor_type_for_request_path(request.url.path),
    feature_name="ai_system_detail",
    result="success",
    route=workspace_telemetry.route_template_from_request(request),
    method=request.method,
    extra={
        "ai_system_id": ai_system_id,
        "framework_key": "EU_AI_ACT",
    },
)
```

### 3.2 Beispiel: Mutation blockiert mit `route_name` im Kontext

```python
workspace_telemetry.emit_workspace_event(
    session,
    usage_event_logger.WORKSPACE_MUTATION_BLOCKED,
    tenant_id,
    workspace_mode=mode,
    actor_type="tenant",
    result="forbidden_demo_readonly",
    route="/api/v1/ai-systems/{ai_system_id}",
    method="POST",
    extra={
        "route_name": "/tenant/ai-systems",
        "ai_system_id": "sys-import-001",
    },
)
```

### 3.3 Beispiel: Reines Body-Bauen (Tests, Export)

```python
body = workspace_telemetry.build_workspace_event_body(
    event_type="workspace_feature_used",
    tenant_id="t-sap-btp-demo",
    workspace_mode="production",
    actor_type="tenant",
    feature_name="board_reports_overview",
    result="success",
    route="/api/v1/workspace/feature-used",
    method="GET",
    extra={"route_name": "/board/ai-compliance-report"},
)
```

---

## 4. `feature_name` – empfohlener Kanon (Governance)

**Regel:** nur `snake_case`, `[a-z0-9_]`, Länge sinnvoll ≤ 64 Zeichen; neue Werte **review-pflichtig** (Product + Security).

### 4.1 UI-/Proxy-kanonisch (Next.js `trackWorkspaceFeatureUsed`)

| `feature_name` | Bedeutung |
|----------------|-----------|
| `playbook_overview` | AI Governance Playbook (Übersicht). |
| `cross_regulation_summary` | Cross-Regulation-Dashboard (Summary-Ansicht). |
| `board_reports_overview` | Board-Reports-Übersicht / Liste. |
| `ai_system_detail` | KI-System-Detail im Mandanten-Workspace. |

### 4.2 Erweitert (Berater-Workspace / API-first)

| `feature_name` | Bedeutung |
|----------------|-----------|
| `advisor_governance_snapshot` | Abruf Advisor-Mandanten-Governance-Snapshot (empfohlen bei Instrumentierung von `GET …/governance-snapshot`). |

### 4.3 Weitere im Backend bereits genutzte Keys (API-Hits)

Diese entstehen **serverseitig** beim Aufruf bestimmter Endpunkte (nicht identisch mit allen UI-Enums):

- `ai_governance_playbook` – u. a. Compliance-Overview-API  
- `cross_regulation_dashboard` – Cross-Regulation-Summary-API  
- `board_report_detail` – Board-Report-Detail (Mandant/Berater)  
- Beliebige weitere `feature_key` über `GET /api/v1/workspace/feature-used`, sofern Pattern erlaubt  

**Interpretation für Audits:** UI-Events (`*_overview`, `*_summary`) messen **Sichtbarkeit der Oberfläche**; API-gekoppelte Namen messen **Backend-Nutzung**. Beides darf parallel vorkommen – in Auswertungen trennen oder mappen.

---

## 5. Frontend-Integrationsmuster

### 5.1 Layout-Ebene

- **`TenantWorkspaceShell`** (Client) im **Tenant-Layout** und **Board-Layout** ruft **`useWorkspaceMode(tenantId)`** einmal pro Shell auf und rendert den Modus-Banner.  
- Untergeordnete Views nutzen dieselbe Tenant-ID; optional später **Context-Provider**, wenn Meta nur einmal gefetcht werden soll.

### 5.2 Feature-Tracking (ohne PII)

- Helper: **`trackWorkspaceFeatureUsed`** (`frontend/src/lib/workspaceTelemetry.ts`).  
- Ablauf: `POST /api/workspace/feature-used` (Same-Origin) → Next.js-Route proxied als `GET` zum Backend mit `x-tenant-id` und Server-API-Key.  
- **Erlaubte JSON-Felder:** `tenant_id`, `feature_name`, `workspace_mode` (Client-Spiegel), optional `ai_system_id`, `framework_key`, `route_name`.  
- **Niemals:** Nutzername, E-Mail, Freitext, Dateinamen, Suchbegriffe.

### 5.3 View-Mount (ein Event pro „Leben“ der Seite)

| Ansicht | `feature_name` | `route_name` (Konvention) |
|---------|----------------|---------------------------|
| AI Governance Playbook | `playbook_overview` | `/tenant/ai-governance-playbook` |
| Cross-Regulation Dashboard | `cross_regulation_summary` | `/tenant/cross-regulation-dashboard` |
| Board Reports | `board_reports_overview` | `/board/ai-compliance-report` |
| AI-System-Detail | `ai_system_detail` | `/tenant/ai-systems/{id}` + `ai_system_id` setzen |

Komponente: **`GovernanceViewFeatureTelemetry`** – feuert erst, wenn Workspace-Meta geladen ist (`meta != null`), mit Ref-Guard gegen Doppel-Sendung (Strict Mode).

---

## 6. Whitelist-Policy (`extra` / optionale Top-Level-Felder)

**Warum Whitelist?**

- **DSGVO / DACH:** Datenminimierung und Zweckbindung – Nutzungsmessung darf nicht dazu dienen, Personenprofile zu bilden. Technische IDs und Routen reichen für Betrieb, Nachweis und Aggregatauswertung.  
- **NIS2 / Betriebssicherheit:** Nachvollziehbarkeit **welcher Mandant** **welche Governance-Oberfläche** nutzt, ohne Inhalte personenbezogener Vorgänge zu loggen.  
- **ISO 27001 / 42001:** Nachweisbarkeit von Zugriffen auf kritische Steuerungsfunktionen (AI-Governance) ohne sensible Geschäftsdaten in Telemetrie.

**String-Validierung:** nur alphanumerisch plus `_.:/-`, Länge begrenzt – verwirft Freitext und injizierte Payloads.

---

## 7. Beispiel-Abfragen (Structured Logs / SIEM)

Annahme: eine JSON-Zeile pro Event im Log (Key-Value oder JSON), Feldnamen wie in der Payload.

### 7.1 Mandanten mit aktiver Cross-Regulation-Nutzung (30 Tage)

**Frage an die Daten:** Welche `tenant_id` hatten mindestens ein `workspace_feature_used` mit `feature_name` in (`cross_regulation_summary`, `cross_regulation_dashboard`)?

**Beispiel (Elasticsearch/Lucene-artig):**

```text
event_type:"workspace_feature_used"
AND (feature_name:"cross_regulation_summary" OR feature_name:"cross_regulation_dashboard")
AND @timestamp:[now-30d TO now]
```

Aggregation: Terms auf `tenant_id`, min_doc_count 1.

**Regulatorik:** **NIS2** – Nachweis, dass Monitoring/Steuerungsinstrumente genutzt werden; **ISO 42001** – Evidenz für Nutzung des AI-Governance-Stacks; **ISO 27001** – Nutzer-/Mandantenaktivität auf Funktionsebene (ohne Personenbezug).

### 7.2 Mutation blockiert nach `route_name` (7 Tage)

```text
event_type:"workspace_mutation_blocked"
AND result:"forbidden_demo_readonly"
AND @timestamp:[now-7d TO now]
```

Aggregation: Terms auf `route_name` (falls gesetzt), alternativ `route`.

**Regulatorik:** Nachweis, dass **Schreibschutz** in Demo/Playground greift (**EU AI Act**-Piloten, **DSGVO**-Demo ohne echte Verarbeitung); **ISO 27001** – technische Durchsetzung von Zugriffs-/Änderungsregeln.

### 7.3 Feature-Events mit Bezug zu High-Risk-KI (90 Tage, ein Mandant)

```text
event_type:"workspace_feature_used"
AND tenant_id:"<TENANT_ID>"
AND _exists_:ai_system_id
AND @timestamp:[now-90d TO now]
```

Optional JOIN/Anreicherung in DWH: `ai_system_id` gegen Register-Tabelle filtern auf `risk_level=high` (außerhalb des Log-Streams).

**Regulatorik:** **EU AI Act** – Nachverfolgbarkeit der Arbeit mit konkreten hochriskanten Systemen; **ISO 42001** – operative Überwachung des AI-Managementsystems; **NIS2** – Fokus auf kritische digitale Dienste/KI in KRITIS-Kontexten.

---

## 8. Enterprise / SAP BTP

- **Mandanten** (z. B. SAP BTP Subaccount → `tenant_id`) erscheinen konsistent in allen Events.  
- **Empfehlung:** In Verträgen/DPAs klarstellen, dass diese Telemetrie **keine** Inhalte von KI-Anwendungen, keine Prompts und keine personenbezogenen Nutzer-IDs enthält.  
- **Export:** `usage_events` oder strukturierte Logs an Kunden-SIEM (JSON Lines) – Felder wie oben, ohne Erweiterung um PII.

---

## 9. Änderungsprozess

1. Neues `feature_name` oder neuer Whitelist-Key → **Security + Product** Review.  
2. Backend: `workspace_telemetry._EXTRA_ALLOWED_KEYS` nur bei triftigem Grund erweitern.  
3. Frontend: Enum in `WORKSPACE_GOVERNANCE_FEATURES` + Proxy-Validierung.  
4. Diese Datei und ggf. `docs/workspace-telemetry-compliance.md` aktualisieren.

---

## 10. Verwandte Dateien (Code)

| Bereich | Datei |
|---------|--------|
| Event-Konstanten | `app/services/usage_event_logger.py` |
| Payload, Whitelist, Emit | `app/services/workspace_telemetry.py` |
| Feature-Used HTTP | `app/main.py` (`/api/v1/workspace/feature-used`) |
| Next.js Proxy | `frontend/src/app/api/workspace/feature-used/route.ts` |
| Client-Helper | `frontend/src/lib/workspaceTelemetry.ts` |
| View-Hook / Shell | `frontend/src/hooks/useWorkspaceMode.ts`, `TenantWorkspaceShell` |

---

*Stand: interne Blueprint-Version für ComplianceHub; bei Abweichungen zum Code gewinnt der Code – diese Dokumentation dann anpassen.*
