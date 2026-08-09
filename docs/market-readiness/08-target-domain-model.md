# 08 – Ziel-Domänenmodell

**Ausgangslage:** 103 Tabellen in `app/models_db.py`. Das Modell ist **breit**, aber in
drei Achsen **flach**:

1. **Organisationsachse:** `Tenant` ist die einzige Organisationseinheit. Es gibt keine
   juristische Person, keine Jurisdiktion, keinen Standort.
2. **Risiko-/Lieferantenachse:** Weder `Risk` noch `Supplier` existieren als Entität.
   Beides ist auf Boolean-Flags an `ai_systems` reduziert.
3. **Datenschutzachse:** Keine einzige Entität bildet Verarbeitungstätigkeit, Zweck,
   Rechtsgrundlage, Datenkategorie, Transfer oder Aufbewahrung ab.

Diese drei Lücken sind der Grund, warum das Produkt heute ein sehr gutes
**KI-Register** ist, aber noch kein **Compliance Operating System**.

---

## 1. Soll-Ist-Abgleich der geforderten Entitäten

| Entität | Status | Bestehende Tabelle | Maßnahme |
|---|---|---|---|
| Tenant | ✅ | `tenants` | Felder ergänzen (§3.1) |
| **Legal Entity** | ❌ | — | Neu (P2-3) |
| **Country / Jurisdiction** | ⚠️ | `tenants.country` (String) | Zu Referenztabelle ausbauen (P2-3) |
| AI System | ✅ | `ai_systems` | Rollen, Version, Lifecycle ergänzen |
| AI Use Case | ⚠️ | `ai_system_inventory_profiles.use_case` (String) | Eigene Entität (P2-4) |
| **AI Provider** | ❌ | `ai_systems.provider_name` (Freitext) | Neu (P2-4) |
| **AI Model** | ❌ | — | Neu (P2-4) |
| Risk Classification | ✅ | `risk_classifications` | Bestätigungsfelder (P1-13) |
| Requirement | ✅ | `compliance_requirements`, `governance_requirements` | Konsolidieren (§5) |
| Control | ✅ | `compliance_controls`, `governance_controls` | Konsolidieren, `control_nature` (P2-2) |
| Evidence | ✅ | `evidence_files`, `governance_control_evidence` | Hash + Klassifizierung (P0-4) |
| Policy | ✅ | `policies`, `rules` | Versionierung ergänzen |
| **Policy Version** | ❌ | — | Neu (§4) |
| Incident | ✅ | `incidents`, `nis2_incidents`, `service_health_incidents` | Konsolidieren (§5) |
| **Incident Timeline** | ⚠️ | Zeitstempel-Spalten | Eigene Event-Tabelle |
| **Notification Draft** | ❌ | — | `regulatory_notifications` (P1-5) |
| Approval | ✅ | `approval_requests` | Auf Board-Billigung erweitern (P1-6) |
| Task | ✅ | `governance_workflow_tasks`, `remediation_actions` | Konsolidieren (§5) |
| **Risk** | ❌ | — | **Neu (P1-11) — Kernlücke** |
| **Risk Treatment** | ❌ | — | **Neu (P1-11)** |
| **Supplier** | ❌ | `ai_systems.has_supplier_risk_register` (Bool) | **Neu (P1-2) — Kernlücke** |
| **Subprocessor** | ❌ | — | Als Rolle auf `suppliers` (P1-2) |
| **Transfer Record** | ❌ | — | **Neu (P1-1)** |
| **TIA** | ❌ | — | **Neu (P1-1)** |
| **DPA / AVV** | ❌ | — | **Neu (P1-1)** |
| **Data Processing Activity** | ❌ | — | **Neu (P1-1) — Kernlücke** |
| **Data Category** | ❌ | — | **Neu (P1-1)** |
| **Retention Rule** | ❌ | — | **Neu (P0-5)** |
| Audit Event | ✅ | `audit_logs` | Retention-Pfad (P0-5), externer Anker (P1-16) |
| Board Report | ✅ | `board_reports` + 4 Satelliten | — |
| **Training / AI Literacy Record** | ❌ | — | **Neu (P1-4)** |
| **Complaint / Review Case** | ❌ | `governance_audit_cases` (anderer Zweck) | Neu (P2) |

