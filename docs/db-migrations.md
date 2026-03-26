# Datenbank-Migrationen (Governance, ohne Alembic)

## Warum das existiert

SQLAlchemy **`Base.metadata.create_all()`** legt fehlende Tabellen an, führt aber **kein** `ALTER TABLE` auf bestehenden Tabellen aus. Wird am ORM eine neue Spalte ergänzt (z. B. `TenantDB.kritis_sector`), schlagen **Upgrades** mit bestehender Datei/DB mit Fehlern wie *no such column* fehl — wie bei PR #111, bevor die idempotente Migration nachgezogen wurde.

Dieses Repo nutzt daher:

1. **Explizite additive Migrationen** unter `app/db_migrations/migrations/` (Python-Module, sortierbare `MIGRATION_ID`).
2. **`schema_migrations`-Ledger** (optional) — Tabelle mit angewendeten Ids (schneller Skip + Audit), sofern die DB-Rolle `CREATE TABLE` ausführen darf.
3. **CI-Reflexionstest** — nach `create_all` + `run_all_db_migrations` müssen alle ORM-Spalten in der DB existieren (`tests/test_db_schema_alignment.py` → `list_orm_columns_missing_in_db`).

## Konventionen

| Element | Regel |
|--------|--------|
| Modulpfad | `app/db_migrations/migrations/m{YYYYMMDD}_{kurzbeschreibung}.py` — führendes **`m`**, weil Python-Modulnamen nicht mit Ziffern beginnen dürfen. |
| Öffentliche Id | `MIGRATION_ID = "20260327_add_foo"` — **lexikographisch sortierbar** bei Präfix `YYYYMMDD`. |
| Anzeigename | Optional `DISPLAY_NAME` für die Ledger-Spalte `name`. |
| Idempotenz | `apply(engine) -> bool`: `True` nur wenn **dieser Lauf** DDL ausgeführt hat; vorher mit `inspect` / `app/db_migrations/util.py` prüfen. |
| Bereits erfüllt | `satisfied(engine) -> bool`: z. B. Spalte existiert schon nach frischem `create_all` — Runner trägt die Id **ohne** DDL ins Ledger ein (*backfill*). |
| Reihenfolge | `discovery.py` lädt alle Module im Paket `migrations`, **ohne** führenden Unterstrich im Dateinamen, und sortiert nach `MIGRATION_ID`. |
| Template / Doku-Stub | `_template_example.py` wird **nicht** geladen; enthält `MIGRATION_TEMPLATE` zum Kopieren. |

Referenzordner `scripts/migrations/` ist dokumentarisch (`scripts/migrations/README.md`); ausführbare Quelle = **`app/db_migrations/`**.

## Migration template

Datei: **`app/db_migrations/migrations/_template_example.py`**

- Enthält die Konstante **`MIGRATION_TEMPLATE`** (mehrzeiliger String mit dem Standard-Skelett: `MIGRATION_ID`, `DISPLAY_NAME`, `satisfied`, `apply`).
- Wird von der Discovery **ignoriert** (Dateiname beginnt mit `_`).

## Rezept (neue Migration)

1. **`app/db_migrations/migrations/mYYYYMMDD_kurzbeschreibung.py`** anlegen (von `_template_example.MIGRATION_TEMPLATE` kopieren oder `m20260327_add_tenant_ai_governance_setup_notes.py` als Referenz).
2. **`MIGRATION_ID`** / **`apply`** / **`satisfied`** ausfüllen — nur **additive** DDL (kein `DROP`, keine destruktiven `ALTER`).
3. **`app/models_db.py`** (oder anderes ORM-Modul) anpassen, falls neue Spalte/Tabelle.
4. Lokal: **`python scripts/migrate_all.py`** (ggf. `-v`) gegen eine Kopie der Ziel-DB oder frisches SQLite.
5. **`pytest`** — mindestens `tests/test_db_schema_alignment.py` muss grün sein; bei Legacy-Pfaden zusätzlich gezielter Test (siehe `tests/test_db_migrations_*.py`).

### Änderungen an `models_db.py`

Jede **persistent**e Schema-Änderung (Spalte/Tabelle, die in Pilot/Prod vorkommt) **soll** ein Migration-Modul haben, damit bestehende Datenbanken nachziehen können.

Ausnahmen nur mit **kurzer Begründung** im PR (z. B. reines Test-Double, niemals deployed). Ohne Migration droht derselbe Fehler wie bei **`kritis_sector`**: App startet, SQL meldet fehlende Spalte.

## Zwei Betriebsmodi (`run_all_db_migrations`)

