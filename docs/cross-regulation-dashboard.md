# Cross-Regulation Dashboard („Map once, comply many“)

Das **Cross-Regulation Dashboard** (`/tenant/cross-regulation-dashboard`) bündelt einen **globalen Anforderungskatalog** (mehrere Regelwerke) mit **mandantenspezifischen Controls** und zeigt **Coverage und Lücken** je Framework.

## Datenmodell (Kurz)

| Tabelle | Zweck |
|--------|--------|
| `compliance_frameworks` | Stammdaten: `eu_ai_act`, `iso_42001`, `iso_27001`, `iso_27701`, `nis2`, `dsgvo` |
| `compliance_requirements` | Pflichten je Framework (Code, Titel, Typ, Kritikalität) |
| `compliance_requirement_relations` | Crosswalk zwischen Pflichten verschiedener Frameworks |
| `compliance_controls` | Tenant-Controls (Name, Typ, Owner-Rolle, Status) |
| `compliance_requirement_control_links` | Verknüpfung Pflicht ↔ Control inkl. `coverage_level` (`full` / `partial` / `planned`) |
| `compliance_control_ai_systems` | Optional: Control → KI-System |
| `compliance_control_policies` | Optional: Control → Policy |
| `compliance_control_actions` | Optional: Control → Governance-Action |

Beim Start der API wird der **globale Katalog** idempotent geseedet (`ensure_cross_regulation_catalog_seeded`), sofern noch keine Frameworks existieren.

## Coverage-Logik

- Eine Pflicht gilt als **abgedeckt**, wenn mindestens ein Link mit `coverage_level` **`full`** oder **`partial`** existiert.
- **`planned`** zählt für die Kennzahl „covered“ nicht (bleibt fachlich Lücke / Planung).
- `coverage_percent` je Framework: `covered_requirements / total_requirements` (0–100 %).

## API (Feature-Flag)

Schalter: **`COMPLIANCEHUB_FEATURE_CROSS_REGULATION_DASHBOARD`** (Frontend: **`NEXT_PUBLIC_FEATURE_CROSS_REGULATION_DASHBOARD`**). Aus = **403** auf die Endpunkte.

Alle Pfade verlangen **`x-tenant-id`** / API-Key; **`tenant_id` im Pfad** muss mit dem authentifizierten Mandanten übereinstimmen.

- `GET /api/v1/tenants/{tenant_id}/compliance/cross-regulation/summary`
- `GET /api/v1/tenants/{tenant_id}/compliance/frameworks`
- `GET /api/v1/tenants/{tenant_id}/compliance/regulatory-requirements?framework=eu_ai_act`
- `GET /api/v1/tenants/{tenant_id}/compliance/regulatory-controls`
- `GET /api/v1/tenants/{tenant_id}/compliance/regulatory-requirements/{id}/controls`
- `GET /api/v1/tenants/{tenant_id}/ai-systems/{ai_system_id}/regulatory-context`

## Beispiel-Flow

1. **Control anlegen** (aktuell über DB/Tooling): z. B. „AI-Risikomanagement-Prozess“ für `tenant_id` T.
2. **Links setzen**: `compliance_requirement_control_links` von diesem Control zu **EU AI Act Art. 9**, **ISO 42001 6.1**, **NIS2 Art. 21(2)(b)** mit `full` oder `partial`.
3. **Dashboard öffnen**: Unter EU AI Act, ISO 42001 und NIS2 steigt die Coverage; im Drilldown sieht man ein Control mit mehreren Pflichten (**ein Control, viele Regelwerke**).
4. Optional **KI-System verknüpfen** (`compliance_control_ai_systems`): System-Detail zeigt die zugehörigen Pflichten und Link zum Dashboard.

## UI-Einstiege

- Tenant-Navigation: **Cross-Regulation**
- **Compliance-Übersicht**: Karte „Cross-Regulation Overview“
- **AI Governance Playbook**: Abschnitt „Frameworks konsolidieren“
- **KI-System-Detail**: Hinweis- bzw. Listenblock, wenn Controls mit System verknüpft sind

Siehe auch `docs/e2e-demo-flow.md` (Cross-Regulation im Demo-Kontext).