**Bilanz: 13 von 33 geforderten Entitäten fehlen vollständig, 4 sind nur als
Freitext/Boolean abgebildet.**

---

## 2. Zielmodell — die vier neuen Domänenblöcke

### Block A · Datenschutz (P1-1)

```
legal_entities ──< data_processing_activities >── data_categories
                          │        │
                          │        └──< dpa_records >── suppliers
                          │                 │
                          └──< transfer_records >── tia_assessments
                                    │
                              retention_rules
```

### Block B · Lieferanten (P1-2)

```
suppliers ──< supplier_assessments
    │
    ├──< dpa_records                (DSGVO Art. 28)
    ├──< transfer_records           (Kap. V DSGVO)
    ├──< risks                      (NIS2 Art. 21(2)(d))
    └──< ai_systems  (welcher Lieferant liefert welches KI-System)
```

Eine Entität, drei Normen. Das ist der stärkste Hebel im gesamten Backlog.

### Block C · Risiko (P1-11)

```
risks ──< risk_treatments ──< governance_workflow_tasks
  │
  ├── asset_ref  (ai_system | supplier | process | asset)
  └── risk_acceptances  (wer hat wann welches Restrisiko akzeptiert)
```

### Block D · AI-Act-Rollen und Kompetenz (P1-3, P1-4)

```
ai_systems ──< ai_system_actor_roles >── ai_actor_role (Enum)
     │                                        │
     │                                        └── abgeleitete Pflichten
     │                                             über compliance_requirements
     └──< human_oversight_measures

ai_literacy_records ──> compliance_requirements (Art. 4)
```

---

## 3. Pflichtfelder je neuer Entität

### 3.1 `legal_entities`

| Feld | Typ | Pflicht | Begründung |
|---|---|---|---|
| `id` | UUID | ✔ | |
| `tenant_id` | String(255) | ✔ | Isolation |
| `legal_name` | String(500) | ✔ | Rechtlich verbindlicher Name |
| `legal_form` | String(64) | ✔ | GmbH, AG, e. V., Körperschaft d. ö. R. |
| `registration_number` | String(128) | — | HRB o. Ä. |
| `vat_id` | String(32) | — | |
| `country_code` | Char(2) | ✔ | ISO 3166-1, bestimmt anwendbares Recht |
| `address` | JSON | ✔ | |
| `is_primary` | Bool | ✔ | Genau eine je Mandant |
| `nis2_entity_category` | Enum | ✔ | `essential \| important \| out_of_scope \| assessment_required` |
| `employee_count`, `annual_turnover_eur` | Int/Numeric | — | NIS2-Größenschwelle |
| `dpo_name`, `dpo_contact` | String | — | Art. 37 DSGVO |
| `ciso_name`, `ciso_contact` | String | — | NIS2 |

### 3.2 `suppliers` (P1-2)

