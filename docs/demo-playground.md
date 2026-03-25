# Demo-Modus & Playground

ComplianceHub unterstützt **geführte Demos** (Sales, Founder, Berater) und die Vorbereitung eines **read-only Playgrounds** für Website-Leads.

## Aktivierung

### Backend

| Variable | Bedeutung |
|----------|-----------|
| `COMPLIANCEHUB_FEATURE_DEMO_MODE=true` | Server-seitig: u. a. `demo_mode_feature_enabled` in `GET /api/v1/workspace/tenant-meta` |
| `COMPLIANCEHUB_FEATURE_DEMO_SEEDING` | Demo-Seed-API (bestehend) |

### Frontend

| Variable | Bedeutung |
|----------|-----------|
| `NEXT_PUBLIC_FEATURE_DEMO_MODE=true` | Banner, Demo-Guide, kontextuelle Demo-Hinweise |
| `NEXT_PUBLIC_DEMO_WORKSPACE_TENANT_ID` | Optional: bei `?demo=1` wird der Workspace-Mandant per Cookie gesetzt |
| `NEXT_PUBLIC_DEMO_DOCS_URL` | Optional: Link „Mehr zur Demo“ im Banner (Default: Platzhalter-URL) |

### Session / Einstieg

- Aufruf mit **`?demo=1`** (Next.js-Middleware setzt Cookie `ch_demo_mode`).
- Mandanten mit **`is_demo=true`** in der Tabelle `tenants` lösen die Demo-UI aus, sobald `NEXT_PUBLIC_FEATURE_DEMO_MODE` aktiv ist (ohne Query-Parameter).

## Demo-Mandanten anlegen

### CLI (empfohlen)

Voraussetzung: Datenbank erreichbar (`COMPLIANCEHUB_DB_URL`), Kataloge beim App-Start wie in Produktion geseedet.

```bash
# Ein Preset
python scripts/seed_demo_tenant.py --preset mittelstand-ag

# Beide Standard-Demos
python scripts/seed_demo_tenant.py --all-presets

# Ohne neuen API-Key
python scripts/seed_demo_tenant.py --preset grc-consulting --no-api-key
```

Presets:

- **mittelstand-ag** → Template `industrial_sme`, Tenant-ID `demo-mittelstand-ag`
- **grc-consulting** → Template `tax_advisor`, Tenant-ID `demo-grc-consulting`

Der Seed enthält u. a. KI-Systeme (Hochrisiko/NIS2), NIS2-KPIs, AI-KPI-Zeitreihen, Cross-Regulation-Controls mit realistischen Teilabdeckungen, Setup-Wizard-Payload (Schritte 1–5), zwei Board-Reports sowie den bisherigen Kern-Seed (Policies, Maßnahmen, Evidenzen).

### API (bestehend)

`POST /api/v1/demo/tenants/seed` mit Demo-Seed-Key – legt bei fehlendem Eintrag eine **`tenants`-Zeile mit `is_demo=true`** an und führt den gleichen Seed aus.

## Schreibschutz

- **`is_demo=true`** und **`demo_playground=false`**: schreibende HTTP-Methoden für diesen Mandanten werden mit **403** abgewiesen (über Auth-Dependencies).
- **`demo_playground=true`**: Schreiben bleibt möglich (Sandbox-Variante, z. B. für spätere Aufräum-Jobs).

## Demo-Guide (Storyline)

Die App zeigt optional eine **schmale Demo-Guide-Leiste** (FAB + Schrittliste). Empfohlene Reihenfolge (entspricht den Steps im UI):

1. **AI & Compliance Readiness Score** – `/board/kpis`
2. **AI Governance Playbook** – `/tenant/ai-governance-playbook`
3. **Cross-Regulation & Gap-Assist** – `/tenant/cross-regulation-dashboard`
4. **Hochrisiko-KI & KPIs/KRIs** – erstes Hochrisiko-System aus `/tenant/ai-systems`
5. **AI Compliance Board-Report** – `/board/ai-compliance-report`
6. **Berater-Portfolio** – `/advisor`
7. **Setup-Wizard** – `/tenant/ai-governance-setup`

Kontextzeile: **„Demo-Hinweis · Schritt X von 7“** erscheint auf den passenden Routen, wenn die Demo-UI aktiv ist.

## Playground / Leads (Ausblick)

- Sandbox-Mandant mit `is_demo=true` und `demo_playground=true`, regelmäßiges **Reset-Job** (nicht im Kern-Repo beschrieben).
- **LLM-Budget**: für öffentliche Playgrounds Rate-Limits und niedrige Token-Budgets empfohlen (`COMPLIANCEHUB_FEATURE_LLM_*`, Mandanten-Overrides).

## API: Mandanten-Meta

`GET /api/v1/workspace/tenant-meta` (mit `x-api-key`, `x-tenant-id`):

- `is_demo`, `demo_playground`
- `demo_mode_feature_enabled` (Spiegel von `COMPLIANCEHUB_FEATURE_DEMO_MODE`)

## Berater & Sales

- Mandanten mit Demo-Seed zeigen **realistische Lücken** (Cross-Reg, NIS2, Board-Report) ohne echte Kundendaten.
- Berater können im **Advisor-Workspace** Portfolio und Snapshots zeigen; Demo-Mandanten sind in der Regel **read-only**, um Abweichungen während der Präsentation zu vermeiden.

## Datenbank-Spalten `tenants`

- `is_demo` (boolean, default false)
- `demo_playground` (boolean, default false)

Bei bestehenden PostgreSQL-Instanzen ohne Auto-Migrate: Spalten manuell ergänzen (analog zum SQLAlchemy-Modell in `app/models_db.py`).
