# SBS-Nexus ComplianceHub

Enterprise-SaaS-Prototyp für den DACH-Mittelstand: E-Rechnung, DSGVO und GoBD
in einer integrierten Compliance-Maschine.

## Was jetzt besser funktioniert

- **Offline-fähiger Core** ohne Drittanbieter-Zwang (Regel-Engine + Modelle laufen mit Standardbibliothek).
- **API als optionales Add-on** (`.[api]`) für FastAPI-Deployments.
- **Tests laufen auch in restriktiven Umgebungen** ohne Paket-Downloads.

## Voraussetzungen

- Python >= 3.11
- Optional: `uvicorn` über `.[api]` für die API

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

## API nutzen (MVP)

Health:

```bash
curl http://127.0.0.1:8000/api/v1/health
```

Dokumenten-Intake (Platzhalter):

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents/intake \\
  -H 'Content-Type: application/json' \\
  -d '{
    "tenant_id": "tenant-001",
    "document_id": "doc-001",
    "document_type": "invoice",
    "supplier_name": "Supplier GmbH",
    "supplier_country": "DE",
    "contains_personal_data": true,
    "e_invoice_format": "xrechnung",
    "xml_valid_en16931": true,
    "amount_eur": 199.0
  }'
```

## API Endpoints

- `GET /api/v1/health`
- `POST /api/v1/documents/intake`

## Entwicklung & Qualität

```bash
pip install -e '.[dev]'
pytest
ruff check .
```

## Projektstruktur

- `app/`: Core-Modelle, Services, optionale API
- `tests/`: Unit- und API-Tests (offline-fähig)
- `docs/`: Architektur, Compliance-Mapping, Board Memo

## Architektur-Dokumente

- `docs/architecture.md`
- `docs/compliance-mapping.md`
- `docs/board_memo.md`
