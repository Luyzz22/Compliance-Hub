# Resolve PR conflicts for ComplianceHub (#6)

Diese Anleitung löst den Status **"This branch has conflicts that must be resolved"**.

## Betroffene Dateien

- `.github/workflows/ci.yml`
- `README.md`
- `app/main.py`
- `app/models.py`
- `app/services/compliance_engine.py`
- `docs/architecture.md`
- `docs/compliance-mapping.md`
- `pyproject.toml`
- `tests/test_api.py`

## Sichere CLI-Vorgehensweise

```bash
# 1) In dein lokales Repo
cd ~/Compliance-Hub

# 2) Aktuelle Stände holen
git fetch origin

# 3) Auf den PR-Branch wechseln
git checkout codex/build-sbs-nexus-compliancehub-project-70f52c

# 4) main in den PR-Branch mergen (dadurch entstehen lokal Konflikte)
git merge origin/main
```

Jetzt Konflikte auflösen, Datei für Datei.

### Empfohlene inhaltliche Priorität

1. **CI/Fixes aus main behalten** (`.github/workflows/ci.yml`, `pyproject.toml`)
2. **Neue Fachlogik aus PR behalten** (`app/services/compliance_engine.py`, `app/models.py`, `app/main.py`)
3. **Tests aktualisieren** (`tests/test_api.py`) passend zur finalen Fachlogik
4. **Docs konsolidieren** (`README.md`, `docs/*.md`)

## Konflikte auflösen & prüfen

```bash
# Zeigt alle Dateien mit Konfliktmarkern
git diff --name-only --diff-filter=U

# Nach manueller Auflösung:
git add .github/workflows/ci.yml README.md app/main.py app/models.py \
  app/services/compliance_engine.py docs/architecture.md docs/compliance-mapping.md \
  pyproject.toml tests/test_api.py

# Qualitätschecks
ruff check .
pytest
```

## Abschluss

```bash
git commit -m "merge: resolve conflicts with main for PR #6"
git push origin codex/build-sbs-nexus-compliancehub-project-70f52c
```

Danach aktualisiert sich der PR-Status auf GitHub.
