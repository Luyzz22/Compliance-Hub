# Migrations (Referenz)

Die **ausführbare** Logik liegt unter Python-Paket:

`app/db_migrations/migrations/m{YYYYMMDD}_{snake_case}.py`

Dateiname **muss** mit `m` beginnen (gültiger Modulname). Die öffentliche, sortierbare Id steht im Modul als `MIGRATION_ID` (z. B. `20260326_add_tenants_kritis_sector`).

**Template (nur Kopieren, nicht von Discovery geladen):** `app/db_migrations/migrations/_template_example.py` → Konstante `MIGRATION_TEMPLATE`.

Dieses Verzeichnis ist die **dokumentierte Spiegelung** des Namensschemas; du kannst hier Release-Notes oder Checklisten ablegen. Einstieg für Läufe:

```bash
python scripts/migrate_all.py
```

Siehe `docs/db-migrations.md`.
