# 04 – NIS2 / BSIG Gap-Analyse (Deutschland)

**Gegenstand:** Richtlinie (EU) 2022/2555 (NIS2) und ihre deutsche Umsetzung im
BSI-Gesetz (NIS2-Umsetzungsgesetz).

> **Hinweis:** Die deutsche Umsetzung und die zugehörigen Rechtsverordnungen waren
> Gegenstand eines längeren Gesetzgebungsverfahrens. Paragraphenverweise auf das BSIG
> in diesem Dokument sind **indikativ** und vor jeder Außenkommunikation gegen die
> geltende Fassung zu prüfen. Die funktionale Bewertung ist davon unabhängig, weil sie
> auf den Pflichtenkategorien der Richtlinie aufsetzt.

---

## 1. Betroffenheits- und Scope-Modell

**Status: TEILWEISE BELEGT — mit strukturellem Mangel.**

| Element | Umsetzung | Bewertung |
|---|---|---|
| Mandanten-Scope-Flag | `tenants.nis2_scope`, Default `"in_scope"` | **Problematisch** — siehe unten |
| KRITIS-Sektor | `tenants.kritis_sector` (nullable String) | Vorhanden, ohne Enum-Validierung |
| Einrichtungskategorie | Normalisierung in `app/services/advisor_portfolio_priority.py:182–201` auf `essential_entity` / `important_entity` | Vorhanden, aber **nur in einer Advisor-Ableitungsfunktion**, nicht als Mandantenattribut |
| Scope-Wizard | `frontend/src/app/tenant/nis2/wizard/[sessionId]` | Vorhanden |
| Scope je KI-System | `ai_system_inventory_profiles.nis2_scope`, Default `review_needed` | Gut gelöst |

**Zwei Mängel:**

**(1) `nis2_scope` defaultet auf `"in_scope"`.**
Ein neu angelegter Mandant gilt damit ohne jede Prüfung als NIS2-betroffen. Für ein
Tool, dessen Kernwert die *Betroffenheitsklärung* ist, ist das die falsche
Voreinstellung. Korrekt wäre `unknown` / `assessment_required`, mit erzwungener
Bewertung. Zusätzlich ist `advisor_portfolio_priority.py:201` ein `return
"important_entity"` als Fallback — also **stille Annahme der Betroffenheit** bei
unbekanntem Wert.