| Modus | Voraussetzung | Verhalten |
|--------|----------------|-----------|
| **Ledger** (Standard) | `CREATE TABLE schema_migrations` gelingt | Wie bisher: Ledger lesen/schreiben, `apply()` darf additives DDL ausführen, Backfill wenn `satisfied()`. |
| **Ledgerless** | Kein Recht auf Ledger-Tabelle (Permission / read-only Schema) | **Kein** DDL durch `apply()`, **kein** Lesen/Schreiben des Ledgers. Pro Migration nur `satisfied(engine)`; bei `False` erscheint die Id in `MigrationRunSummary.ledgerless_unsatisfied` und ein **Warning**-Log. API-Start bricht **nicht** nur deshalb ab. |

- Im Ledgerless-Fall sind **DBA oder privilegierte Jobs** für `ALTER TABLE` zuständig (z. B. `python scripts/migrate_all.py` mit Owner-Rolle).
- CI mit voller Test-DB bleibt der Fangnetz-Check: fehlende ORM-Spalten fallen weiterhin durch `test_db_schema_alignment` auf.

## `schema_migrations`-Tabelle

| Spalte | Bedeutung |
|--------|-----------|
| `id` | Primärschlüssel = `MIGRATION_ID` |
| `name` | Kurzname (`DISPLAY_NAME` oder Id) |
| `applied_at` | UTC-Zeitstempel (ISO-8601-String, SQLite-kompatibel) |

- **Anlage ist best-effort:** schlägt `CREATE TABLE` mit typischen Berechtigungs-/Read-only-Fehlern fehl, läuft der Runner im Ledgerless-Modus (siehe oben).
- Ist eine Id bereits eingetragen, wird die Migration **übersprungen** (Log: `migration skipped (ledger)`).
- Fehlt der Eintrag, aber `satisfied()` ist wahr, wird nur das Ledger nachgezogen.
- **`apply()`** bleibt idempotent: bei fehlendem Ledger wird nicht blind vertraut.

## Schema-Abgleich (ORM ↔ DB)

Hilfsfunktion: **`app.db_migrations.schema_alignment.list_orm_columns_missing_in_db`**

- `require_all_tables=True` (Standard): jede ORM-Tabelle muss in der DB existieren; jede ORM-Spalte muss reflektiert werden — **CI**.
- `require_all_tables=False`: nur Tabellen, die bereits existieren, werden spaltenweise geprüft — Legacy-Mini-DBs in Tests.

## Wann brauche ich eine Migration?

Immer, wenn sich das **physische** Schema von dem unterscheidet, was eine **bestehende** DB bereits hat: neue Spalten/Tabellen, relevante Indizes. Reine Python-Logik: keine Migration.

### Warnbeispiel `kritis_sector`

ORM-Feld ohne `ALTER TABLE` auf alten Dateien → Laufzeitfehler. Lösung: Migration `m20260326_add_tenants_kritis_sector.py` + Ledger + Tests.

## Lokal ausführen

```bash
python scripts/migrate_all.py        # normal
python scripts/migrate_all.py -v     # Debug-Logs
```

Umgebung wie die API: **`COMPLIANCEHUB_DB_URL`** (`app/db.py`).

Die **API** ruft `run_all_db_migrations(engine)` im Lifespan nach `create_all` auf.

Historischer Einzeleinstieg (nur KRITIS-Spalte):

```bash
python scripts/migrate_20260326_add_tenants_kritis_sector.py
```

## CI / Qualitätssicherung

| Check | Ort |
|-------|-----|
| Volle DB deckt ORM ab | `tests/test_db_schema_alignment.py` |
| Legacy KRITIS | `tests/test_db_migrations_kritis_sector.py` |
| Discovery + `setup_notes` + Logging | `tests/test_db_migrations_discovery_and_setup_notes.py` |
| Ledger optional (CREATE verweigert) | `tests/test_db_migrations_ledger_optional.py` |

`conftest.py`: `DROP TABLE IF EXISTS schema_migrations` vor `drop_all`, danach `run_all_db_migrations`.

## Registrierte Migrationen

| `MIGRATION_ID` | Zweck |
|----------------|--------|
| `20260326_add_tenants_kritis_sector` | `tenants.kritis_sector` VARCHAR(64) NULL |
| `20260327_add_tenant_ai_governance_setup_notes` | `tenant_ai_governance_setup.setup_notes` TEXT NULL (optional, DevEx-Beispiel) |

## Später: Alembic?

| Minimal-Skripte (aktuell) | Alembic |
|---------------------------|---------|
| Wenig Boilerplate, sofort lesbar | Revisionen, Autogenerate, Up/Down |
| Manuell disziplinieren (Reviews, CI) | Standard-Ökosystem, Branching von DB-Revisionen |
| Gut für kleine Teams / Pilot | Sinnvoll bei vielen Umgebungen und parallelen Features |

**Austauschbarkeit:** Migrationen sind kleine Module mit `apply(engine)`; ein späterer Alembic-Adapter könnte dieselben Schritte aus `upgrade()` aufrufen, ohne die **Inspect-vor-DDL**-Disziplin aufzugeben.
