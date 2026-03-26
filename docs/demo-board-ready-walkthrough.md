# Internes Demo-Skript: Board- & Berater-Walkthrough (ComplianceHub)

Zielgruppe: **Sales**, **Customer Success**, **Berater-Partner** – reproduzierbare Führung für **CISO/Board** (ein Mandant) und **Advisor** (Portfolio + Deep Dive).  
Technische Provisionierung: [`demo-governance-maturity-flow.md`](./demo-governance-maturity-flow.md).

**Kernbotschaft in drei Säulen**

| Säule | Produktname | Was Sie sagen (Kurz) |
|-------|-------------|----------------------|
| **Struktur** | AI & Compliance **Readiness** | „Wo stehen wir mit EU AI Act, ISO 42001/27001 und Nachweisen – unabhängig vom Tagesgeschäft?“ |
| **Nutzung** | **GAI** (Governance Activity Index) | „Nutzen wir ComplianceHub wirklich für Steuerung – Playbook, Cross-Reg, Board?“ |
| **Betrieb** | **OAMI** (Operational AI Monitoring) | „Sehen wir Laufzeit-Signale und Vorfälle – Anknüpfung an NIS2-Incident-Themen und Post-Market-Monitoring?“ |

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
| 5 | **AI Compliance Board-Report** (`/board/ai-compliance-report`) | 2′ / 3′ | **Readiness-Karte** (strukturell); vorgefertigter **Demo-Board-Report**; OAMI-Auszug im Report wo vorhanden. |
| 6 | **Optional 15′** | +3′ | EU-AI-Act-Readiness-Seite, Playbook-Phase, oder **Governance-Maturity** per API/Docs erwähnen (Readiness + GAI + OAMI in einem JSON). |

### Talking Points (Auszug)

- „Der **Readiness Score** bündelt Setup, Coverage, KPIs, Gaps und Reporting – das ist unsere **Board-taugliche** Einordnung zur **EU AI Act**-Reife, nicht die juristische Klassifikation.“  
- „**GAI** messen wir aus der **Nutzung** von Playbook, Cross-Reg und Board – das unterscheidet **Papier-Compliance** von aktiver Governance.“  
- „**OAMI** steht für **operative Signale** (Vorfälle, Drift, Deployments) – das stützt **Post-Market-Monitoring** und das Gespräch mit **NIS2**-Incident-Prozessen, ohne dass wir hier Meldepflichten automatisch qualifizieren.“

### Typische Board-/CISO-Fragen (diese Demo adressiert)

- „**Wie sehen wir unseren EU-AI-Act-Reifegrad** über eine Zahl hinaus?“ → Readiness-Dimensionen + Cross-Reg-Gaps.  
- „**Wie koppeln wir NIS2-Incidents an KI-Governance?**“ → NIS2-KPIs + Runtime-/OAMI-Narrativ + Actions im Register.  
- „**Was fehlt uns noch vor 2026?**“ → Offene Actions, rote/amber Gaps, Board-Report-Empfehlungen (Demo-Text).

---

## B) Advisor – Portfolio + ein Mandant (~10 oder ~15 Min.)

### Screen-Folge

| # | Screen | Dauer (10′ / 15′) | Was Sie zeigen |
|---|--------|-------------------|----------------|
| 1 | **Advisor-Portfolio** (`/advisor`) | 2′ / 3′ | Vergleich Mandanten: EU-AI-Act-Readiness, **Readiness-Badge** (strukturell), Cross-Reg-Ø, High-Risk-Anzahl. |
| 2 | **Spalten-Tooltips** | 0.5′ | Kurz: Readiness = fünf Dimensionen; Cross-Reg = Framework-Coverage. |
| 3 | **Governance-Snapshot** (Mandant wählen) | 4′ / 6′ | Mandantenstammdaten, **Readiness**, Setup, AI-Systeme, KPIs, Cross-Reg-Tabelle, **OAMI** (Index, Level, Kurznarrativ), Reports. |
| 4 | **Board im Workspace** (CTA aus Snapshot) | 2′ / 3′ | Gleicher Mandant: **Demo-Board-Report anzeigen**, Readiness-Karte erneut – roter Faden. |
| 5 | **Optional 15′** | +3′ | Zweiter Mandant im Portfolio kurz vergleichen (z. B. Industrie vs. Kanzlei-Template). |

### Talking Points

- „Im Portfolio sehen Sie **schnell**, wo Mandanten in **Readiness** und **Cross-Reg** auseinanderlaufen – ideal für **Priorisierung**.“  
- „Der **Snapshot** ist Ihr **einziges Blatt** vor dem Mandantentermin: Register, KPIs, Lücken, **operative KI-Überwachung** (OAMI).“  
- „Alles, was wie **Live-Betrieb** aussieht, ist in der Demo **synthetisch** – für Vertrauen in die **Story**, nicht für echte SLAs.“

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
```

---

*Version: 1.0 – intern; keine Kunden-PDF ohne Durchsicht Legal/Compliance.*