| Feld | Typ | Pflicht | Begründung |
|---|---|---|---|
| `id`, `tenant_id` | UUID / String | ✔ | |
| `name`, `legal_form` | String | ✔ | |
| `country_code` | Char(2) | ✔ | Transferbewertung |
| `parent_company_jurisdiction` | Char(2) | — | **CLOUD-Act-Bewertung** — genau dieses Feld fehlt allen Wettbewerbern |
| `services_provided` | Text | ✔ | |
| `criticality` | Enum | ✔ | `critical \| high \| medium \| low` |
| `is_processor` | Bool | ✔ | DSGVO Art. 28 |
| `is_subprocessor` | Bool | ✔ | Kette |
| `nis2_relevant` | Bool | ✔ | Art. 21(2)(d) |
| `provides_ai_system` | Bool | — | Verknüpfung zu `ai_systems` |
| `contract_ref`, `contract_start`, `contract_end` | — | Fristen |
| `dpa_signed_at`, `dpa_record_id` | — | AVV vorhanden? |
| `security_requirements_ref` | — | Vertraglich vereinbarte Anforderungen |
| `last_assessment_at`, `assessment_result`, `next_assessment_due` | ✔ | Wiederkehrende Bewertung |
| `exit_plan_ref` | — | Ausstiegsfähigkeit (BaFin/DORA-Erwartung) |
| `status` | Enum | ✔ | `active \| suspended \| terminated` |

### 3.3 `risks` und `risk_treatments` (P1-11)

`risks`: `id`, `tenant_id`, `title`, `description`, `category`
(`cyber \| ai \| privacy \| supply_chain \| operational \| legal`),
`asset_type` + `asset_id` (polymorph), `threat`, `vulnerability`,
`likelihood` (1–5), `impact` (1–5), `inherent_score` (berechnet),
`treatment_decision` (`avoid \| reduce \| transfer \| accept`),
`residual_likelihood`, `residual_impact`, `residual_score`,
`owner_user_id` ✔, `identified_at` ✔, `last_reviewed_at`, `next_review_at` ✔,
`status`, `framework_refs` (JSON — NIS2 Art. 21(1), ISO 27001 6.1.2, ISO 42001 6.1).

`risk_treatments`: `risk_id`, `measure_description`, `control_id` (FK auf
`governance_controls`), `task_id` (FK auf `governance_workflow_tasks`),
`responsible_user_id`, `due_at`, `completed_at`, `effectiveness_verified_at`,
`evidence_file_id`.

`risk_acceptances`: `risk_id`, `accepted_by` (Name + Funktion), `accepted_at`,
`rationale`, `valid_until`, `approval_request_id`. — **Dies ist der Nachweis, den
Prüfer sehen wollen.**

### 3.4 `data_processing_activities` (ROPA, P1-1)

Pflichtfelder direkt aus Art. 30(1): `name`, `purpose` ✔,
`legal_basis` ✔ (Enum Art. 6(1)(a)–(f)), `legal_basis_detail`,
`special_category_basis` (Art. 9(2)), `controller_legal_entity_id` ✔,
`joint_controllers`, `data_subject_categories` ✔, `data_categories` ✔ (n:m),
`recipient_categories` ✔, `third_country_transfers` ✔ (→ `transfer_records`),
`retention_rule_id` ✔, `tom_reference` ✔, `dpia_required` (Bool),
`dpia_id`, `system_refs` (JSON), `owner_user_id`, `last_reviewed_at`, `next_review_at`.

### 3.5 `transfer_records` + `tia_assessments` (P1-1)

`transfer_records`: `processing_activity_id`, `recipient_supplier_id`,
`recipient_country` ✔, `transfer_mechanism` ✔
(`adequacy_decision \| scc \| bcr \| art49_derogation \| dpf`),
`scc_module`, `scc_version`, `signed_at`, `supplementary_measures` (Text),
`tia_assessment_id`, `risk_level`, `last_reviewed_at`.

`tia_assessments`: `transfer_record_id`, `recipient_jurisdiction_analysis`,
`government_access_risk` (`low \| medium \| high`), `applicable_surveillance_laws`,
`practical_experience`, `supplementary_measures_effectiveness`,
`conclusion` (`transfer_permissible \| permissible_with_measures \| not_permissible`) ✔,
`assessed_by`, `assessed_at` ✔, `next_review_at` ✔, `evidence_file_id`.

### 3.6 `retention_rules` + `legal_holds` (P0-5)

