# Wave 19 – Pricing & Sales-Playbook (Stub, Repo-Verankerung)

**Zweck:** Im Repository die **kanonischen SKU-/Paketbezeichnungen** und die **Verkettung zu Wave 20** festhalten. Detaillierte Preise, Bundles, Lead-zu-Paket-Heuristiken und interne Sales-Argumente liegen im **vollständigen Wave-19-Artefakt** (nicht öffentlich im Repo) – dieses Dokument ist der **Stub** für Navigation und Abgleich.

**Vertraulichkeit:** Keine Beträge oder rabattierten Konditionen hier dokumentieren.

---

## Kanonische SKUs (Pakete)

| SKU (Anzeige- & Vertragsname) | Kurzbeschreibung (Fit) | Typische Module / Schwerpunkte (Orientierung) |
| ----------------------------- | ---------------------- | --------------------------------------------- |
| **AI Act Readiness** | Einstieg: KI-Register, Readiness, Board-KPIs, geführte nächste Schritte | AiSystem, Lifecycle/Readiness, Advisor, Board Reports |
| **Governance & Evidence** | Vertiefung: Evidenzketten, GRC-Kontext, wiederholbare Reviews, Audit-Pfade | Evidence, GRC, Register, erweiterte Reports |
| **Enterprise Connectors** | Skalierung: SAP BTP / Enterprise-Landschaft, Mandanten-Portfolio, Integrationsworkshops | Integrationen, Advisor-Portfolio, konzernweite Reports |

*Tiers und Bundle-Kombinationen: nur im vollständigen Wave-19-Playbook; hier nicht duplizieren.*

---

## Bezug zu Wave 20 (öffentliche / halböffentliche Messaging-Rohbauten)

| Wave | Dokument | Inhalt |
| ---- | -------- | ------ |
| **20** | [`wave20-sales-deck-outline.md`](./wave20-sales-deck-outline.md) | Sales-Deck-Struktur, Persona-Module, Visual-Platzhalter |
| **20** | [`wave20-website-messaging-de.md`](./wave20-website-messaging-de.md) | Landingpage-Copy (DE), ohne Preise |
| **20** | [`tone_of_voice_de.md`](./tone_of_voice_de.md) | Tonalität, Do/Don’t, Review-Checkliste |

**Regel:** In Deck, Website und Kampagnen dieselben **drei SKU-Namen** wie oben verwenden; Abweichungen nur nach Produkt-/GTM-Abstimmung und Legal-Review.

---

## Bezug zu Wave 21 (Claims & Disclaimers)

| Wave | Dokument | Inhalt |
| ---- | -------- | ------ |
| **21** | [`compliance-statement-library-de.md`](./compliance-statement-library-de.md) | **Quelle der Wahrheit** für wiederverwendbare, reviewfähige Formulierungen (DE) |
| **21** | [`statements/statements.v1.json`](./statements/statements.v1.json) | Maschinenlesbare Statements inkl. `review_status` |
| **21** | [`statement-review-process.md`](./statement-review-process.md) | Freigabe-Flow und Versionierung |

**Regel:** Claims, Disclaimers und SKU-Claims für externe Kanäle bevorzugt aus der Statement Library übernehmen oder dort zuerst anlegen.

---

## Pflege

- Bei Umbenennung einer SKU: zuerst **Wave-19-Master**, dann **diesen Stub**, **Wave-20-Dateien** und **Statement-Indizes** ([`statement_index_by_sku.json`](./statements/statement_index_by_sku.json)) anpassen.
- Versionierung: im Commit oder im internen Playbook festhalten; dieser Stub braucht keine eigene Versionsnummer, solange das Datum im Changelog/PR genügt.

---

*Stub angelegt für sichtbare Kette Wave 19 → Wave 20 im Repo.*
