# Datenbank-Migrationen (minimal, ohne Alembic)

## Kontext

Neue Spalten am SQLAlchemy-ORM (`app/models_db.py`) werden von **`Base.metadata.create_all()`** nur berücksichtigt, wenn die Tabelle **neu** angelegt wird. Bestehende Installationen (Pilot, Staging, Produktion) bekommen **kein** automatisches `ALTER TABLE`.

Dafür gibt es **additive, idempotente** Migrationen in `app/db_migrations.py`, die:

- fehlende Spalten per `ALTER TABLE` ergänzen,
- ohne Datenänderung auskommen,
- mehrfach ausgeführt werden dürfen (No-op, wenn die Spalte schon existiert).

## Aktuelle Migrationen

| Id | Änderung |
|----|----------|
| `20260326_add_tenants_kritis_sector` | `tenants.kritis_sector` – `VARCHAR(64)`, **NULL** (optional; „nicht gesetzt“ = kein KRITIS-Sektor in den Stammdaten) |

## Wann läuft was?

1. **API-Start (uvicorn):** In `app.main.lifespan` wird nach `create_all` immer `run_all_db_migrations(engine)` aufgerufen. Bestehende SQLite-/Postgres-Dateien erhalten fehlende Spalten beim nächsten Start.
2. **Manuell / Deploy-Skript:** Gleiche Logik ohne Server:

   ```bash
   python scripts/migrate_all.py
   ```

   Verbindung wie die API: Umgebungsvariable **`COMPLIANCEHUB_DB_URL`** (Fallback siehe `app/db.py`).

3. **Historischer Einzeleinstieg** (enthält nur die KRITIS-Spalte):

   ```bash
   python scripts/migrate_20260326_add_tenants_kritis_sector.py
   ```

## CI

Die Regression liegt in **`tests/test_db_migrations_kritis_sector.py`**: Legacy-Schema ohne `kritis_sector` → Migration → Insert/Lesen über `TenantDB`.

## Neue Migrationen hinzufügen

1. In `app/db_migrations.py` eine Funktion `migrate_*` implementieren (Existenzprüfung per `sqlalchemy.inspect`, dann `ALTER` in `engine.begin()`).
2. In `run_all_db_migrations` registrieren und eine stabile Id zurückgeben.
3. Test mit „altem“ Schema ergänzen.
4. Diese Datei und ggf. domänenspezifische Docs aktualisieren.

Später kann dieselbe Liste in **Alembic** überführt werden; bis dahin bleibt das Modell bewusst klein und explizit.
