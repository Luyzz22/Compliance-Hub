# Wave 50 – Enterprise-/SAP-ERP-Evidence-Hooks

Interne Advisor-Funktion: **Metadaten-Hooks** zur Darstellung möglicher Evidenz-Anknüpfungspunkte an Systemlandschaften (SAP, DATEV, Dynamics, generisches ERP). **Kein ETL, keine Live-Integration**, keine automatische Rechtsbewertung.

## Datenmodell (gespeicherte Hooks)

Pfad: `frontend/data/advisor-evidence-hooks.json` (Next.js-`process.cwd()` = `frontend`) bzw. `ADVISOR_EVIDENCE_HOOKS_PATH` oder unter Vercel `/tmp/compliancehub-advisor-evidence-hooks.json`.

| Feld | Beschreibung |
|------|----------------|
| `hook_id` | Eindeutige ID (z. B. UUID oder sprechender Schlüssel) |
| `tenant_id` | Mandanten-ID (`client_id`) |
| `source_system_type` | Siehe unten |
| `source_label` | Freitext-Anzeige (z. B. „S/4HANA Produktiv“) |
| `evidence_domain` | Siehe unten |
| `connection_status` | `not_connected` · `planned` · `connected` · `error` |
| `last_sync_at` | Optional, ISO-8601 (letzte bekannte Synchronisation/Abgleich) |
| `note` | Optional, Beraterhinweis |

## Unterstützte `source_system_type`

- `sap_s4hana` – SAP S/4HANA (Industrie-Mittelstand / Enterprise)
- `sap_btp` – SAP BTP als Integrations-/Evidenzpfad
- `datev` – DATEV-Kanal (Kanzlei)
- `ms_dynamics` – Microsoft Dynamics / Business Central (breitere ERP-Fit)
- `generic_erp` – Sonstiges ERP, bewusst unspezifisch

## `evidence_domain`

- `invoice` – Belege, Rechnungen, E-Rechnung/GoBD-Kontext
- `access` – Zugriffe, Berechtigungen (NIS2, ISO 27001)
- `approval` – Freigaben, Vier-Augen
- `vendor` – Lieferanten, AV-Verträge
- `ai_system_inventory` – KI-Inventar / Register
- `policy_artifact` – Policies, Arbeitsanweisungen

## Mapping Domäne → Compliance-Sicht (explizit)

Die Zuordnung ist im Code als `evidenceDomainComplianceRelevanceDe` hinterlegt (kurz):

| Domäne | Relevanz (Auszug) |
|--------|-------------------|
| `invoice` | DSGVO (Kontext), GoBD, EN 16931 |
| `access` | NIS2/KRITIS-Dach, ISO 27001, DSGVO Art. 32 |
| `approval` | GoBD/Interne Kontrolle, ISO 27001/42001, NIS2 |
| `vendor` | DSGVO AV, NIS2 Lieferkette, ISO 27001 |
| `ai_system_inventory` | EU AI Act, ISO 42001, NIS2 (Kontext) |
| `policy_artifact` | ISO 42001/27001, EU AI Act (Doku), DSGVO |

## Synthetische Hooks (ohne Store-Eintrag)

Aus dem **Kanzlei-Portfolio** werden automatisch ergänzt:

- **DATEV / `invoice`:** aus `last_datev_bundle_export_at` und Export-Kadenz (`any_export_max_age_days`).
- **SAP S/4HANA-Platzhalter / `invoice`:** wenn kein gespeicherter SAP- oder BTP-Hook für den Mandanten existiert – sichtbar als Enterprise-Readiness-Lücke, nicht als Produktanspruch.

## API

`GET /api/internal/advisor/evidence-hooks` (Lead-Admin-Auth wie andere Advisor-Routen)

- Antwort: `evidence_hooks` (Portfolio-DTO inkl. `summary`, `mandanten`, `top_gaps`, `markdown_de`)
- Query `markdown=0`: `markdown_de` im Objekt leer, `markdown_de` top-level `null` (schlankeres JSON)

## Berater-Wortlaut (Empfehlung)

- Betonen: **Steuerung und Transparenz**, keine „Anbindung fertig“.
- **DATEV** für Kanzlei und steuerliche Evidenz; **SAP/ERP** für Mittelstand/Enterprise-Belegflüsse.
- Upsell: „Evidenz aus der echten Landschaft kann die Nachweisfähigkeit stärken – nächster Schritt wäre Klärung der technischen Roadmap (z. B. BTP), nicht sofort Vollintegration.“

## Grenzen

- Nur Metadaten und Heuristiken; **keine** direkte SAP-/DATEV-API-Anbindung in dieser Wave.
- Keine Mandantenfähigkeit über RLS in diesem JSON-Store – Datei ist **Lead-Admin-/Installationsweit**; tenant_id pro Hook bleibt Pflicht für Zuordnung.

## Ausblick (SAP BTP / S/4HANA)

- Phase 1 (diese Wave): Darstellung, KPIs im Cockpit, Reports/Partnerpaket.
- Später: OAuth/API über BTP, ausgewählte Entitäten (z. B. Freigaben, Schnittstellen-Logs), immer mit explizitem Mandanten- und Einwilligungskontext; Weiterführung siehe Produkt-Roadmap GRC/ERP.

## Verwandte Doku

- `docs/advisors/wave51-board-ready-evidence-pack.md` (Abschnitt D – Evidence Touchpoints)
- `docs/advisors/wave42-kanzlei-monatsreport.md` (Abschnitt 10)
- `docs/advisors/wave44-partner-review-package.md` (Teil J)
- `docs/advisors/wave49-cross-regulation-matrix.md`
- `docs/advisors/wave39-kanzlei-portfolio-cockpit.md`
