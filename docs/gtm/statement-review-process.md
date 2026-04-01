# Statement Library – Review- und Versionsprozess (Wave 21)

**Gilt für:** [`docs/gtm/statements/statements.v1.json`](./statements/statements.v1.json) und alle abgeleiteten GTM-/Produkttexte, die Claims oder Disclaimers betreffen.

---

## 1. Statusmodell (`review_status`)

| Status | Bedeutung | Verwendung in Produktion |
| ------ | --------- | ------------------------ |
| `draft` | In Arbeit | Nur intern / nicht kundenöffentlich ohne Kennzeichnung |
| `needs_legal_review` | Produkt hat geprüft, Legal offen | Nicht für externe finale Copy ohne Freigabe |
| `approved` | Freigegeben | Website, Decks, In-App, Outbound gemäß Kanalregeln |

Ergänzend im Datensatz (optional):

- `deprecated: true` – Text nicht mehr für neue Assets verwenden; bestehende Referenzen migrieren.
- `supersedes` (auf dem **neuen** Datensatz): vorherige `statement_id`, die ersetzt wird; alter Datensatz zusätzlich `deprecated: true` setzen.

---

## 2. Leichtgewichtiger Workflow

```text
Entwurf (draft)
    → Produkt / Product Marketing Review (Konsistenz, SKU, Kanal, Tone)
        → bei regulatorischer oder integrationsnaher Copy: Legal / Compliance Review
            → approved
```

**Trigger für Legal/Compliance (mindestens):**

- Neue oder geänderte `family`-Werte `disclaimer`, `integration_careful`, `regulatory_context`
- Erwähnung von SAP, DATEV, GoBD, NIS2-Meldepflicht, ISO-Zertifizierung
- Jede Formulierung, die wie eine Garantie oder Zertifizierung wirken könnte

---

## 3. Benennung (`statement_id`)

**Format:** `CSL-DE-<FAMILY-KURZ>-<nnn>` (dreistellig fortlaufend pro Familie) oder fachliche Präfixe wie `CSL-DE-SKU-AAR-001`.

- **Keine** Wiederverwendung einer ID nach inhaltlicher Änderung: lieber neue ID und alte mit `deprecated: true` + `replaced_by: "CSL-DE-…"`.
- Groß-/Kleinschreibung der SKU-Strings im Feld `sku` exakt wie im [Wave-19-Stub](./wave19-pricing-sales-playbook-stub.md).

---

## 4. Versionierung der Datei

- **`statements.v1.json`:** Major-Änderungen am Schema oder große Reorganisation → neue Datei `statements.v2.json`; v1 bleibt bis Migration abgeschlossen.
- **Kleine Ergänzungen** (neue IDs): v1 erweitern; im Git-Commit/PR beschreiben.
- **Indizes** [`statement_index_by_sku.json`](./statements/statement_index_by_sku.json) und [`statement_index_by_channel.json`](./statements/statement_index_by_channel.json) bei jeder ID-Änderung anpassen.

---

## 5. Downstream-Referenzen

- **Website / Deck / In-App:** Wo möglich `statement_id` in Kommentaren, Content-CMS-Metadaten oder internen Specs hinterlegen (z. B. „Hero: CSL-DE-WEB-HERO-001“).
- **Markdown-Rohbauten** ([`wave20-website-messaging-de.md`](./wave20-website-messaging-de.md), [`wave20-sales-deck-outline.md`](./wave20-sales-deck-outline.md)): Bei Überarbeitung auf passende `statement_id`s ausrichten oder in PR vermerken.
- **Deprecated:** Assets, die alte IDs nutzen, innerhalb eines Quartals oder vor nächstem externen Launch aktualisieren.

---

## 6. Verantwortlichkeiten (Rollen, nicht Personennamen)

| Rolle | Aufgabe |
| ----- | ------- |
| Product Marketing | Neue Statements vorschlagen, `owner` setzen, Indizes/Mapping pflegen |
| Product / PM | inhaltliche Richtigkeit, SKU- und Kanal-Fit |
| Legal / Compliance | Freigabe `approved`, Formulierung sensibler Claims |
| Engineering (optional) | Einbindung von IDs in Config/Copy-Pipelines, wenn eingeführt |

---

*Prozess ist bewusst schlank; bei regulatorischen Vorfällen oder Partner-Anfragen (SAP/DATEV) vorab Legal einschalten.*
