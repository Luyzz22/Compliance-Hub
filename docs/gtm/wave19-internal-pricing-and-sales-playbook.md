# Wave 19 — Internes Pricing & Sales Playbook (Entwurf)

> **Status:** Arbeitsdokument für Produkt, Vertrieb und Marketing.  
> **Pflicht vor Go-Live:** Abstimmung mit Legal und Finance; keine verbindlichen Preise oder Zusicherungen aus diesem Dokument.

---

## 1. Zweck

Dieses Playbook verbindet **technische Capabilities** (Tiers, Bundles, SKUs) mit **Vertriebslogik**:

- relative Preis- und Lizenzlogik (ohne EUR),
- Argumentation pro Segment,
- Demo-Empfehlungen,
- Qualifizierungsfragen und Paket-Routing.

---

## 2. Produktüberblick (Reminder)

| Tier | Typische SKU | Bundles (Kurz) |
|------|----------------|----------------|
| **Starter** | AI Act Readiness | AI Act Readiness |
| **Professional** | AI Governance & Evidence | Readiness + Governance & Evidence |
| **Enterprise** | + Enterprise Connectors | alle Bundles inkl. Integrationen |

**SKUs (Kundensprache):**

- `SKU_AI_ACT_STARTER` — AI Act Readiness  
- `SKU_GOVERNANCE_PRO` — AI Governance & Evidence Suite  
- `SKU_ENTERPRISE_CONNECT` — Enterprise Connectors (SAP/DATEV)

Technische Details: `app/product/offerings.py`, `app/product/models.py`, Wave-17/18-Dokumentation unter `docs/architecture/`.

---

## 3. Relative Preis-Positionierung

**Quelle der Wahrheit:** `docs/gtm/pricing_internal.yaml`

**Prinzipien:**

- **1x** = Referenz (`SKU_AI_ACT_STARTER`), qualitative Bänder (`low_to_mid`, `mid_to_high`, `high`).
- **Governance-Pro** typisch **2x–4x** relativ, abhängig von Segment (Kanzlei oft höhere Mandanten-Streuung).
- **Enterprise Connectors** = **Premium-Add-on** (`+1x` bis `+4x` relativ zur Governance-Basis), nicht als Alleinstellungsmerkmal ohne Governance-Kern.

**Abrechnungsdimensionen (Hinweise, nicht Vertragstext):**

| Dimension | Wann relevant |
|-----------|----------------|
| Pro Tenant / Mandant | Mandantenfähige Kanzlei, Konzern-Tenants |
| Pro KI-System (Staffel) | großes Inventar, faire Verteilung |
| Setup + Betrieb (Connectors) | SAP BTP, DATEV-Pfade, Projektstart |

Keine Euro-Beträge in Repo-Konfiguration — nur relative und qualitative Angaben.

---

## 4. Vertriebsargumente pro SKU & Segment

**Quelle:** `docs/gtm/sales_arguments_by_segment.json`

Kurzfassung:

- **AI Act Readiness + KMU:** Schneller Überblick, Evidence für interne Audits, geringer Einstieg, später Upgrade.  
- **AI Act Readiness + Kanzlei:** Einstiegs-Honorar-Pakete, Standardisierung, Pfad zu Dossiers.  
- **Governance & Evidence + Kanzlei:** Board Reports, Dossiers, Mandanten-Skalierung, DATEV-Nähe.  
- **Governance & Evidence + Industrie:** Inventar + NIS2/ISO-42001-Bezug, eine Quelle für Security und Fachbereich.  
- **Enterprise Connectors + SAP:** Event Mesh, weniger Medienbruch, Konzern-Skalierung — immer mit Governance-Basis.

Formulierung in Gesprächen: **„unterstützt bei Readiness / Governance / Nachweisen“** — nie **„garantiert compliant“**.

---

## 5. In-App-Hinweise (ohne Preise)

Die UI nutzt deutsche **Value Hints** und **Upgrade-Hinweise** (`app/product/copy_de.py`):

- Zuordnung zu **Paketnamen** und **Tier** (z. B. „Professional-Tier“, „Zusatzpaket Enterprise Connectors“).
- **Keine** Euro-Preise, **keine** Rabattversprechen.

API für gefilterte Hints: `GET /api/internal/product/value-hints` (Wave 18).

---

## 6. Demo-Empfehlungen pro Segment

| Segment | Demo-Profil (intern) | Fokus in 20–30 Min |
|---------|----------------------|---------------------|
| Industrie-Mittelstand | `industrie_mittelstand_demo` | Inventar → GRC → Evidence → Board Report |
| Kanzlei | `kanzlei_demo` | Mandanten-Systeme → Advisor → Report → Dossier |
| Enterprise SAP | `sap_enterprise_demo` | Inventar + Integrations-/Jobs-Sicht + Governance |

Ausführliche Skripte: `docs/architecture/wave18-offerings-and-gtm-alignment.md`.

---

## 7. Lead-Qualifizierung & Paket-Mapping

**Quelle:** `docs/gtm/lead_to_package_heuristics.json`

**Beispielfragen:**

1. ISMS / ISO 27001 und geplantes ISO-42001-AI-MS?  
2. DATEV als Leit-system für Mandanten?  
3. Hochrisiko-KI (Scoring, Personal, Biometrie)?  
4. SAP S/4 oder BTP / Event-getriebene Architektur?  
5. Wie viele Mandanten bzw. Einheiten?  
6. Audit- oder Meldedruck in den nächsten 12 Monaten?

**Heuristik (vereinfacht):**

| Signal | Tendenz |
|--------|---------|
| Wenig KI, kein Integrationszwang | Starter / AI Act Readiness |
| DATEV, Mandanten-Reports, Dossiers | Pro / Governance & Evidence |
| Viele Systeme, NIS2, CISO involviert | Pro / Governance & Evidence |
| SAP Events, konzernweite Anbindung | Enterprise + Connectors (mit Pro-Basis) |

CRM/Playbooks können die JSON-Struktur 1:1 importieren oder in Notion/HubSpot übernehmen.

---

## 8. Sales-Deck-Bausteine

**Quelle:** `docs/gtm/sales_enablement_cheat_sheet.md`

Struktur pro Track: Problem → Lösung → Module → Pakete → Use-Cases → Nächste Schritte.

---

## 9. Nächste Schritte (Produkt & GTM)

1. Finance: EUR-Bänder und Staffeln festlegen (außerhalb dieses Repos).  
2. Legal: Claims-Review Website und Angebots-PDFs.  
3. Marketing: Website-Segmente (Industrie / Kanzlei / SAP) an Cheat Sheet anbinden.  
4. CRM: Qualifizierungsfelder aus `lead_to_package_heuristics.json` mappen.

---

## 10. Dateiindex Wave 19

| Datei | Inhalt |
|-------|--------|
| `docs/gtm/pricing_internal.yaml` | SKU × Segment × relative Preis × Billing-Hinweise |
| `docs/gtm/sales_arguments_by_segment.json` | 3–5 Argumente je SKU & Segment |
| `docs/gtm/lead_to_package_heuristics.json` | Fragen & Routing-Heuristiken |
| `docs/gtm/sales_enablement_cheat_sheet.md` | Deck-Stichpunkte DE |
| `docs/gtm/wave19-internal-pricing-and-sales-playbook.md` | dieses Dokument |
| `app/product/copy_de.py` | UI-Texte mit Tier-/Paket-Positionierung (ohne Preise) |
