# Marktreife-Review DACH — 2026-08-09

Enterprise- und Regulatorik-Readiness-Review von ComplyWithAI / Compliance Hub für den
deutschen und DACH-Markt. Grundlage: vollständige statische Analyse des Repositorys
(409 Python-Module, 71.474 LOC, 103 ORM-Tabellen, 480 TypeScript-Dateien).

## Einstieg

**Wenig Zeit?** → [`00-executive-readiness-verdict.md`](00-executive-readiness-verdict.md)
— Scorecard, Blocker, Launch-Entscheid, Empfehlung für die nächsten 14 Tage.

**Vertriebsgespräch vorzubereiten?** →
[`13-security-questionnaire-pack.md`](13-security-questionnaire-pack.md)

**Text zu schreiben?** → [`10-messaging-redlines.md`](10-messaging-redlines.md)
und [`02-claim-vs-proof-matrix.md`](02-claim-vs-proof-matrix.md)

**Zu entwickeln?** → [`07-refactoring-roadmap.md`](07-refactoring-roadmap.md)

## Alle Dokumente

| # | Dokument | Inhalt |
|---|---|---|
| 00 | [Executive Marktreife-Bewertung](00-executive-readiness-verdict.md) | Scores, Blocker P0–P3, Umsetzungsergebnis, Launch-Entscheid |
| 01 | [System Inventory](01-system-inventory.md) | Architektur, Stacks, Datenmodell, Mandantenmodell, Auth, Vendoren, Deployment |
| 02 | [Claim-vs-Proof-Matrix](02-claim-vs-proof-matrix.md) | 48 Produktaussagen gegen den Nachweis im Code |
| 03 | [EU AI Act Gap-Analyse](03-eu-ai-act-gap-analysis.md) | Kundenpflichten **und** die eigene AI-Act-Position |
| 04 | [NIS2 / BSIG Gap-Analyse](04-nis2-gap-analysis.md) | Scope, Geschäftsleitung, Risiko, Lieferkette, Meldekaskade |
| 05 | [DSGVO / Schrems II / CLOUD Act](05-gdpr-cloud-act-gap-analysis.md) | Dateninventar, Vendor-Kette, Transfers, Löschkonzept, Souveränität |
| 06 | [Zielarchitektur: drei Betriebsmodi](06-target-architecture-modes.md) | `Standard DACH` · `EU Sovereign` · `Strict Sovereign` mit je zulässigem Claim |
| 07 | [Refactoring-Roadmap](07-refactoring-roadmap.md) | P0–P3 mit Dateien, Risiken, Tests, Aufwand |
| 08 | [Ziel-Domänenmodell](08-target-domain-model.md) | Soll-Ist der 33 Entitäten, RLS-Strategie, Migrationsplan |
| 09 | [Security-Hardening-Plan](09-security-hardening-plan.md) | 18 Bereiche mit Befund und Maßnahme |
| 10 | [Messaging-Redlines](10-messaging-redlines.md) | Verbotene und zulässige Formulierungen mit Begründung |
| 11 | [Überarbeitete Website-Texte](11-revised-website-copy.md) | Hero, Module, Sicherheit, FAQ, Trust Center, Disclaimer |
| 12 | [GTM-Readiness DACH](12-gtm-readiness-dach.md) | ICPs, Dealbreaker, Käuferfragen, Due-Diligence-Paket, Preislogik |
| 13 | [Security-Questionnaire-Pack](13-security-questionnaire-pack.md) | Antwortbibliothek, Top-50-Fragen, 20 Sales-Red-Flags |

## Belegstufen

Alle Dokumente kennzeichnen ihre Aussagen:

| Marker | Bedeutung |
|---|---|
| **BELEGT IM CODE** | Im Repository verifizierbar, Datei/Zeile benannt |
| **PLAUSIBLE ANNAHME** | Aus Code/Doku ableitbar, nicht vollständig verifiziert |
| **OFFENE LÜCKE** | Nicht vorhanden; vor Enterprise-Einsatz nötig |
| **KRITISCHER BLOCKER** | Verhindert wahrheitsgemäße Claims oder ist Sicherheits-/Rechtsrisiko |

## Arbeitsregeln, die aus diesem Review folgen

1. **Kein neuer Claim ohne Zeile in `02`.** Wer einen öffentlichen Text schreibt, trägt
   den Claim mit Nachweis und Risikolevel ein.
2. **Kein 🔴-Claim in Vertriebsunterlagen.** Die Ampel in `10` gilt für Website, Deck,
   Angebot, Ausschreibung und LinkedIn gleichermaßen.
3. **Fragebogenantworten folgen der Ehrlichkeitsregel** aus `13` Teil 4: Eine Lücke wird
   benannt, nicht umgedeutet.
4. **Quartalsweiser Claim-Review.** Fällt ein Nachweis weg, verschwindet der Claim.

## Grenzen dieses Reviews

- Rein statische Codeanalyse. Kein Zugriff auf Produktivumgebung, Azure-Tenant,
  Verträge, Subprozessorenliste oder Betriebsdokumentation.
- Keine Rechtsberatung. Normbezüge und Paragraphenverweise sind fachliche Einordnung
  und vor Außenkommunikation durch qualifizierte Beratung zu prüfen.
- Anwendungszeitpunkte der KI-Verordnung waren zuletzt Gegenstand laufender
  Gesetzgebungsverfahren; dieses Review bewertet funktionale Abdeckung, keine Fristen.
- Kein Penetrationstest und keine dynamische Sicherheitsanalyse. Die Abwesenheit eines
  Befunds ist hier kein Beleg für Abwesenheit einer Schwachstelle.