`retention_rules`: `tenant_id` (NULL = Systemdefault), `data_category` ✔,
`entity_table` ✔, `retention_period_days` ✔, `anchor_field` ✔ (welche Spalte
startet die Frist), `legal_basis` ✔ (z. B. „§ 147 Abs. 3 AO"),
`action` ✔ (`delete \| anonymize \| archive`), `is_system_default`, `enabled`,
`last_executed_at`.

`legal_holds`: `tenant_id`, `scope_type`, `scope_id`, `reason` ✔,
`requested_by` ✔, `active_from` ✔, `active_until`, `released_by`, `released_at`.

`data_deletion_audit`: **enthält keine Nutzdaten** — nur `table_name`, `record_id`,
`tenant_id`, `deleted_at`, `actor_id`, `retention_rule_id`, `reason`.
Muster übernommen aus der bereits vorhandenen
`compliancehub_private.runtime_state_deletion_audit`.

### 3.7 `ai_literacy_records` (P1-4)

`tenant_id`, `person_ref` ✔ (pseudonymisiert — **nicht** Klarname, Datenminimierung),
`person_role`, `organizational_unit`, `training_title` ✔, `training_provider`,
`training_type` (`internal \| external \| e_learning \| workshop`),
`completed_at` ✔, `duration_minutes`, `scope_systems` (JSON),
`competence_level` (`basic \| advanced \| expert`), `evidence_file_id`,
`valid_until`, `refresher_due_at`.

### 3.8 `regulatory_notifications` (P1-5)

Generisch für drei Regime: `tenant_id`, `incident_id`, `regime` ✔
(`nis2 \| gdpr \| ai_act \| dora \| other`), `stage` ✔
(`early_warning \| notification \| intermediate \| progress \| final`),
`authority` ✔, `authority_country`, `due_at_utc` ✔, `submitted_at_utc`,
`submitted_by_user_id`, `submission_channel`, `reference_number`,
`content_snapshot` (Text — was wurde gemeldet), `content_hash` (SHA-256),
`evidence_file_id`, `status` (`draft \| due \| submitted \| acknowledged \| overdue`).

`content_hash` macht die Meldung nachträglich unbestreitbar — starkes Prüfmerkmal.

---

## 4. Versionierung und Evidenzintegrität

### 4.1 Drei Muster, konsistent anzuwenden

| Muster | Wofür | Umsetzung |
|---|---|---|
| **Append-only Event Log** | Audit-Trail | `audit_logs` mit Hash-Kette — **vorhanden** |
| **Snapshot-Versionierung** | Policies, AI-Act-Doku, Board-Reports | Eigene `*_versions`-Tabelle mit `version_no`, `content`, `content_hash`, `created_by`, `created_at`, `superseded_at` |
| **Inhalts-Hash** | Evidenzdateien, Meldungsinhalte | SHA-256 bei Erstellung, Verifikationsendpunkt |

### 4.2 Kanonische Hash-Berechnung

Die vorhandene `_compute_entry_hash` (`app/repositories/audit_logs.py:13`) ist die
Referenz. Für neue Versionsobjekte gilt:

```
content_hash = SHA256(
    canonical_json(payload)      # sortierte Schlüssel, UTF-8, keine Leerzeichen
    + "|" + iso8601_utc(created_at)
    + "|" + (previous_hash or "")
)
```

**Wichtig:** `canonical_json` muss deterministisch sein (sortierte Keys, feste
Zahlenformatierung), sonst ist die Kette nach einem Bibliotheks-Update nicht mehr
verifizierbar. Als eigene Funktion in `app/services/canonical_hash.py` implementieren
und mit einem Golden-Test gegen fixe Erwartungswerte absichern.

### 4.3 Externer Anker (P1-16)

Die interne Hash-Kette beweist Konsistenz, nicht Nicht-Manipulation. Ergänzung:
täglicher `audit_anchor` je Mandant mit dem Kopf-Hash der Kette, versehen mit einem
RFC-3161-Zeitstempel einer qualifizierten Zeitstempelstelle. Erst damit ist die
Aussage „nachträgliche Änderung nachweisbar" belastbar.

---

## 5. Konsolidierung bestehender Doppelstrukturen

Das Modell ist gewachsen und enthält drei Parallelwelten. Vor jedem weiteren Ausbau
sind sie zu klären — sonst wächst die Divergenz.

| Doppelung | Tabellen | Empfehlung |
|---|---|---|
| Requirements | `compliance_requirements` vs. `governance_requirements` | `governance_requirements` als führend; `compliance_requirements` migrieren |
| Controls | `compliance_controls` vs. `governance_controls` | `governance_controls` als führend (hat Evidence, Reviews, Statushistorie, Framework-Mappings) |
| Incidents | `incidents`, `nis2_incidents`, `service_health_incidents`, `ai_runtime_incident_summaries` | Eine `incidents`-Basistabelle + regime-spezifische Erweiterungstabellen |
| Tasks | `governance_workflow_tasks` vs. `remediation_actions` (+7 Satelliten) | `governance_workflow_tasks` als führend; Remediation als Task-Subtyp |
| Board-Reports | `board_reports` vs. `ai_compliance_board_reports` | Generalisieren |

**Priorität P2** — nicht vor P0. Konsolidierung ohne Migrationsframework (Alembic,
P2-6) ist riskant.

---

## 6. RLS-Strategie

### 6.1 Zielbild

Alle mandantenbezogenen Tabellen erhalten:

```sql
ALTER TABLE <t> ENABLE ROW LEVEL SECURITY;
ALTER TABLE <t> FORCE ROW LEVEL SECURITY;   -- gilt auch für den Tabelleneigentümer

CREATE POLICY <t>_tenant_isolation ON <t>
  FOR ALL TO compliancehub_runtime_app
  USING      (tenant_id = NULLIF(current_setting('compliancehub.tenant_id', TRUE), ''))
  WITH CHECK (tenant_id = NULLIF(current_setting('compliancehub.tenant_id', TRUE), ''));
```

`FORCE` ist entscheidend: ohne ihn umgeht der Tabelleneigentümer die Policy.
Die Runtime-Rolle ist `NOLOGIN NOBYPASSRLS` und **nicht** Eigentümerin der Tabellen —
dieses Muster existiert bereits korrekt in
`db/postgres/migrations/20260715_advisor_runtime_state_rls.sql` und ist auf den
Kern zu übertragen.

### 6.2 GUC-Vereinheitlichung

**Heute inkonsistent:** `app/db_tenant.py` setzt `app.current_tenant`, die einzige
existierende Policy prüft `compliancehub.tenant_id`. Verbindlich wird
**`compliancehub.tenant_id`**.

### 6.3 Setzen der GUC — fail-closed

```python
# app/db_tenant.py — Zielzustand
async def get_async_db(request: Request) -> AsyncGenerator[AsyncSession, None]:
    auth = getattr(request.state, "auth_context", None)
    if auth is None or not auth.tenant_id:
        raise HTTPException(status_code=401, detail="No authenticated tenant context")
    async with AsyncSessionLocal() as session:
        await session.execute(
            text("SELECT set_config('compliancehub.tenant_id', :tid, true)"),
            {"tid": str(auth.tenant_id)},
        )
        yield session
```

Zwei Änderungen gegenüber heute: der Mandant kommt aus dem **authentifizierten**
Kontext (nie aus einem Header), und ein fehlender Kontext führt zu einem Fehler statt
zu einer Session ohne Schranke.

Für die **sync**-Session (`app/db.py`) ist dasselbe über ein
`SessionEvents.after_begin`-Event nachzuziehen — sonst hat der Großteil der
Anwendung weiterhin keine DB-Schranke.

### 6.4 Plattformzugriffe

Für mandantenübergreifende Funktionen (Advisor-Portfolio, Admin-Provisionierung,
Retention-Job) gilt das bereits vorhandene Zwei-Rollen-Muster:
`compliancehub_runtime_app` (mandantengebunden) und
`compliancehub_runtime_platform_app` (Plattform, mit `compliancehub.platform_access`).
Jeder Plattformzugriff **muss** einen Audit-Eintrag erzeugen.

### 6.5 Migrationsreihenfolge

1. Runtime-Rollen und Grants anlegen; Anwendung auf die Runtime-Rolle umstellen
   (**nicht** mehr als Tabelleneigentümer verbinden).
2. GUC-Setzung in beiden Session-Pfaden aktivieren.
3. RLS zunächst nur mit `ENABLE` (ohne `FORCE`) auf einer Tabellengruppe,
   Shadow-Betrieb, Fehler beobachten.
4. `FORCE` aktivieren.
5. Gruppenweise über alle Tabellen ausrollen.
6. Negativtests je Gruppe in `tests/postgres/`.

**Risiko:** RLS bricht mandantenübergreifende Abfragen, die heute stillschweigend
funktionieren. Genau deshalb sind Schritte 3 und 6 nicht verhandelbar.

---

## 7. Migrationsplan

| Welle | Inhalt | Voraussetzung | Aufwand |
|---|---|---|---|
| **M1** | Alembic einführen, aktuellen Zustand als Baseline stempeln | — | M |
| **M2** | RLS-Rollen, Grants, GUC-Umstellung, RLS auf Gruppe 1 (`ai_*`) | M1 | M |
| **M3** | Evidence-Härtung: `sha256`, `scan_status`, `data_classification` (P0-4) | M1 | S |
| **M4** | NIS2-Fristenanker: `became_aware_at`, `deadline_basis` + Backfill (P0-2) | M1 | S |
| **M5** | Retention: `retention_rules`, `legal_holds`, `data_deletion_audit` (P0-5) | M1 | M |
| **M6** | Lieferanten: `suppliers`, `supplier_assessments` (P1-2) | M1 | M |
| **M7** | Datenschutz: ROPA, `data_categories`, `transfer_records`, `tia_assessments`, `dpa_records` (P1-1) | M6 | L |
| **M8** | Risiko: `risks`, `risk_treatments`, `risk_acceptances` (P1-11) | M6 | M |
| **M9** | AI-Act: `ai_system_actor_roles`, `ai_literacy_records`, `human_oversight_measures` (P1-3/4/12) | M1 | M |
| **M10** | Meldungen: `regulatory_notifications` (P1-5) | M4 | S |
| **M11** | RLS auf alle übrigen Tabellengruppen | M2 | L |
| **M12** | Konsolidierung der Doppelstrukturen (§5) | M11 | XL |

**Regel für alle Migrationen:** additiv, rückwärtskompatibel, mit Backfill und
Rollback-Skript. Kein `DROP COLUMN` im selben Release wie die Umstellung des Codes.

---

## 8. Was das Zielmodell verkaufbar macht

Nach M6–M9 kann das Produkt Aussagen treffen, die heute keiner der DACH-Wettbewerber
belegen kann:

- „Zeigen Sie mir alle Lieferanten mit US-Muttergesellschaft, die personenbezogene
  Daten verarbeiten, und deren TIA älter als 12 Monate ist."
- „Zeigen Sie mir alle KI-Systeme, bei denen wir Anbieter statt Betreiber sind, und
  die daraus folgenden offenen Pflichten."
- „Zeigen Sie mir alle Risiken, deren Restrisiko akzeptiert wurde, ohne dass die
  Geschäftsleitung unterschrieben hat."
- „Zeigen Sie mir den KI-Kompetenz-Abdeckungsgrad je Organisationseinheit."

Das sind die Fragen, die Vorstand, Aufsichtsrat und Prüfer tatsächlich stellen — und
sie sind ohne die vier neuen Domänenblöcke nicht beantwortbar.
