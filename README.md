# SBS-Nexus ComplianceHub

Enterprise-SaaS-Prototyp für den DACH-Mittelstand: E-Rechnung, DSGVO und GoBD in einer integrierten Compliance-Maschine.

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
