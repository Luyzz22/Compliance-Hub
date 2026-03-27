# Internes Demo-Skript: Board- & Berater-Walkthrough (ComplianceHub)

Zielgruppe: **Sales**, **Customer Success**, **Berater-Partner** – reproduzierbare Führung für **CISO/Board** (ein Mandant) und **Advisor** (Portfolio + Deep Dive).  
Technische Provisionierung: [`demo-governance-maturity-flow.md`](./demo-governance-maturity-flow.md).

**Kernbotschaft in drei Säulen** (Begriffe wie in der UI, siehe [`governance-maturity-copy-de.md`](./governance-maturity-copy-de.md))

| Säule | Produktname (deutsch) | Was Sie sagen (1 Satz) |
|-------|------------------------|-------------------------|
| **Struktur** | **AI & Compliance Readiness** | „Wo stehen Aufbau, Framework-Abdeckung, KPI-Register, Lücken und Board-Reporting – also die strukturelle KI-Compliance-Reife zu EU AI Act, ISO/IEC 42001 und 27001?“ |
| **Nutzung** | **Governance-Aktivitätsindex (GAI)** | „Nutzen wir Playbook, Cross-Regulation und Board-Reports wirklich – oder nur auf dem Papier?“ |
| **Betrieb** | **Operativer KI-Monitoring-Index (OAMI)** | „Welche technischen Laufzeit-Signale sehen wir – zur Einordnung von Post-Market-Monitoring und NIS2-Incident-Themen, ohne automatische Melde-Entscheidung?“ |

**Reifegrade Readiness:** Basis · Etabliert · Integriert. **Stufen GAI/OAMI:** Niedrig · Mittel · Hoch.

Alle **Demodaten sind synthetisch** (keine echten Betriebs- oder Personendaten). Runtime-Events und Telemetrie sind **realistisch**, aber **nicht** aus Produktiv-SAP.

---

## Vorbereitung (ca. 5 Minuten vor Termin)

1. **Backend** mit Demo-ENV: `COMPLIANCEHUB_DEMO_SEED_API_KEYS`, `COMPLIANCEHUB_DEMO_SEED_TENANT_IDS`, Feature **demo_seeding** aktiv.  
2. **Mandant anlegen** (Allowlist + Key):
   ```http
   POST /api/v1/demo/tenants/seed
   x-api-key: <demo-seed-key>
   {"template_key": "industrial_sme", "tenant_id": "demo-mittelstand-ag"}
   ```
   (oder Preset `python scripts/seed_demo_tenant.py --preset mittelstand-ag`.)  
3. **Frontend**: Workspace mit `x-tenant-id` / Login auf genau diesen Mandanten; bei **Advisor-Demo** `NEXT_PUBLIC_ADVISOR_ID` und Mandanten-Link gesetzt.  
4. **Flags**: Readiness, Board-Report, Advisor-Snapshot nach Bedarf **an** (wie Pilot).

**Checkliste vor Live-Demo:** Mandant öffnet sich, Board-Report-Liste nicht leer, Readiness-Karte lädt, bei Advisor: Portfolio zeigt Zeilen.

---

## A) CISO / Board – Ein Mandant, Deep Dive (~10 oder ~15 Min.)

### Screen-Folge (empfohlen)

| # | Screen / Bereich | Dauer (10′ / 15′) | Was Sie zeigen |
|---|------------------|-------------------|----------------|
| 1 | **Workspace-Banner** | 1′ / 1′ | Demo read-only: keine produktiven Änderungen; Daten gekennzeichnet. |
| 2 | **KI-Register** (`/tenant/ai-systems`) | 2′ / 3′ | Hochrisiko-Systeme (Anhang III), Kurzbezug **EU AI Act**; NIS2-Relevanz über Kritikalität. |
| 3 | **Cross-Regulation** (`/tenant/cross-regulation-dashboard`) | 2′ / 4′ | Coverage vs. Gaps (**Art. 9, 11, 12** etc.), ISO-42001/27001-Kontext. |
| 4 | **Board-KPIs / NIS2** (`/board/nis2-kritis`, `/board/kpis`) | 1′ / 2′ | Incident-Readiness, Supplier – **NIS2**-Narrativ ohne Rechtsberatung. |
| 5 | **AI Compliance Board-Report** (`/board/ai-compliance-report`) | 2′ / 3′ | **AI & Compliance Readiness**-Karte; **Demomandant**-Banner; vorgefüllter **Demo-Board-Report**; OAMI im Report wo vorhanden. |
| 6 | **Optional 15′** | +3′ | EU-AI-Act-Readiness-Seite, Playbook, oder API **Governance Maturity** (Readiness + **governance_activity** + **operational_ai_monitoring**). |

### Talking Points (Auszug) – gleiche Wortwahl wie in der Oberfläche

- „**AI & Compliance Readiness** bündelt die fünf Dimensionen struktureller Reife – das ist unsere **board-taugliche** Einordnung, **nicht** die juristische Hochrisiko-Klassifikation und **nicht** dasselbe wie die Spalte **EU AI Act (Register)** im Berater-Portfolio.“  
- „Der **Governance-Aktivitätsindex** zeigt, ob die Governance-Funktionen **tatsächlich genutzt** werden – Unterscheidung von Papier-Compliance.“  
- „Der **operative KI-Monitoring-Index** fasst Laufzeit-Signale zusammen – Gespräch zu **EU AI Act** Post-Market-Monitoring und **NIS2**-Incidents, **ohne** automatische Qualifikation von Meldepflichten.“

### OAMI und Incident-Subtypes (optional, ~1 Minute)

