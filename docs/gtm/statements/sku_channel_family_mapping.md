# Statement-Families × SKU × Kanal (Wave 21)

**Quelle der Wahrheit für Texte:** [`statements.v1.json`](./statements.v1.json) + [`compliance-statement-library-de.md`](../compliance-statement-library-de.md).  
**Indizes:** [`statement_index_by_sku.json`](./statement_index_by_sku.json), [`statement_index_by_channel.json`](./statement_index_by_channel.json).

Dieses Dokument beschreibt, **welche Familien** pro SKU und Kanal genutzt werden dürfen und **welche Tonvarianten** typisch passen. Konkrete Sätze immer per `statement_id` aus der JSON-Bibliothek übernehmen oder nach Review ergänzen.

---

## Familien (Kurzüberblick)

| `family` (im JSON)        | Zweck |
| ------------------------- | ----- |
| `product_claim_safe`      | Kern-Nutzen ohne Konformitätsgarantie |
| `disclaimer`              | Rechts-/Produkt-Disclaimers |
| `sku_value_prop`          | Paketbeschreibung |
| `sales_proof_point`       | Deck-Bullet, rationaler Nutzen |
| `integration_careful`     | SAP/DATEV/Enterprise ohne Zertifizierungsimplikation |
| `regulatory_context`      | NIS2, GoBD, EU AI Act als Kontext |
| `feature_not_enabled`     | Upgrade / gesperrte Funktion |
| `website_headline_support`| Hero, Subline |
| `outbound_safe`           | E-Mail, seriös, kein Fear-Marketing |

---

## AI Act Readiness

| Kanal        | Empfohlene Familien | Tonvariante (typisch) | Hinweis |
| ------------ | ------------------- | --------------------- | ------- |
| Website Hero | `website_headline_support`, `product_claim_safe` | short, medium | Zusätzlich generische `disclaimer` kurz prüfen |
| Website Paketsektion | `sku_value_prop` | short, medium | `CSL-DE-SKU-AAR-001` |
| Sales Deck   | `sku_value_prop`, `sales_proof_point`, `product_claim_safe` | medium, formal | EU AI Act nur kontextualisiert |
| In-App (Tooltip/Upgrade) | `feature_not_enabled`, `product_claim_safe` | short | Keine Compliance-Androhung |
| One-Pager    | `sku_value_prop`, `sales_proof_point` | medium | |
| E-Mail       | `product_claim_safe`, `outbound_safe` | short | |

---

## Governance & Evidence

| Kanal        | Empfohlene Familien | Tonvariante (typisch) | Hinweis |
| ------------ | ------------------- | --------------------- | ------- |
| Website      | `sku_value_prop`, `product_claim_safe` | medium | ISO als **Kontext**, kein Zertifizierungsversprechen |
| Sales Deck   | `sku_value_prop`, `sales_proof_point` | medium, formal | `CSL-DE-SKU-GEV-002` nach Legal-Freigabe |
| In-App       | `feature_not_enabled`, `disclaimer` (Footer) | short | |
| One-Pager    | `sku_value_prop`, `product_claim_safe` | medium | |
| E-Mail       | `sales_proof_point`, `outbound_safe` | short, medium | |

---

## Enterprise Connectors

| Kanal        | Empfohlene Familien | Tonvariante (typisch) | Hinweis |
| ------------ | ------------------- | --------------------- | ------- |
| Website      | `sku_value_prop`, `integration_careful` | medium | **Keine** Formulierungen „zertifiziert“, „offiziell freigegeben“ |
| Sales Deck   | `integration_careful`, `sales_proof_point` | medium, formal | SAP BTP / Event-Kontext = **Integrationsbereitschaft**, nicht Zertifikat |
| In-App       | `feature_not_enabled` | short | `CSL-DE-UI-002` |
| One-Pager    | `integration_careful`, `sku_value_prop` | medium | DATEV: **Exportstruktur**, keine DATEV-Produktbehauptung |
| E-Mail       | `integration_careful`, `outbound_safe` | short, medium | |

**Pflicht:** Bei SAP/DATEV immer klären, dass Schnittstellen **projektabhängig** sind und keine Partner-Zertifizierung impliziert wird.

---

## Generisch (alle SKUs / Thought Leadership)

Überall zulässig, wo es passt:

- `product_claim_safe`, `disclaimer`, `regulatory_context` (NIS2, GoBD), `website_headline_support` (nur Website).

Kanal-spezifisch:

- **Sales Deck:** `sales_proof_point`, `CSL-DE-SD-PROOF-001`
- **E-Mail:** `outbound_safe`, `CSL-DE-EMAIL-001`

---

## Audience-Filter (optional)

| `audience` im JSON   | Typische Einsetzbarkeit |
| -------------------- | ----------------------- |
| `generic`            | Standard |
| `industrie_mittelstand` | Deck, One-Pager, NIS2-Kontext |
| `kanzlei`            | GoBD, Mandanten-Dossiers, DATEV-vorsichtige Texte |
| `enterprise_sap`     | `integration_careful`, Enterprise-SKU |

---

*Bei neuen Familien oder Kanälen: Mapping und Indizes mitziehen; Review siehe [`statement-review-process.md`](../statement-review-process.md).*
