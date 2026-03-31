# Governance Maturity Lens – Readiness, GAI & Operational AI (Roadmap)

**ComplianceHub** – Architektur- und Produktreferenz für **zusammengeführte Governance-Reife**: strukturelle Fähigkeit, Nutzung der Plattform und (zukünftig) Laufzeit-Signale aus SAP BTP / SAP AI Core.

**Regulatorischer Kontext:** **EU AI Act** (Post-Market-Monitoring, Art. 72 ff.; kontinuierliche Überwachung bei Hochrisiko), **NIS2** (Erkennung und Steuerung von Vorfällen), **ISO/IEC 42001** (AI-Managementsystem – Steuerung und Verbesserung), **ISO 27001**, **DSGVO** (Datenminimierung in Telemetrie).

**Verwandte Spezifikationen:**

- [`governance-telemetry.md`](./governance-telemetry.md) – Event-Modell, keine PII.  
- [`governance-activity-index.md`](./governance-activity-index.md) – GAI-Formel, Gewichte, Datenmodell-Skizze.  
- [`governance-operational-ai-monitoring.md`](./governance-operational-ai-monitoring.md) – SAP AI Core Events, OAMI, Persistenz, BTP-Integrationsmuster.  
- [`demo-governance-maturity-flow.md`](./demo-governance-maturity-flow.md) – Demo/Pilot: Seeding, Szenarien, 10–15-Minuten-Ablauf.  
- [`demo-board-ready-walkthrough.md`](./demo-board-ready-walkthrough.md) – Internes Skript (CISO/Board vs. Advisor, Talking Points).  
- [`governance-maturity-copy-de.md`](./governance-maturity-copy-de.md) – **Terminologie und Tooltips** (Board-taugliches Deutsch).

---

## 1. Drei Säulen (konzeptionell)

| Säule | Name (Produkt) | Was gemessen wird | Datenquelle (heute / geplant) |
|-------|----------------|-------------------|-------------------------------|
| **A** | **AI & Compliance Readiness Score** | **Strukturelle / inhaltliche Reife**: Setup, Framework-Coverage, KPI-Basis, regulatorische Lücken, Reporting-Reife. | Tenant-Stammdaten, Compliance-Graph, KPI-Register, Board-Reports (ComplianceHub-DB). |
| **B** | **Governance Activity Index (GAI)** | **Aktivierung der Governance-Werkzeuge** in ComplianceHub (Playbook, Cross-Reg, Board, Register, Advisor-Snapshot). | `usage_events`: `workspace_session_started`, `workspace_feature_used` (siehe GAI-Spec). |
| **C** | **Operational AI Monitoring Index (OAMI)** – *Placeholder* | **Laufzeit- und Post-Market-Signale** angebundener KI-Landschaft (Vorfälle, Drift, Deployment-Änderungen), **ohne** Modell-Inhalte. | *Geplant:* SAP BTP / SAP AI Core Events, normalisiert in eigener Pipeline oder erweiterten `usage_events` mit klarem `event_type`. |

**Wichtig:** A, B und C sind **logisch unabhängig** und **ergänzend**:

- Hohe **Readiness**, niedrige **GAI** → Risiko **„Papier-Compliance“**: Prozesse und Daten sind vorbereitet, die Plattform wird kaum zur Steuerung genutzt.  
- Hohe **GAI**, mittlere **Readiness** → intensive Nutzung bei noch offenen strukturellen Lücken (typisch in Transformationsphasen).  
- **OAMI** (später) kann hoch sein, während **GAI** niedrig ist, wenn Monitoring vollautomatisch aus SAP kommt und ComplianceHub nur aggregiert – dann Narrative anpassen („Monitoring datenreich, Governance-Workspace wenig frequentiert“).

---

## 2. Zusammenpräsentation: Readiness Level + Activity Level

### 2.1 Bestehende Readiness-Stufen

Unverändert aus dem Produkt: **Level** `basic` | `managed` | `embedded` (aus Score 0–100 abgeleitet).

### 2.2 GAI-Stufen