Der Index gewichtet u. a. nach **Laufzeit-Subtype** (z. B. sicherheitsnahe vs. verfügbarkeitsbezogene Signale). Für ein glaubwürdiges Narrativ ohne Live-Zahlenpaukerei eignen sich die synthetischen **Golden-Szenarien** unter `tests/fixtures/oami-subtype-explain/` (S1–S3); CI deckt Index, Stufe und Keywords ab (`tests/test_oami_subtype_explain_golden.py`).

| Szenario | Kurzinhalt | Beispiel-Satz für den Presenter (aus Fixture `presenter_script_de`) |
|----------|------------|----------------------------------------------------------------------|
| **S1** | Wenige Incidents, Schwerpunkt **safety_violation** + hohe Schwere | „Hier sehen Sie, dass der OAMI vor allem durch sicherheitsrelevante Incidents getrieben wird: wenige Ereignisse, aber mit Subtype safety_violation und hoher Schwere – das Gewicht im Index liegt stärker auf Sicherheit als auf reiner Verfügbarkeit.“ |
| **S2** | Mehr Incidents, überwiegend **availability_incident** | „Hier dominieren Verfügbarkeits-Incidents: der OAMI bleibt mittel, aber die Einordnung zeigt, dass die Lage primär Betriebsstabilität betrifft – nicht denselben Gewichtspfad wie sicherheitsklassifizierte Subtypes.“ |

### Typische Board-/CISO-Fragen (diese Demo adressiert)

- „**Wie sehen wir unseren EU-AI-Act-Reifegrad** über eine Zahl hinaus?“ → Readiness-Dimensionen + Cross-Reg-Gaps.  
- „**Wie koppeln wir NIS2-Incidents an KI-Governance?**“ → NIS2-KPIs + Runtime-/OAMI-Narrativ + Actions im Register.  
- „**Was fehlt uns noch vor 2026?**“ → Offene Actions, rote/amber Gaps, Board-Report-Empfehlungen (Demo-Text).

---

## B) Advisor – Portfolio + ein Mandant (~10 oder ~15 Min.)

### Screen-Folge

| # | Screen | Dauer (10′ / 15′) | Was Sie zeigen |
|---|--------|-------------------|----------------|
| 1 | **Advisor-Portfolio** (`/advisor`) | 2′ / 3′ | Vergleich Mandanten: Spalte **EU AI Act (Register)**, **Readiness** (struktureller Score), Cross-Reg-Ø, High-Risk. Hinweiszeile zu **GAI** und **OAMI** im Snapshot. |
| 2 | **Spalten-Tooltips** | 0.5′ | **Readiness** = AI & Compliance Readiness (fünf Dimensionen); **EU AI Act (Register)** = Register-Heuristik. |
| 3 | **Governance-Snapshot** (Mandant wählen) | 4′ / 6′ | Einleitung (drei Säulen), **AI & Compliance Readiness**, Kachel **GAI** (Verweis API), **OAMI** (Index, Stufe Niedrig/Mittel/Hoch, Narrativ), Setup, KPIs, Cross-Reg, Reports. |
| 4 | **Board im Workspace** (CTA aus Snapshot) | 2′ / 3′ | **Demo-Board-Report anzeigen**, Readiness-Karte – gleiche Begriffe wie oben. |
| 5 | **Optional 15′** | +3′ | Zweiter Mandant im Portfolio kurz vergleichen (z. B. Industrie vs. Kanzlei-Template). |

### Talking Points

- „Im Portfolio sehen Sie **schnell** Unterschiede zwischen **EU AI Act (Register)** und strukturellem **Readiness** sowie Cross-Reg – ideal zur **Priorisierung**.“  
- „Der **Snapshot** bündelt **Readiness**, den erklärten **GAI** und **OAMI**, KPIs und Lücken – ein Blatt fürs Mandantengespräch.“  
- „Laufzeit-Daten in der Demo sind **synthetisch** – glaubwürdige Story, keine Produktiv-SLA.“

### Typische Berater-Fragen

- „**Wie priorisiere ich zehn Mandanten?**“ → Portfolio-Health + Readiness-Badge + Cross-Reg-Ø.  
- „**Was nehme ich in das Geschäftsführungsgespräch?**“ → Snapshot + Board-Report-PDF/MD-Export (wenn erlaubt).

---

## Zeitvarianten

| Variant | CISO-Pfad | Advisor-Pfad |
|---------|-----------|--------------|
| **10 Min.** | Schritte 1–5 ohne EU-AI-Act-Extra | Schritte 1–4, ein Mandant |
| **15 Min.** | + EU-AI-Act/Playbook oder Governance-Maturity API | + zweiter Mandant Kurzvergleich |

---

## Nach dem Termin

- Fragen notieren, die **außerhalb** des Produktumfangs lagen (Rechtsberatung, individuelle SAP-Architektur).  
- Bei Bedarf **erneut seeden** (idempotent) oder zweiten Demo-Mandanten anlegen (siehe `demo-governance-maturity-flow.md`).

---

## Automatisierter Smoke-Check (CI / Pre-Demo)

Siehe **`tests/test_demo_walkthrough_smoke.py`**: seeded Demo-Mandant, dann GET auf Readiness, Governance Maturity, Board-Reports, High-Risk-Count. Vor Live-Terminal optional:

```bash
pytest tests/test_demo_walkthrough_smoke.py -q
# Optional: OAMI-Subtype-Golden (Index, Explain, Advisor-Fokus aus Fixtures)
pytest tests/test_oami_subtype_explain_golden.py -q
```

---

*Version: 1.0 – intern; keine Kunden-PDF ohne Durchsicht Legal/Compliance.*