**(2) Die Betroffenheitsprüfung ist nicht als Nachweis modelliert.**
NIS2-Betroffenheit ergibt sich aus Sektor (Anhang I/II), Größenschwelle
(mind. 50 Beschäftigte oder > 10 Mio. € Jahresumsatz/Bilanzsumme) und
Sonderregelungen unabhängig von der Größe. Das Ergebnis ist ein
**begründungspflichtiges Prüfergebnis**, das der Kunde gegenüber der Aufsicht
darstellen können muss — inklusive der Grundlage („warum bin ich *nicht* betroffen?").

**Empfehlung (P1-6):** Entität `nis2_scope_assessment`:
`tenant_id`, `legal_entity_id`, `sector_annex` (I/II + Sektorcode), `subsector`,
`employee_count`, `annual_turnover_eur`, `balance_sheet_total_eur`,
`size_threshold_met` (bool), `special_rule_applies` (bool, Begründung),
`result` (`essential | important | out_of_scope`), `rationale`,
`assessed_by_user_id`, `assessed_at_utc`, `next_review_at_utc`,
`evidence_file_id`.

Ohne diese Entität ist der Claim „Betroffenheitsanalyse" nicht belegbar.

---

## 2. Rolle und Pflichten der Geschäftsleitung (Art. 20 NIS2)

**Status: NICHT VORHANDEN.**

`grep -ri "geschaeftsleitung\|management_body\|leitungsorgan"` in `app/` → **0 Treffer**.

Art. 20 verlangt zwei Dinge, die beide **nachweispflichtig** sind:

1. Die Leitungsorgane müssen die Risikomanagementmaßnahmen **billigen** und ihre
   Umsetzung **überwachen**; sie können persönlich haftbar gemacht werden.
2. Die Leitungsorgane müssen **Schulungen** absolvieren und vergleichbare Schulungen
   für Beschäftigte anbieten.

Das Produkt hat `board_reports`, `board_report_snapshots`, `approval_requests` und
`board_readiness_models` — also die **Bausteine**, aber keine Verbindung, die den
Nachweis „Die Geschäftsleitung hat die NIS2-Maßnahmen am TT.MM.JJJJ gebilligt"
erzeugt.

**Empfehlung (P1-6):** Entität `management_body_approval`:
`tenant_id`, `subject_type` (`nis2_measures | risk_treatment_plan | policy | board_report`),
`subject_id`, `approved_by` (Name + Funktion), `approval_date`, `approval_minutes_ref`,
`evidence_file_id`, `valid_until`, `next_approval_due`.
Plus `management_training_record` analog zum AI-Literacy-Record (Art. 4 KI-VO).

**Vertriebsargument:** Genau dieser Nachweis ist es, was Geschäftsführer in DACH
nachts wachhält, seit die persönliche Haftung diskutiert wird. Ein Modul
„Geschäftsleitungs-Billigung mit Nachweisakte" ist ein sehr gut verkaufbares Feature
mit geringem Bauaufwand.

---

## 3. Risikomanagement (Art. 21(1))

**Status: TEILWEISE — Kernlücke.**

Vorhanden: `risk_classifications` (für KI-Systeme), `compliance_requirements`,
`governance_controls`, `readiness_score_service`, `governance_maturity_service`,
`what_if_simulator`.

**Fehlend: ein Risikoregister als eigene Entität.** Es gibt in 103 Tabellen
**keine** `risks`- oder `risk_treatments`-Tabelle. Ein NIS2-Risikomanagement nach
„gefahrenübergreifendem Ansatz" (all-hazards) braucht:

- Risiko-Objekt (Asset/Prozess, Bedrohung, Schwachstelle, Eintrittswahrscheinlichkeit,
  Auswirkung, Bruttorisiko)
- Behandlungsentscheidung (vermeiden / vermindern / übertragen / akzeptieren)
- Zugeordnete Maßnahmen mit Verantwortlichem und Termin
- Nettorisiko nach Maßnahmen
- Risikoakzeptanz durch benannte Person mit Datum
- Review-Zyklus

Ohne dieses Register ist das Produkt für NIS2 ein **Maßnahmen-Tracker**, kein
**Risikomanagementsystem** — und ISO-27001-Berater merken das in der ersten Demo.

**Empfehlung (P1-2):** Entitäten `risk` und `risk_treatment` (Details in `08`).
Hoher Hebel: dasselbe Register bedient NIS2 Art. 21(1), ISO 27001 Kap. 6.1/8.2/8.3
und ISO 42001 — also drei Normen der beworbenen Positionierung.

---

## 4. Maßnahmenkatalog (Art. 21(2) a–j)

**Status: BELEGT IM CODE — gut abgedeckt.**

Die zehn Maßnahmenbereiche sind über `compliance_requirements` +
`governance_controls` + `governance_control_framework_mappings` abbildbar.
`app/config/norm_evidence_defaults.py` (10 KB) liefert Standard-Evidenzerwartungen.

| Art. 21(2) | Bereich | Abdeckung |
|---|---|---|
| (a) | Risikoanalyse, Sicherheitskonzepte | Requirement/Control ✔, Risikoregister ✘ |
| (b) | Bewältigung von Sicherheitsvorfällen | `nis2_incidents` ✔ |
| (c) | Business Continuity, Backup, Krisenmanagement | Control ✔; `ai_systems.has_backup_runbook` als Flag |
| (d) | Sicherheit der Lieferkette | **Schwach** — siehe §5 |
| (e) | Sicherheit bei Erwerb/Entwicklung/Wartung | Control ✔ |
| (f) | Bewertung der Wirksamkeit | `governance_control_reviews` ✔ |
| (g) | Cyberhygiene, Schulungen | **Lücke** — kein Trainingsregister |
| (h) | Kryptografie/Verschlüsselung | Control ✔ (nur als Anforderung) |
| (i) | Personalsicherheit, Zugriffskontrolle, Asset-Management | `access_reviews`, `sod_policies`, RBAC ✔; **Asset-Register ✘** |
| (j) | MFA, gesicherte Kommunikation, Notfallkommunikation | MFA ✔ |

**Lücke Asset-Management:** Es gibt kein generisches Asset-Register — nur
`ai_systems`. NIS2 Art. 21(2)(i) und ISO 27001 A.5.9 verlangen ein Inventar der
Informationswerte. **P1.**

---

## 5. Lieferketten- und Lieferantenrisiko (Art. 21(2)(d), Art. 21(3))

**Status: KRITISCHE LÜCKE.**

Vorhanden ist ausschließlich:
- `ai_systems.has_supplier_risk_register` — ein **Boolean-Flag**
- `app/services/ai_governance_suppliers.py` — Ableitungen auf Basis dieses Flags
- `frontend/src/app/board/suppliers` — Darstellung

Es existiert **keine `suppliers`-Tabelle**. Damit ist nicht abbildbar:

- Wer sind meine Lieferanten und Dienstleister?
- Welche Kritikalität hat jeder für welchen Prozess?
- Welche Sicherheitsanforderungen sind vertraglich vereinbart?
- Wann wurde er zuletzt bewertet? Mit welchem Ergebnis?
- Welche Schwachstellen/Vorfälle betrafen ihn?
- Ist er selbst NIS2-betroffen? Ist er Subprozessor nach Art. 28 DSGVO?

**Doppelter Schaden:** Dieselbe Entität wird für DSGVO Art. 28 (Auftragsverarbeiter),
für die Subprozessorenliste und für die Transfer-Records gebraucht
(`05-gdpr-cloud-act-gap-analysis.md`). Die Lücke schlägt in drei Normen zugleich durch.

**Empfehlung (P1-2):** Entität `supplier` mit
`is_processor` (DSGVO), `is_subprocessor`, `nis2_relevant`, `criticality`,
`country`, `parent_company_jurisdiction`, `services_provided`,
`contract_ref`, `dpa_signed_at`, `security_requirements_ref`,
`last_assessment_at`, `assessment_result`, `next_assessment_due`,
`incidents_count`, `exit_plan_ref`.

Dies ist die **einzelne Ergänzung mit dem höchsten Nutzen im gesamten Backlog.**

---

## 6. Incident-Management und Meldekaskade (Art. 23)

**Status: KRITISCHER BLOCKER — funktional falsch.**

### 6.1 Was vorhanden ist

`nis2_incidents` (`app/models_db.py:1755`) mit:
- `bsi_notification_deadline` (24 h)
- `bsi_report_deadline` (72 h)
- `final_report_deadline` (1 Monat)
- Lebenszyklus: `detected_at`, `contained_at`, `eradicated_at`, `recovered_at`, `closed_at`
- Workflow-Status, KRITIS-Relevanz, Betroffenheit personenbezogener Daten
- Überfälligkeitsprüfung (`_deadline_overdue`)
- Board-Alerts über `enterprise_control_center.py:101` („BSI-Frühmeldung")

Die Struktur ist **richtig gedacht**. Die Implementierung ist es nicht.

### 6.2 Blocker 1 — Fristen laufen ab Dateneingabe, nicht ab Kenntniserlangung

```python
# app/repositories/nis2_incidents.py:79-97
now = datetime.now(UTC)
report_deadline = now + timedelta(hours=NIS2DeadlinePolicy.REPORT_HOURS)
row = NIS2IncidentTable(
    ...
    bsi_notification_deadline=now + timedelta(hours=NIS2DeadlinePolicy.NOTIFICATION_HOURS),
    bsi_report_deadline=report_deadline,
    final_report_deadline=report_deadline + timedelta(days=...),
    detected_at=now,          # <-- immer "jetzt"
)
```

Und das Eingabemodell:

```python
# app/nis2_incident_models.py:43-51
class NIS2IncidentCreate(BaseModel):
    title, incident_type, severity, summary,
    affected_systems, kritis_relevant,
    personal_data_affected, estimated_impact
    # KEIN detected_at / became_aware_at
```

**Konsequenz:** Art. 23 knüpft die Fristen an die **Kenntniserlangung** von dem
erheblichen Sicherheitsvorfall. Ein Vorfall, den ein Kunde am Freitagabend bemerkt und
am Montagmorgen erfasst, bekommt im Tool eine Frühwarnfrist bis Dienstag — während sie
real bereits am Samstag abgelaufen ist.

**Das Produkt zeigt in diesem Fall „im Fristenrahmen" an, obwohl der Kunde die Frist
verletzt hat.** Für ein Fristenüberwachungstool ist das der schwerstmögliche Defekt:
Es erzeugt falsche Sicherheit in genau der Situation, für die es gekauft wurde.

**Fix (P0-2):** Pflichtfeld `became_aware_at_utc` im Create-Modell, Validierung
`became_aware_at <= now`, Warnung bei Rückdatierung > 24 h, alle Fristen ab diesem
Anker, `detected_at` als separates optionales Feld (technische Detektion ≠
Kenntniserlangung der verantwortlichen Stelle).

### 6.3 Blocker 2 — Kein Nachweis der tatsächlichen Meldung

Die Tabelle speichert **nur Fristen**, keine Meldungen. Es fehlen:

| Fehlendes Feld/Objekt | Warum nötig |
|---|---|
| `submitted_at` je Meldestufe | Nachweis der Fristwahrung |
| `authority` (BSI / Landesbehörde / CSIRT / Aufsichtsbehörde) | Mehrere Empfänger möglich |
| `reference_number` / Aktenzeichen | Rückverfolgbarkeit |
| Meldungsinhalt (Snapshot) | „Was wurde gemeldet?" ist prüfungsrelevant |
| Zwischenmeldung (Art. 23(4)(c)) | Auf Ersuchen der Behörde; fehlt ganz |
| Fortschrittsbericht bei laufendem Vorfall | Art. 23(4)(d) Alt. |
| Grenzüberschreitende Betroffenheit | Art. 23(4) — Weiterleitung an andere MS |
| Parallele DSGVO-Meldung (Art. 33) | `personal_data_affected` ist da; die 72-h-Meldung an die Datenschutzaufsicht wird nicht erzeugt |

**Fix (P1-5):** Entität `regulatory_notification` (generisch, auch für AI Act Art. 73
und DSGVO Art. 33/34 nutzbar) mit
`incident_id`, `notification_stage` (`early_warning | incident_notification |
intermediate | final | progress`), `regime` (`nis2 | gdpr | ai_act | dora | other`),
`authority`, `due_at_utc`, `submitted_at_utc`, `submitted_by_user_id`,
`reference_number`, `content_snapshot`, `evidence_file_id`, `status`.

### 6.4 Blocker 3 — Fristen laufen nur, wenn extern gescheduled

`app/services/health_monitor.py:4–5` und der offene TODO in Zeile 219 belegen: es gibt
keinen In-Process-Scheduler. Eskalationen und Reminder hängen an n8n oder Cron, die
nicht Teil des Deployments sind (weil es kein Deployment-Artefakt gibt, siehe `01` §12).

**Ein Kunde kann heute nicht feststellen, ob seine Fristenüberwachung tatsächlich
läuft.** Fix: P0-6 (Scheduler + Heartbeat-Anzeige „Fristenprüfung zuletzt gelaufen am …").

### 6.5 Detail — „ein Monat" ≠ 30 Tage

`NIS2DeadlinePolicy.FINAL_REPORT_DAYS_AFTER_REPORT = 30` und die Verankerung am
72-h-**Deadline** statt am tatsächlichen **Meldezeitpunkt**. Art. 23(4)(d) knüpft an die
Übermittlung der Meldung nach Buchstabe b. Korrekt: `submitted_at(incident_notification)
+ relativedelta(months=1)`. Solange keine Meldung erfasst ist, ist ein Default zulässig —
er muss dann aber als Default gekennzeichnet sein.

---

## 7. Registrierungspflicht

**Status: NICHT VORHANDEN.**

NIS2 verlangt die Registrierung betroffener Einrichtungen bei der zuständigen Stelle
(in DE: BSI) mit Angaben zu Name, Anschrift, Sektor, Kontaktdaten, IP-Bereichen,
Mitgliedstaaten mit Diensterbringung — und die Aktualisierung bei Änderungen.

Im Produkt: kein Feld, kein Workflow, keine Frist.

**Empfehlung (P2):** `nis2_registration` mit `registered_at`, `registration_reference`,
`last_updated_at`, `next_review_due`, `contact_person`, `notified_member_states`.
Aufwandsarm, hoher wahrgenommener Nutzen.

---

## 8. Auditierbarkeit und Nachweise für Aufsicht/Board/Prüfer

**Status: BELEGT IM CODE — Stärke.**

| Fähigkeit | Umsetzung |
|---|---|
| Audit-Trail mit Hash-Kette | `audit_logs`, `verify_integrity()` |
| Behördliches Prüfpaket | `app/services/authority_audit_preparation_pack.py` |
| Evidence-Bundles mit ECDSA-Signatur | `evidence_bundles` (`signature`, `cert_fingerprint`, `signing_key_id`, `signed_payload`) |
| Trust Center mit Sensitivity-Stufen und Access-Log | `trust_center_assets`, `trust_center_access_logs` |
| Board-Reports mit Snapshots und Metrik-Historie | `board_reports`, `board_report_snapshots`, `board_report_metric_history` |
| KRITIS-KPIs mit Board-Alert-Schwellen | `nis2_kritis_kpis`, `app/config/nis2_kritis_board_alert_thresholds.py` |
| Governance-Audit-Cases | `governance_audit_cases` + Framework-/Control-Verknüpfung |

Das ist der reifste Teil des Produkts und ein echtes Verkaufsargument gegenüber
Wirtschaftsprüfern und internen Revisionen.

**Einschränkung:** siehe `01` §7 — Append-only ist ORM-seitig, die Hash-Kette hat
keinen externen Anker.

---

## 9. Aufgaben, Eskalationen, Fristen

**Status: BELEGT IM CODE — gut, aber ohne Ausführungsgarantie.**

`governance_workflow_tasks` mit `due_at_utc`, `escalation_level`,
`assignee_user_id`, `template_code`, `framework_tags`, SLA-Defaults
(`governance_workflow_templates.default_sla_days`), History-Tabelle, Überfälligkeitslogik
(`_task_is_overdue`), deterministisches Regel-Bundle mit `RULE_BUNDLE_VERSION`,
Remediation mit Eskalationen und Remindern.

Das ist eine **gute** Workflow-Engine. Sie leidet ausschließlich am fehlenden
Scheduler (§6.4).

---

## 10. Technische vs. organisatorische Maßnahmen

**Status: LÜCKE.**

`governance_controls` hat kein Feld, das eine Kontrolle als *technisch*,
*organisatorisch*, *physisch* oder *personell* klassifiziert. Für Prüfer ist genau
diese Aufteilung der Einstieg in jedes Interview, und ISO-27001-Berichte gliedern
danach.

**Empfehlung (P2):** `control_nature` als Enum + `control_type`
(`preventive | detective | corrective | deterrent`) + `automation_level`
(`manual | semi_automated | automated`). Sehr kleiner Aufwand, hoher Prüferwert.

---

## 11. Dokumentation je Mandant

**Status: BELEGT IM CODE.** Alle relevanten Tabellen sind `tenant_id`-scoped,
Advisor-Portfolio erlaubt mandantenübergreifende Sicht für Berater
(`app/services/advisor_portfolio.py`), mit eigenem Auth-Pfad
(`require_advisor_api_access`).

**Sicherheitsanmerkung:** Der Advisor-Pfad autorisiert über
`validate_api_key_only` + `x-advisor-id`-Header + optionale ENV-Allowlist
(`app/security.py:80–110`). Die Zuordnung Advisor → erlaubte Mandanten läuft über
`advisor_tenants`. Diese Kombination — globaler API-Key plus selbstdeklarierter
Header — ist die **schwächste Autorisierungsstelle im gesamten Code** und gehört
in die Cross-Tenant-Testsuite (P0-6) und mittelfristig auf Session-Auth umgestellt.

---

## 12. Gesamtbewertung NIS2

| Bereich | Abdeckung | Bewertung |
|---|---|---|
| Scope-/Betroffenheitsmodell | 35 % | Default `in_scope` ist falsch; kein Prüfnachweis |
| Geschäftsleitung (Art. 20) | 0 % | Lücke mit hohem Verkaufswert |
| Risikomanagement (Art. 21(1)) | 25 % | Kein Risikoregister |
| Maßnahmenkatalog (Art. 21(2)) | 70 % | Gut über Requirements/Controls |
| Lieferkette (Art. 21(2)(d)) | 10 % | **Kernlücke, dreifach wirksam** |
| Incident-Management | 55 % | Struktur gut, Fristenanker **falsch** |
| Meldekaskade (Art. 23) | 20 % | Fristen ja, Meldungsnachweise nein |
| Registrierung | 0 % | Lücke, leicht schließbar |
| Auditierbarkeit | 80 % | **Stärke** |
| Aufgaben/Eskalation/Fristen | 65 % | Gut; Ausführung nicht garantiert |
| Tech./org. Maßnahmenabgrenzung | 0 % | Lücke, minimaler Aufwand |
| Dokumentation je Mandant | 85 % | Stärke |

### Reifegrad-Score NIS2: **41 / 100**

**Der Score wird maßgeblich vom Fristenanker-Defekt gedrückt.** Ein Fristentool mit
falschem Fristenanker ist funktional wertlos und rufschädigend. Nach Umsetzung von
P0-2 und P1-5 steigt der Score realistisch auf ~65.

### Zulässige Außenkommunikation (Stand heute)

✅ „Strukturierte Erfassung von NIS2-Maßnahmen mit Kontrollen, Evidenz und Reviews"
✅ „KRITIS-KPIs und Board-Alerts"
✅ „Audit-Trail mit Integritätsprüfung und behördlichem Prüfpaket"
✅ „Governance-Workflows mit SLA und Eskalationsstufen"

❌ „NIS2-ready" / „NIS2-konform"
❌ „24h/72h-Meldekaskade" — **bis P0-2 umgesetzt ist, ist dieser Claim sachlich falsch**
❌ „Lieferkettenrisikomanagement"
❌ „automatische Fristenüberwachung" (ohne Scheduler-Nachweis)
❌ „Betroffenheitsanalyse" (ohne dokumentiertes Prüfergebnis)
