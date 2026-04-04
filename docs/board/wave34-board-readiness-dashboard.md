# Wave 34 – Board Readiness Dashboard

Interne Executive-Ansicht unter `/admin/board-readiness` (Next.js Admin, `LEAD_ADMIN_SECRET`). Sie bündelt **wenige, nachvollziehbare** Governance-Signale aus den bestehenden FastAPI-Endpunkten – ohne zusammengesetzten „Compliance-Score“.

## Ziele

- Beantwortung: **Wie AI-Act-/ISO-42001-/NIS2-/DSGVO-ready sind wir produktseitig** über die in `data/gtm-product-account-map.json` gemappten Mandanten?
- **Auditierbarkeit:** Jede Teilmetrik nennt die **API-Pfade**, aus denen sie abgeleitet wird; Attention Items enthalten **Workspace-Pfade** und **API-Pfade** für Nachweise.
- **GTM-Bezug:** Segment- und Readiness-Klassen-Rollups knüpfen an **Wave 33** (Product–GTM Bridge) und die gleiche 30-Tage-Fensterlogik wie `/admin/gtm`.

## Governance-Datenmodell (Python)

Strukturelle DTOs (für Vertrag/Dokumentation, zukünftige APIs): `app/board_readiness_models.py` (`BoardReadinessPillarBlock`, `BoardReadinessSubIndicator`, `BoardAttentionItem`, …).

## Indikatoren je Säule

Schwellen (Ampel) sind zentral in `frontend/src/lib/boardReadinessThresholds.ts` definiert:

| Ampel  | Bedingung (Ratio 0–1)      |
|--------|----------------------------|
| Grün   | Ratio ≥ 0,75               |
| Amber  | 0,45 ≤ Ratio < 0,75 oder Ratio nicht berechenbar |
| Rot    | Ratio < 0,45               |

Zusätzlich gelten **harte Rot-Signale** dort, wo ein fachliches Minimum fehlt (z. B. fehlender aktueller Board-Report trotz High-Risk-Systemen).

### EU AI Act

| Key | Bedeutung | Datenquellen |
|-----|-----------|--------------|
| `high_risk_art9_complete_ratio` | Anteil der **klassifizierten High-Risk**-Systeme mit Compliance-Status **Art. 9 (Risikomanagement)** = `completed` | `GET /api/v1/compliance/dashboard` (Filter `risk_level == high_risk`), `GET /api/v1/ai-systems/{id}/compliance` |
| `high_risk_evidence_bundle_ratio` | Anteil High-Risk mit **Art. 11 abgeschlossen** oder **≥ 2 gespeicherte AI-Act-Doc-Sektionen** (`status == saved`) | `.../compliance`, `GET /api/v1/ai-systems/{id}/ai-act-docs` (Feature-Flag; bei Fehler zählt nur Art. 11) |
| `board_report_recency` | Mindestens ein Eintrag in `GET /api/v1/tenants/{tid}/board/ai-compliance-reports` mit `created_at` innerhalb von **90 Tagen** (`BOARD_REPORT_FRESH_DAYS`), sofern der Mandant High-Risk-Systeme hat | Board-Report-Liste |

Portfolio-Säule: **schlechteste** Ampel der drei Teilindikatoren über alle gemappten Mandanten; Teil-Prozente werden **gemittelt** (nur Mandanten mit Wert).

### ISO 42001 (AI-Managementsystem, pragmatisch)

| Key | Bedeutung | Datenquellen |
|-----|-----------|--------------|
| `iso42001_scope_framework` | `active_frameworks` oder `compliance_scopes` enthält ISO-42001-Hinweis (Substring `42001`) | `GET /api/v1/tenants/{tid}/ai-governance-setup` |
| `iso42001_roles` | Mindestens **zwei** nicht-leere Einträge in `governance_roles` | Setup |
| `iso42001_policies` | `policies_published` im Guided Setup | `GET /api/v1/tenants/{tid}/setup-status` |

### NIS2 / KRITIS (operative Mindestsignale)

