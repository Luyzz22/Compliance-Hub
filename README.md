# SBS-Nexus ComplianceHub

Enterprise-SaaS-Prototyp für den DACH-Mittelstand: E-Rechnung, DSGVO und GoBD in einer integrierten Compliance-Maschine.

### EU AI Act Risk Classification & Gap Analysis

Dieses Modul klassifiziert registrierte KI-Systeme entlang der EU-AI-Act-Logik und erzeugt ein mandantenfähiges Gap-Analyse-Dashboard [file:1238].

- **Risk Classification Engine**  
  - Decision-Tree-Logik gemäß EU AI Act Art. 6: `prohibited → high_risk → limited_risk → minimal_risk` [file:1238].  
  - Berücksichtigung von Annex I/III–Kategorien, kritikalitätsbasierten Attributen und DPIA-Pflicht (GDPR) pro AI-System [file:1237].  
  - Ergebnisse werden pro Tenant persistent gespeichert und über einen API-Endpoint für Dashboards bereitgestellt [file:1237].

- **Policy Engine & Violations**  
  - Default-Policy „AI Compliance Policy“ mit Rules wie  
    - „High risk requires DPIA“  
    - „High criticality requires valid owner email“ [file:1238].  
  - Violations werden pro Tenant erzeugt, versioniert und über Endpoints für GRC-Workflows abrufbar gemacht [file:1237].

- **Gap Analysis Dashboard**  
  - Aggregationen pro Tenant: Anzahl Systeme nach Risk Level und AI-Act-Kategorie (Annex I/III) [file:1237].  
  - Grundlage für Board-taugige Reports (NIS2/ISO‑42001/ISO‑27001 Alignment) im ComplianceHub [file:1238].

- **Audit Events & Evidence**  
  - Alle Policy-Evaluations und AI-System-Lifecycle-Änderungen werden als Audit Events mit Metadaten (Actor, Action, Entity, Violations Count) geloggt [file:1237].  
  - Architektur ist vorbereitet für spätere NIS2/ISO‑27001 Evidence Flushes in externe Systeme (z.B. DMS, SIEM) [file:1238].
    

## Was jetzt besser funktioniert

- **Offline-fähiger Core** ohne Drittanbieter-Zwang (Regel-Engine + Modelle laufen mit Standardbibliothek).
- **API als optionales Add-on** (`.[api]`) für FastAPI-Deployments.
- **Tests laufen auch in restriktiven Umgebungen** ohne Paket-Downloads.

## Quickstart (Core)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
pytest
```

## API starten (optional)

```bash
pip install -e '.[api]'
uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000` for the landing page.

## API Endpoints

- `GET /api/v1/health`
- `POST /api/v1/documents/intake`
- `GET /api/v1/compliance/score/{tenant_id}`

## Architektur-Dokumente

- `docs/architecture.md`
- `docs/product-strategy.md`
- `docs/compliance-mapping.md`

## Warum auf GitHub evtl. nichts sichtbar ist

Wenn `git remote -v` leer ist, existiert lokal **kein** verknüpftes GitHub-Repository.
Dann werden Commits nur lokal gespeichert und nicht automatisch veröffentlicht.
Siehe: `docs/github-publish.md`.