Unverändert aus GAI-Spec: **low** | **medium** | **high** (0–39 / 40–69 / 70–100).

### 2.3 Matrix für Stakeholder (ohne neue Mathematik)

Zwei Achsen nebeneinander zeigen:

| | **Strukturelle Reife** (Readiness Level) | **Governance-Aktivität** (GAI Level) |
|---|------------------------------------------|--------------------------------------|
| **Frage** | „Wie weit ist das Programm aufgebaut?“ | „Wird die Steuerungsplattform genutzt?“ |
| **EU AI Act / ISO 42001** | Dokumentation, Risiko, Controls | Operative Nutzung des Managementsystems |
| **NIS2** | Prozesse, KRITIS-KPIs im Register | Sichtbarkeit von Steuerung und Nachverfolgung |

**Narrative Tags** (Beispiele, regelbasiert aus Kombinationen):

| Readiness | GAI | Tag (interner Key) | Kurztext (DE) |
|-----------|-----|---------------------|----------------|
| embedded / managed | low | `structurally_strong_low_usage` | Strukturell stark, geringe Nutzung der Governance-Oberflächen – Prüfen, ob Steuerung im Alltag fehlt. |
| basic | high | `active_early_stage` | Hohe Plattform-Aktivität bei noch grundlegendem Setup – Fokus auf strukturelle Lücken schließen. |
| managed | medium | `balanced` | Ausgewogene Lage – kontinuierliche Verbesserung. |
| *any* | *any* | `review_operational_monitoring` | *Placeholder:* wenn OAMI fehlt oder `not_configured` – Hinweis auf Post-Market-Datenlücke. |

Diese Tags können `GET .../governance-maturity` als `narrative_tag_ids: string[]` liefern (kein Freitext aus Telemetrie).

---

## 3. Readiness Score und GAI: Einfluss und Leitplanken

### 3.1 Empfohlene Produktlinie (Phasen)

| Phase | Verhalten |
|-------|-----------|
| **Jetzt (MVP)** | **Keine** Änderung der numerischen Readiness-Zahl. GAI nur als **zweite Kennzahl** + in **Explain-Prompt** (LLM) und UI. Vermeidet Verwirrung und Regressionen. |
| **Optional (Phase 2)** | **Weicher Modifier** auf den **angezeigten** Score (nicht zwingend persistiert): \(R_{\mathrm{adj}} = \mathrm{clamp}(R + \alpha(G-50), 0, 100)\) mit \(\alpha \le 0{,}15\) (max. ±7,5 PP), wie in GAI-Spec. |
| **Nicht empfohlen** | GAI als eigene **sechste Dimension** im gleichen gewichteten Readiness-Balken ohne klare Trennung – verwischt „Struktur“ und „Nutzung“. |

### 3.2 Guardrails (gegen Gaming und Rauschen)

Bereits in GAI-Spec verankert; hier **explizit für Readiness-Kombination**:

1. **Sättigung / Caps** auf Feature-Counts und Engagement-Ratio vor Eingang in GAI.  
2. **Distinct Days** und **Diversität** (`K`) – reines Wiederholen eines Features bringt ab einem Punkt keinen weiteren GAI-Gewinn.  
3. **Modifier** (falls Phase 2): nur bei **extremen** GAI-Werten diskutierbar (z. B. GAI &lt; 20: Hinweis im Explain, kein harter Abzug ohne Freigabe).  
4. **Anomalie-Flag** (optional): Wenn `feature_used` pro Tag &gt; Schwelle (z. B. &gt; 50 gleiche `feature_name`) → GAI-Berechnung mit **Deckel** oder Markierung `activity_pattern_flag: "suspicious_volume"` für Audit (keine automatische Strafe ohne Policy).

### 3.3 Explain-API (LLM)

Kontextfelder immer getrennt ausgeben:

- `readiness_score`, `readiness_level`, `dimensions_summary` (kurz).  
- `governance_activity_index`, `governance_activity_level`, `window_days`.  
- Satz: *„Die beiden Kennzahlen messen unterschiedliche Dinge: Reife des Programms vs. Nutzung der Governance-Werkzeuge.“*

