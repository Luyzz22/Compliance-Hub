# Governance-Maturity: deutsche Produktterminologie (ComplianceHub)

**Zielgruppe:** CISO, Vorstand, Aufsichtsrat, GRC-/ISMS-Berater (DACH).  
**Implementierung:** zentrale Konstanten in `frontend/src/lib/governanceMaturityDeCopy.ts` – diese Datei ist die **inhaltliche Referenz**; bei Abweichungen zuerst dort anpassen, dann UI prüfen.

---

## 1. Festgelegte Begriffe

| Begriff | Offizielle UI-/Produktbezeichnung | Kurz erklärt |
|---------|-------------------------------------|--------------|
| Strukturelle Reife | **AI & Compliance Readiness** | Aufbau, Framework-Abdeckung, KPI-Register, Lücken, Board-Reporting – EU AI Act (u. a. Art. 9–15), ISO/IEC 42001, ISO/IEC 27001, NIS2-Anschluss. |
| Nutzung der Plattform | **Governance-Aktivitätsindex (GAI)** | Ob Playbook, Cross-Regulation, Board und Register **tatsächlich genutzt** werden. |
| Operative Signale | **Operativer KI-Monitoring-Index (OAMI)** | Technische Laufzeit-Signale (Vorfälle, Schwellen, Deployments) – Post-Market-Monitoring, NIS2-Incident-Bezug; keine automatische Melde-Entscheidung. |

**Reifegrade (Readiness, API `basic` / `managed` / `embedded`):** **Basis** · **Etabliert** · **Integriert**  
**Stufen bei Indexwerten GAI/OAMI (`low` / `medium` / `high`):** **Niedrig** · **Mittel** · **Hoch**

**Portfolio-Spalte „EU AI Act (Register)“:** heuristischer Registerüberblick – **nicht** identisch mit dem strukturellen Readiness-Score.

---

## 2. Tooltips und Regulierungs-Footer (Auszug)

| Kennzahl | C-Level-Tooltip (ein Satz) | Regulierungs-Footer (kurz) |
|----------|----------------------------|----------------------------|
| Readiness | Siehe `READINESS_TOOLTIP_C_LEVEL` in TS. | EU AI Act Art. 9–15, ISO/IEC 42001, ISO/IEC 27001; NIS2 über Governance/Incident. |
| GAI | Siehe `GAI_TOOLTIP_C_LEVEL`. | Nachweisbare Steuerungsaktivität; kein Ersatz für Prüfung. |
| OAMI | Siehe `OAMI_TOOLTIP_C_LEVEL`. | EU AI Act Post-Market (Art. 72), NIS2 Incident. |

Ausführliche Sätze für Berater-Detail: `READINESS_ADVISOR_DETAIL_EXTRA`, `GAI_ADVISOR_DETAIL_EXTRA`, `OAMI_ADVISOR_DETAIL_EXTRA` im TS.

---

## 3. Banner und Demohinweise

- **Board-Report (read-only):** `DEMO_BANNER_BOARD_REPORT`
- **Readiness-Karte (Demo):** `DEMO_HINT_READINESS_CARD`
- **Portfolio-Hinweis:** `PORTFOLIO_GOVERNANCE_MATURITY_NOTE`
- **Nach Demo-Seed:** `DEMO_SEED_SUCCESS_GOVERNANCE_NOTE`

---

## 4. Walkthrough-Skript

Begriffe im gesprochenen Text: [`demo-board-ready-walkthrough.md`](./demo-board-ready-walkthrough.md) – an diese Tabelle anbinden.

---

*Version 1.0 – Redaktion/Produkt; keine Rechtsberatung.*
