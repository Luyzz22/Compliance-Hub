# Compliance Statement Library (DE) – Wave 21

**Zweck:** Eine interne, **reviewfähige** Schicht genehmigter Formulierungen für Website, Sales-Decks, In-App-Texte, One-Pager und Outbound – konsistent mit SKUs und **ohne Überversprechen** (keine Konformitäts- oder Zertifizierungsgarantien).

**Quelle der Wahrheit für Claims und Disclaimers:** [`statements/statements.v1.json`](./statements/statements.v1.json).  
Ergänzend: [Tone of Voice](./tone_of_voice_de.md), [SKU-Stub Wave 19](./wave19-pricing-sales-playbook-stub.md), [SKU-Kanal-Mapping](./statements/sku_channel_family_mapping.md), [Review-Prozess](./statement-review-process.md).

---

## 1. Datenmodell (Felder pro Statement)

| Feld | Typ / Werte | Beschreibung |
| ---- | ----------- | ------------ |
| `statement_id` | string | Eindeutig, stabil; siehe Benennung im Review-Doc |
| `channels` | array | `website`, `sales_deck`, `in_app`, `one_pager`, `email` |
| `audience` | enum | `industrie_mittelstand`, `kanzlei`, `enterprise_sap`, `generic` |
| `sku` | enum | `AI Act Readiness`, `Governance & Evidence`, `Enterprise Connectors`, `generic` |
| `regulation_context` | enum | `eu_ai_act`, `nis2`, `iso42001`, `gobd`, `generic` |
| `language` | string | `de` |
| `tone_variant` | enum | `short`, `medium`, `formal` |
| `family` | string | Logische Gruppe (z. B. `product_claim_safe`, `disclaimer`) – siehe Mapping-Doc |
| `approved_text` | string | **Kanonicaler** deutscher Text |
| `disallowed_alternatives` | array | Beispiele für **verbotene** oder riskante Formulierungen |
| `review_status` | enum | `draft`, `approved`, `needs_legal_review` |
| `owner` | string (optional) | Rolle/Team |
| `last_reviewed_at` | string (optional, ISO-Datum) | Letzte Freigabe |
| `notes` | string (optional) | Kontext für Reviewer |
| `deprecated` | boolean (optional) | Standard `false` |
| `supersedes` | string oder null | Vorherige ID, falls Ersatzfolge |

Neue optionale Felder können im Schema ergänzt werden; Version in `schema_version` der JSON-Datei anheben.

---

## 2. Dateien im Ordner `docs/gtm/statements/`

| Datei | Inhalt |
| ----- | ------ |
| [`statements.v1.json`](./statements/statements.v1.json) | Alle Statements |
| [`statement_index_by_sku.json`](./statements/statement_index_by_sku.json) | Lookup `statement_id` nach SKU |
| [`statement_index_by_channel.json`](./statements/statement_index_by_channel.json) | Lookup nach Kanal |
| [`sku_channel_family_mapping.md`](./statements/sku_channel_family_mapping.md) | Welche Familien/Tonlagen pro SKU und Kanal |

---

## 3. DO / DON’T für Copywriting und Produkt (Kurzfassung)

### DO (verwenden)

- **Readiness**, **Governance**, **Nachweise**, **strukturierte Dokumentation**, **Audit-Trail**, **Nachvollziehbarkeit**
- **Unterstützung bei**, **Vorbereitung**, **im Kontext von**, **im Abgleich mit Steuerberater / DSB / Mandant**
- **Mandantenfähig**, **Pilot**, **Projekt**, **Schnittstellen klären**

### DON’T (vermeiden, sofern nicht belegt und legal freigegeben)

- **Garantie**, **vollautomatisch konform**, **rechtsverbindlich ohne Prüfung**, **zertifiziert** (Produkt/Integration)
- **Vollständige Erfüllung** von NIS2 / AI Act / GoBD **ohne** Einschränkung
- **Angst-Claims** (Bußgelder, „letzte Chance“) ohne Legal-Freigabe
- **Offizielle SAP-/DATEV-Zertifizierung** behaupten