---

## 4. SAP BTP / SAP AI Core – relevante Signale (Roadmap)

**Detail-Spezifikation:** [`governance-operational-ai-monitoring.md`](./governance-operational-ai-monitoring.md) (kanonisches Event-Schema, Tabellen `ai_runtime_events` / `ai_runtime_incident_summaries`, OAMI-Formel, Ingest-APIs).

Hier nur **Kategorien** und **Einordnung** in die Reife-Linse.

### 4.1 Drei Signalgruppen (Beispiele)

| Signalgruppe | Beispiele (technisch aggregiert) | Relevanz |
|--------------|----------------------------------|----------|
| **Post-Market / Incidents** | Anzahl bestätigter Incidents pro Zeitraum, Schweregrad-Buckets, Zeit bis Eskalation, Verknüpfung mit `ai_system_id` (Register-ID, keine Personen). | EU AI Act Monitoring, NIS2 Melde-/Reaktionskultur. |
| **Laufzeit-KPIs** | Drift-Alarme, erhöhte Fehlerrate, Safety-KPI-Verletzungen (Counts pro System/Fenster). | ISO 42001 Überwachung, Betriebssicherheit. |
| **Deployment-Lebenszyklus** | Neue Modellversionen, Rollbacks, Freigaben (Events ohne Modell-Artefakt-Inhalt). | Nachvollziehbarkeit von Änderungen (AI Act Dokumentationspflichten). |

### 4.2 Einordnung: GAI vs. OAMI

| Aspekt | GAI | OAMI (neu) |
|--------|-----|------------|
| Fokus | Nutzung **ComplianceHub-Governance-UI** und verwandter APIs | **Betrieb** der KI in SAP / angeschlossenen Runtimes |
| Typische Nutzung | CISO/GRC arbeitet in Playbook &amp; Dashboards | Automatisierte Streams aus AI Core / BTP |
| Kann GAI „ersetzen“? | Nein | Ergänzt; optional: **Governance-Reaktion** auf OAMI (z. B. `workspace_feature_used` nach Incident-Review) als *Brücke* in späterer Spec |

**Empfehlung:** **OAMI** als **separater Index** 0–100 mit eigenen Gewichten – ausgearbeitet in [`governance-operational-ai-monitoring.md`](./governance-operational-ai-monitoring.md).

---

## 5. Datenmodell (minimal, kombiniert)

### 5.1 Aggregat-Ansicht (logisch)

Eine Zeile oder JSON-Objekt pro Tenant und Berechnungszeitpunkt:

```text
tenant_id
readiness: { score_0_100, level, dimensions_ref }   # dimensions_ref = Link zu bestehendem Objekt oder eingebettet
gai: { value_0_100, level, window_days, last_computed_at }
oami: { value_0_100, level, window_days, last_computed_at, status: "not_configured" | "partial" | "active" }
narrative_tag_ids: string[]
computed_at_utc
data_freshness: { readiness_source, gai_source, oami_source }  # z. B. timestamps oder "live"
```

**Persistenz-Optionen:**

- **On-the-fly:** Readiness + GAI bei Request berechnen; OAMI-Platzhalter.  
- **Materialisiert:** Tabelle `tenant_governance_maturity_snapshot` (täglich), Spalten JSONB für Teilobjekte – gut für Portfolio-Sortierung.

### 5.2 Datenschutz

- Keine personenbezogenen Felder; nur Mandanten-IDs und technische System-IDs, die bereits im Register stehen.  
- SAP-Events: vor Aggregation **Pseudonymisierung** / Nur-Counts gemäß DPA mit Kunde.

---

## 6. API-Skizze

### 6.1 `GET /api/v1/tenants/{tenant_id}/governance-maturity`

**Auth:** Mandanten-API-Key + RLS wie bestehende Tenant-Routen.

**Response (Pydantic-Skizze):**

