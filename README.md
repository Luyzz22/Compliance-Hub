# Compliance-Hub

Compliance-Hub ist ein schlanker Backend-Baustein für EU AI Act- und DSGVO-konforme KI-Systeminventare im DACH-Mittelstand.  
Technischer Fokus: AI-System-Registry, E-Invoicing-Compliance und Governance-Policies auf Basis von FastAPI und PostgreSQL/SQLite.

## Architekturüberblick

- **Framework:** FastAPI (Python)
- **Persistenz:** SQLAlchemy 2.x (PostgreSQL oder SQLite)
- **Domain-Layer:** Pydantic-Models (`app/ai_system_models.py`, `app/models.py`)
- **DB-Layer:** SQLAlchemy Declarative Models (`app/models_db.py`)
- **Repositories:** Kapselung der Persistenzlogik (`app/repositories/ai_systems.py`)
- **Security:** API-Key-Auth + Mandantenheader (`app/security.py`)
- **Compliance-Engine:** Dokumentbasierte Regel-Engine (`app/services/compliance_engine.py`)
- **Tests:** Pytest (`tests/`)

Die Anwendung ist so strukturiert, dass sie sich sowohl als eigenständiger Service als auch als Subservice (z.B. in SBS Nexus) betreiben lässt. [page:155][web:142]

## Features

### 1. AI-System-Inventar (EU AI Act Ready)

- Registrierung von KI-Systemen inkl.:
  - Name, Beschreibung, Business Unit
  - Risikoniveau (`AISystemRiskLevel`)
  - AI-Act-Kategorie (`AIActCategory`)
  - DPIA-Pflicht (GDPR)
  - Verantwortliche Kontakt-E-Mail
  - Status (`draft`, `active`, …)
- Multi-Tenant-Unterstützung über `tenant_id`
- Repository-Pattern mit sauberen Mapping-Methoden zwischen DB und Domain-Modell. [page:155][web:160]

### 2. API-Key-Security und Mandanten-Trennung

- Header-basierte Security:
  - `x-api-key` für Authentifizierung
  - `x-tenant-id` für Mandantenkontext
- API-Keys werden über `COMPLIANCEHUB_API_KEYS` aus der Umgebung geladen.
- Zentrale Security-Dependency `get_api_key_and_tenant` prüft:
  - Header-Präsenz
  - Gültigkeit des API-Keys
  - Gibt den gültigen `tenant_id` zurück. [page:155][web:203]

### 3. Compliance-Engine für Dokument-Intake

- Endpoint für Dokumenteingang mit Domänenmodell `DocumentIngestRequest`.
- Regeln u.a. für:
  - E-Invoicing (EN 16931, XRechnung/ZUGFeRD)
  - GDPR/DSGVO (personenbezogene Daten, DPIA-Indikatoren)
  - GoBD-konforme Verarbeitung
  - AI-Governance-Hinweise
- Rückgabe einer strukturierten Liste von `ComplianceAction` inkl. Audit-Hash. [page:140][web:45]

## Endpunkte

### Health

```http
GET /api/v1/health
Statusinformationen zur Anwendung.

AI-Systeme
text
GET  /api/v1/ai-systems
POST /api/v1/ai-systems
Headers (alle Requests):

x-api-key: <valid-api-key>

x-tenant-id: <tenant-id>

Beispiel: AI-System anlegen

bash
curl -X POST "http://localhost:8000/api/v1/ai-systems" \
  -H "Content-Type: application/json" \
  -H "x-api-key: local-dev-key" \
  -H "x-tenant-id: org_sbs_001" \
  -d '{
    "id": "aisys_invoice_classifier_v1",
    "name": "KI-Rechnungsklassifizierung",
    "description": "Automatische Klassifizierung von Eingangsrechnungen.",
    "business_unit": "Finance",
    "risk_level": "high",
    "ai_act_category": "high_risk",
    "gdpr_dpia_required": true,
    "owner_email": "compliance@example.com"
  }'
Beispiel: AI-Systeme eines Tenants listen

bash
curl "http://localhost:8000/api/v1/ai-systems" \
  -H "x-api-key: local-dev-key" \
  -H "x-tenant-id: org_sbs_001"
Document Intake
text
POST /api/v1/documents/intake
Payload u.a.:

tenant_id, document_id, document_type

supplier_name, supplier_country

contains_personal_data, e_invoice_format, xml_valid_en16931, amount_eur

Antwort:

accepted, timestamp_utc, actions[], audit_hash

Lokale Entwicklung
Voraussetzungen
Python 3.11+

Virtualenv (empfohlen)

PostgreSQL oder SQLite (für lokale Entwicklung reicht SQLite)

Setup
bash
git clone https://github.com/<ORG>/Compliance-Hub.git
cd Compliance-Hub

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
Konfiguration
Umgebungsvariablen:

COMPLIANCEHUB_DB_URL
z.B.:

sqlite+pysqlite:///./compliancehub.db (Default)

postgresql+psycopg2://user:pass@host:5432/dbname

COMPLIANCEHUB_API_KEYS
z.B.:

bash
export COMPLIANCEHUB_DB_URL="sqlite+pysqlite:///./compliancehub.db"
export COMPLIANCEHUB_API_KEYS="local-dev-key"
Server starten
bash
source .venv/bin/activate
uvicorn app.main:app --reload
Swagger-UI:

http://localhost:8000/docs [web:157]

Tests
Die Test-Suite deckt Repository-, API- und Security-Verhalten ab.

bash
source .venv/bin/activate
pytest
Repository-Tests: tests/test_ai_systems_repository.py

Security/API-Key-Tests: tests/test_security_api_key.py

Weitere Tests: tests/test_compliance_engine.py, tests/test_api.py [page:155][web:168]

Nächste Schritte
Geplante Erweiterungen:

JWT/OAuth2-basierte Auth mit Rollen (Compliance Officer, Viewer, Admin).

Audit-Logging für alle kritischen Aktionen (Create/Update von AI-Systemen, Document Intake).

Erweiterte AI-Act-spezifische Felder (Annex-III-Referenzen, Konformitätsbewertungsstatus).

UI-/Portal-Integration (z.B. SBS Nexus) für Self-Service-Konfiguration.
