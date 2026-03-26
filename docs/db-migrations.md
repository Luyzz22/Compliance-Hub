# Datenbank-Migrationen (Governance, ohne Alembic)

## Warum das existiert

SQLAlchemy **`Base.metadata.create_all()`** legt fehlende Tabellen an, führt aber **kein** `ALTER TABLE` auf bestehenden Tabellen aus. Wird am ORM eine neue Spalte ergänzt (z. B. `TenantDB.kritis_sector`), schlagen **Upgrades** mit bestehender Datei/DB mit Fehlern wie *no such column* fehl — wie bei PR #111, bevor die idempotente Migration nachgezogen wurde.

Dieses Repo nutzt daher:

1. **Explizite additive Migrationen** unter `app/db_migrations/migrations/` (Python-Module, sortierbare `MIGRATION_ID`).
2. **`schema_migrations`-Ledger** — Tabelle mit angewendeten Ids (schneller Skip + Audit).
3. **CI-Reflexionstest** — nach `create_all` + `run_all_db_migrations` müssen alle ORM-Spalten in der DB existieren (`tests/test_db_schema_alignment.py`).

## Konventionen

| Element | Regel |
|--------|--------|
| Modulpfad | `app/db_migrations/migrations/m{YYYYMMDD}_{kurzbeschreibung}.py` — führendes **`m`**, weil Python-Modulnamen nicht mit Ziffern beginnen dürfen. |
| Öffentliche Id | `MIGRATION_ID = "20260326_add_tenants_kritis_sector"` — **lexikographisch sortierbar** bei Präfix `YYYYMMDD`. |
| Anzeigename | Optional `DISPLAY_NAME` für die Ledger-Spalte `name`. |
| Idempotenz | `apply(engine) -> bool`: `True` nur wenn **dieser Lauf** DDL ausgeführt hat; vorher mit `inspect` / Hilfen aus `app/db_migrations/util.py` prüfen. |
| Bereits erfüllt | Optional `satisfied(engine) -> bool`: z. B. Spalte existiert schon nach frischem `create_all` — Runner trägt die Id **ohne** DDL ins Ledger ein (*backfill*). |
| Reihenfolge | `app/db_migrations/discovery.py` lädt alle Module im Paket `migrations` und sortiert nach `MIGRATION_ID`. |

Referenzordner `scripts/migrations/` ist dokumentarisch beschrieben (`scripts/migrations/README.md`); die ausführbare Quelle bleibt **`app/db_migrations/`** (installierbares Paket).

## `schema_migrations`-Tabelle

| Spalte | Bedeutung |
|--------|-----------|
| `id` | Primärschlüssel = `MIGRATION_ID` |
| `name` | Kurzname (`DISPLAY_NAME` oder Id) |
| `applied_at` | UTC-Zeitstempel (ISO-8601-String, SQLite-kompatibel) |

- Ist eine Id bereits eingetragen, wird die Migration **übersprungen** (Log: `migration skipped (ledger)`).
- Fehlt der Eintrag, aber `satisfied()` ist wahr, wird nur das Ledger nachgezogen.
- **`apply()`** bleibt weiterhin idempotent: bei fehlendem Ledger vertraut die Pipeline nicht blind — DDL wird nur ausgeführt, wenn die Vorprüfung greift.

## Wann brauche ich eine Migration?

Immer, wenn sich das **physische** Schema unterscheidet von dem, was eine **bestehende** Produktions-/Pilot-DB bereits hat:

- neue oder umbenannte **Spalten** (additive Migration; Drops separat und vorsichtig),
- neue **Tabellen**, die nicht durch ein kontrolliertes `create_all` in eurer Umgebung entstehen,
- Index-/Constraint-Änderungen (explizites DDL).

Reines Ändern von Python-Logik ohne Schema: **keine** Migration.

### Warnbeispiel `kritis_sector`

ORM-Feld `TenantDB.kritis_sector` ohne `ALTER TABLE` → alte SQLite/Postgres-Dateien brechen. Lösung: Modul `m20260326_add_tenants_kritis_sector.py` + Ledger + Tests.

## Neuen Migrationsschritt anlegen

1. Datei **`app/db_migrations/migrations/mYYYYMMDD_was_geaendert_wird.py`** anlegen.
2. Konstanten und Funktionen:

```python
"""Kurzbeschreibung (ein Satz)."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db_migrations.util import column_exists, table_exists

logger = logging.getLogger(__name__)

MIGRATION_ID = "20260326_add_example_flag"
DISPLAY_NAME = "add_example_flag"


def satisfied(engine: Engine) -> bool:
    return column_exists(engine, "tenants", "example_flag")


def apply(engine: Engine) -> bool:
    if not table_exists(engine, "tenants"):
        return False
    if satisfied(engine):
        return False
    stmt = text("ALTER TABLE tenants ADD COLUMN example_flag BOOLEAN NOT NULL DEFAULT 0")
    with engine.begin() as conn:
        conn.execute(stmt)
    logger.info("db_migration applied: %s", MIGRATION_ID)
    return True
```

3. **Tests**: Legacy-Schema ohne Spalte → `apply` / `run_all_db_migrations` → ORM-Insert; optional `list_orm_columns_missing_in_db(..., require_all_tables=False)` auf der Mini-DB.
4. **`docs/db-migrations.md`**: Zeile in der Migrationstabelle (unten) ergänzen.

Kein manuelles Registrieren in einer zentralen Liste nötig — **Discovery** zieht alle Module im Paket.

## Lokal ausführen

```bash
python scripts/migrate_all.py        # normal
python scripts/migrate_all.py -v     # Debug-Logs
```

Umgebung wie die API: **`COMPLIANCEHUB_DB_URL`** (siehe `app/db.py`).

Die **API** ruft `run_all_db_migrations(engine)` im Lifespan nach `create_all` auf — Pilot/Prod können sich darauf verlassen oder das Skript im Deploy **vor** dem Rollout laufen lassen.

Historischer Einzeleinstieg (nur KRITIS-Spalte):

```bash
python scripts/migrate_20260326_add_tenants_kritis_sector.py
```

## CI / Qualitätssicherung

| Check | Ort |
|-------|-----|
| Volle DB deckt ORM ab | `tests/test_db_schema_alignment.py` (nach Session-`create_all` + `run_all_db_migrations` in `conftest.py`) |
| Legacy-Upgrade KRITIS | `tests/test_db_migrations_kritis_sector.py` |

`conftest.py` setzt `DROP TABLE IF EXISTS schema_migrations` vor `drop_all`, damit die Test-Datei nicht mit altem Ledger „klebt“.

## Registrierte Migrationen

| `MIGRATION_ID` | Zweck |
|----------------|--------|
| `20260326_add_tenants_kritis_sector` | `tenants.kritis_sector` VARCHAR(64) NULL |

## Später: Alembic?

| Minimal-Skripte (aktuell) | Alembic |
|---------------------------|---------|
| Wenig Boilerplate, sofort lesbar | Revisionen, Autogenerate, Up/Down |
| Manuell disziplinieren (Reviews, CI) | Standard-Ökosystem, Branching von DB-Revisionen |
| Gut für kleine Teams / Pilot | Sinnvoll bei vielen Umgebungen und parallelen Features |

**Austauschbarkeit:** Migrationen sind kleine Module mit `apply(engine)`; ein späterer Alembic-Adapter könnte dieselben Schritte aus `upgrade()`-Skripten aufrufen oder durch `op.add_column` ersetzen, ohne die **Idempotenz-Disziplin** (inspect vor DDL) aufzugeben.