---

## 4. Vorher / Nachher (Beispiele für Teams)

| Schlecht (vermeiden) | Besser (Richtung Statement Library) |
| -------------------- | ------------------------------------- |
| Garantiert AI-Act-konform. | Unterstützung bei AI-Act-Readiness und Dokumentation – abhängig von Risikoklasse. (`CSL-DE-CORE-001`) |
| Automatisch rechtskonform. | Keine Rechtsberatung; unterstützende Einordnung und Dokumentationshilfen. (`CSL-DE-DIS-001`) |
| Vollständige NIS2-Erfüllung ohne manuelle Prüfung. | NIS2-Themen in Übersichten sichtbar machen – Abgleich mit Meldepflicht und ISMS. (`CSL-DE-NIS2-001`) |
| GoBD-konform out of the box. | GoBD-relevante Dokumentation strukturiert vorbereiten, mit Mandant abstimmen. (`CSL-DE-GoBD-001`) |
| ISO-42001-Zertifikat inklusive. | Evidenz für KI-Managementsystem und Reviews bündeln; Zertifizierung durch Ihren Auditor. (`CSL-DE-SKU-GEV-001`) |
| Zertifizierte SAP-Integration. | Vorbereitung technischer Anbindung; Umfang im Projekt definieren. (`CSL-DE-SKU-ENT-001`) |
| Offizieller DATEV-Connector. | DATEV-taugliche Exportstrukturen können vorbereitet werden – keine Produktzertifizierung. (`CSL-DE-SKU-ENT-002`) |
| Ohne Upgrade nicht compliant. | Funktion in Ihrem Paket nicht enthalten; erweiterte Möglichkeiten mit höherem Paket. (`CSL-DE-UI-001`) |
| Revisionssicher ohne Rückfragen. | Prüfbare Audit-Trails; Bewertung durch Prüfer bleibt bei Stakeholdern. (`CSL-DE-SKU-GEV-002` Richtung) |
| Die einzige Software, die Sie brauchen. | Einheitliche Datenbasis für Vorstand, Fachbereich und Berater. (`CSL-DE-SD-PROOF-001`) |
| Sichern Sie vollständige Compliance jetzt. | Pilotfokus ohne Konformitätsversprechen; klare nächste Schritte. (`CSL-DE-EMAIL-001`) |
| SAP-Anbindung in Sekunden. | Enterprise-Anbindungen erfordern Paket und Onboarding-Klärung. (`CSL-DE-UI-002`) |

---

## 5. Erwartung an künftige Arbeit (Deck, Website, In-App)

- Neue oder geänderte **öffentliche** Claims: zuerst in `statements.v1.json` als Entwurf anlegen oder bestehende ID wiederverwenden.
- **Freigabe** gemäß [`statement-review-process.md`](./statement-review-process.md).
- Wave-20-Markdowns sind **Rohbau**; bei Überarbeitung Texte an **IDs** aus dieser Library angleichen.

---

## 6. Bezug zu Wave 19 / 20

| Dokument | Rolle |
| -------- | ----- |
| [Wave 19 Stub](./wave19-pricing-sales-playbook-stub.md) | SKU-Namen |
| [Wave 20 Sales Deck](./wave20-sales-deck-outline.md) | Struktur; Bullets durch Library-IDs absichern |
| [Wave 20 Website](./wave20-website-messaging-de.md) | Copy; Hero/Subline an `CSL-DE-WEB-*` und CORE-Statements ausrichten |
| [Tone of Voice](./tone_of_voice_de.md) | Stil; Library liefert **kanonische** Sätze |

---

*Wave 21 – interne Compliance Statement Library. Keine Rechtsberatung; finale Texte mit Legal/Compliance abstimmen.*