```json
{
  "tenant_id": "…",
  "computed_at": "2026-03-25T12:00:00Z",
  "readiness": {
    "score": 72,
    "level": "managed",
    "interpretation": "…"
  },
  "governance_activity": {
    "index": 45,
    "level": "medium",
    "window_days": 90,
    "last_computed_at": "2026-03-25T08:00:00Z"
  },
  "operational_ai_monitoring": {
    "status": "not_configured",
    "index": null,
    "level": null,
    "window_days": null,
    "message": "SAP AI Core / BTP-Anbindung nicht aktiv."
  },
  "narrative_tag_ids": ["structurally_strong_low_usage"],
  "readiness_display_score": 72,
  "readiness_score_adjustment_note": null
}
```

- `readiness_display_score`: initial identisch zu `readiness.score`; bei Phase-2-Modifier hier der angezeigte Wert, `readiness.score` Rohwert optional als `readiness.structural_score`.  
- `narrative_tag_ids`: maschinenlesbar; UI mappt auf kurze DE-Texte.

### 6.2 Advisor-Variante

`GET /api/v1/advisors/{advisor_id}/tenants/{tenant_id}/governance-maturity` – gleiche Payload nach Link-Prüfung Advisor↔Tenant.

---

## 7. Board & Advisor UI

### 7.1 Board Readiness Card (Tenant)

- **Zwei Kennzahlen** nebeneinander: **Readiness** (groß) + **GAI** (kleiner, „letzte 90 Tage“).  
- **Ein Satz** unterhalb aus `narrative_tag_ids` (vordefinierte Texte).  
- Link „Mehr zur Einordnung“ → Hilfe/Doc mit EU AI Act / kontinuierliche Überwachung.

### 7.2 Advisor Portfolio

- Spalten: **Readiness**, **GAI**, *(später)* **OAMI** oder **Monitoring: aktiv/fehlt**.  
- Sortierbar nach jeder Spalte; Filter: „GAI &lt; 40 &amp; Readiness ≥ 60“ (Papier-Compliance-Filter).  
- Tooltip: kurze Definitionen (nicht technisch: „Struktur“ vs. „Nutzung“).

### 7.3 Advisor Governance Snapshot

- Abschnitt **„Governance-Reife auf einen Blick“**: drei Zeilen oder Mini-Bars (Readiness / GAI / OAMI-Status).  
- **Narrativ (Template):**  
  - *„Hohe strukturelle Reife (Managed), mittlere Governance-Aktivität; operatives KI-Monitoring aus SAP ist noch nicht angebunden – Post-Market-Signale ggf. nur manuell.“*

Wortlaut immer **konservativ** (keine Rechtsberatung), Verweis auf kontinuierliche Überwachung gemäß Rollout EU AI Act / interne Policy.

---

## 8. Verfügbarkeit: Jetzt vs. Roadmap

| Komponente | Status |
|------------|--------|
| Readiness Score + Level | **Live** (Feature-Flag beachten). |
| GAI | **Spec + geplante Implementierung** (siehe `governance-activity-index.md`). |
| `GET .../governance-maturity` | **Entwurf** – in diesem Dokument. |
| OAMI / SAP AI Core | **Spezifikation** in [`governance-operational-ai-monitoring.md`](./governance-operational-ai-monitoring.md); Implementierung Roadmap. |
| Readiness numerischer Modifier durch GAI | **Optional Phase 2** – Standard: nur Explain + UI-Zweispaltigkeit. |

---

## 9. Nächste Schritte (Engineering)

1. Implementierung `compute_governance_activity_index` + ggf. `tenant_governance_activity_index`.  
2. Endpoint `governance-maturity` mit `oami.status = not_configured`.  
3. Board Card + Advisor-Spalten + narrative Tag-Map (i18n).  
4. SAP AI Core Ingest + OAMI gemäß [`governance-operational-ai-monitoring.md`](./governance-operational-ai-monitoring.md); `governance-maturity`-API um echte `operational_ai_monitoring`-Werte erweitern.

---

*Version: 1.0 – Governance Maturity Lens; bei Produktentscheidungen Abweichungen dokumentieren.*