| Key | Bedeutung | Datenquellen |
|-----|-----------|--------------|
| `nis2_obligations_kpi_seed` | `nis2_kpis_seeded` **oder** `nis2_kritis_kpi_mean_percent > 0` | Setup-Status, `GET /api/v1/ai-governance/compliance/overview` |
| `nis2_contact_roles` | Rolle mit Schlüssel passend zu CISO/DPO/NIS2/Incident/Security/KRITIS und nicht-leerer Kontakt | Setup |
| `nis2_incident_runbook_high_risk` | Anteil High-Risk-Systeme mit `has_incident_runbook` | `GET /api/v1/ai-systems` |

### DSGVO / Aufzeichnungen

| Key | Bedeutung | Datenquellen |
|-----|-----------|--------------|
| `dsgvo_dpia_flag_high_risk` | Anteil High-Risk-Systeme mit `gdpr_dpia_required == true` (Proxy für dokumentierten DSFA-Pfad, konsistent mit EU-AI-Act-Readiness-Heuristik) | AI-Systeme |
| `dsgvo_records_evidence` | `evidence_attached` oder `classification_completed` im Setup-Status | Setup-Status |

## Segment- und Readiness-Klassen-Rollups

- **Segment:** Dominantes Lead-Segment (30 Tage) pro Mandant über `findGtmProductMapEntry` – gleiche Logik wie Wave 33.
- **Readiness-Klasse:** `classifyMappedTenantReadiness` aus `frontend/src/lib/gtmAccountReadiness.ts` (Wave 33) auf Basis von `fetchTenantGovernanceSnapshot` + Pilot-Flag aus der Map.
- **Score-Proxy in Tabellen:** Mittelwert der Mandanten-Pillar-Scores (`eu.score` aus Art.9/Evidenz/Board-Mix; ISO/NIS2/DSGVO aus booleschen Teilscores 0–100).

## Board Attention Items

Kriterien (Auszug):

1. **High-Risk-System** ohne `owner_email`.
2. **High-Risk** ohne abgeschlossenes **Art. 9** (`completed`).
3. **High-Risk** ohne Evidenzbündel (Art. 11 / AI-Act-Docs-Proxy).
4. Mandant mit **High-Risk-Systemen**, aber **kein** Board-Report in den letzten 90 Tagen.
5. **GTM:** Segment mit **≥ 3 qualifizierten** Leads (30 Tage) und **dominanter Readiness-Klasse** `early_pilot` → Portfolio-Hinweis (Nachfrage vs. Governance).

Items sind auf **80 Zeilen** begrenzt; zuerst GTM-Hinweise, dann mandantenspezifische Lücken.

## Beziehung zu `/admin/gtm`

- `GET /api/admin/gtm/summary` liefert `board_readiness_banner` (gesamte Ampel + Kurztext), berechnet mit derselben Pipeline wie das Board-Dashboard.
- Auf `/admin/gtm` verlinkt eine Kachel nach `/admin/board-readiness`.

## Konfiguration

- **Admin-Auth:** `LEAD_ADMIN_SECRET` (wie Lead-Inbox).
- **Backend:** `COMPLIANCEHUB_API_BASE_URL`, `COMPLIANCEHUB_API_KEY` (oder `NEXT_PUBLIC_*` Fallbacks wie bei der GTM-Brücke).
- **Account-Mapping:** `data/gtm-product-account-map.json` bzw. `GTM_PRODUCT_ACCOUNT_MAP_PATH`.

## Interpretation

- **Internes Governance-Steering:** Attention Items priorisieren konkrete Artefakt-Lücken; Säulen-Ampeln zeigen **wo** der Portfolio-Schwerpunkt liegt (EU AI Act vs. ISO vs. NIS2 vs. DSGVO).
- **Board-Vorbereitung:** Vor einem Board-Termin zuerst **rote** EU-AI-Act- und Board-Report-Signale schließen, dann ISO/NIS2-Mindestnachweise (Rollen, Policies, KPI-Saat).

## Implementierungsreferenz

| Teil | Pfad |
|------|------|
| Rohdaten-Fetch | `frontend/src/lib/fetchTenantBoardReadinessRaw.ts` |
| Aggregation | `frontend/src/lib/boardReadinessAggregate.ts` |
| Schwellen | `frontend/src/lib/boardReadinessThresholds.ts` |
| API | `frontend/src/app/api/admin/board-readiness/route.ts` |
| UI | `frontend/src/components/admin/BoardReadinessClient.tsx` |
