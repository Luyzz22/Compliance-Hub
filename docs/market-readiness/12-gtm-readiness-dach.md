# 12 – Go-to-Market-Readiness DACH

**Ausgangspunkt:** Das Produkt hat mehr Fachtiefe als Vertriebsfähigkeit. Die
regulatorische Modellierung trägt; was fehlt, sind die Nachweise, die in DACH über den
Abschluss entscheiden.

---

## 1. ICP-Segmente

### ICP 1 — Datenschutz- und ISO-Berater (Einzel bis 15 Personen)

| Merkmal | Ausprägung |
|---|---|
| Größe | 1–15 Berater, 10–80 Mandanten |
| Kaufender | Inhaber/Partner — kurze Entscheidung, kein Einkauf |
| Schmerz | Excel je Mandant, keine Wiederholbarkeit, Umsatz an Personen gebunden |
| Kaufauslöser | Mandant fragt nach dem AI Act; Berater hat keine Struktur |
| Zahlungsbereitschaft | 200–600 €/Monat, Mandantenstaffel |
| Zyklus | **2–6 Wochen** |
| Passender Modus | `Standard DACH` |
| Reifegrad-Fit | **Heute verkaufbar** |

**Warum dieses Segment zuerst:** Kein Security-Review, kein Einkauf, kein Betriebsrat.
Der Berater kauft ein Werkzeug, nicht eine Auftragsverarbeitung im großen Stil. Und er
bringt die Mandanten mit — jeder Berater ist ein Multiplikator.

**Zulässige Claims:** Alle 🟢 aus `02`. Der Cross-Regulation-Layer und das
Mandanten-Portfolio sind hier die Kaufargumente.

**Nötige Unterlagen:** Preisliste, AVV-Muster, Demo-Zugang. Mehr nicht.

---

### ICP 2 — Steuerberater- und WP-Kanzleien

| Merkmal | Ausprägung |
|---|---|
| Größe | 5–60 Berufsträger |
| Kaufender | Partner, oft mit IT-Verantwortlichem |
| Schmerz | Mandanten fragen nach KI-Governance; DATEV deckt es nicht ab |
| Besonderheit | § 203 StGB — berufsrechtliche Verschwiegenheit, sehr hohe Sensibilität |
| Zahlungsbereitschaft | 300–1.500 €/Monat |
| Zyklus | 4–10 Wochen |
| Passender Modus | `Standard DACH`, mittelfristig `EU Sovereign` |
| Reifegrad-Fit | **Nach P0-5 und P0-8** (AVV + Löschkonzept) |

**Besonderheit § 203 StGB:** Mandantendaten in einer Cloud sind berufsrechtlich
heikel. Kanzleien fragen früh nach Verschwiegenheitsverpflichtung des Anbieters,
Verschlüsselung und Zugriffsmöglichkeiten des Betreibers. Der DATEV-Bezug im Code ist
hier ein echter Vertrauensanker — er sollte auf der Website sichtbar sein.

**Nötige Unterlagen:** AVV mit Verschwiegenheitsklausel, TOM, Subprozessorenliste,
Löschkonzept.

---

### ICP 3 — Industrieller Mittelstand (150–2.000 Mitarbeitende)

| Merkmal | Ausprägung |
|---|---|
| Kaufender | Geschäftsführung + IT-Leitung + DSB; Einkauf ab ~500 MA |
| Schmerz | NIS2-Betroffenheit unklar; erste KI-Systeme ohne Governance; Kunden fragen im Lieferantenaudit |
| Kaufauslöser | Kundenanforderung in der Lieferkette, Auditbefund, Vorstandsfrage |
| Zahlungsbereitschaft | 1.000–4.000 €/Monat |
| Zyklus | 3–9 Monate |
| Passender Modus | `Standard DACH`, bei KRITIS-Nähe `EU Sovereign` |
| Reifegrad-Fit | **Nach vollständigem P0** |

**Dealbreaker heute:** Kein Pentest, kein DR-Konzept, keine Cross-Tenant-Nachweise,
keine Referenzen.

---

### ICP 4 — MSP / Managed Compliance Provider

| Merkmal | Ausprägung |
|---|---|
| Kaufender | Geschäftsführung, Service-Portfolio-Verantwortlicher |
| Schmerz | Will Compliance als wiederkehrende Leistung verkaufen, hat kein Werkzeug |
| Besonderheit | Braucht API, Mandantenautomatisierung, ggf. White-Label |
| Zahlungsbereitschaft | 2.000–10.000 €/Monat, mandantenbasiert |
| Zyklus | 2–6 Monate |
| Reifegrad-Fit | **Nach P0 + Provisionierungs-API** |

**Höchster Hebel im gesamten Portfolio:** Ein MSP bringt 20–200 Endkunden. Zugleich
das anspruchsvollste Segment — er prüft die Plattform als Partner, nicht als Nutzer.

---

### ICP 5 — Enterprise / KRITIS

| Merkmal | Ausprägung |
|---|---|
| Kaufender | CISO, Konzern-Compliance, Einkauf, Betriebsrat, ggf. Aufsichtsrat |
| Zahlungsbereitschaft | 20.000–150.000 €/Jahr |
| Zyklus | 9–18 Monate |
| Passender Modus | `EU Sovereign` oder `Strict Sovereign` |
| Reifegrad-Fit | **Frühestens 12 Monate nach P0-Abschluss** |

**Ehrliche Einschätzung:** Dieses Segment ist heute nicht adressierbar. Ohne ISO-27001,
Pentest, DR-Nachweis, SAML, BYOK und mindestens drei vergleichbare Referenzen kommt
man nicht durch das Lieferanten-Onboarding. Verfrühte Enterprise-Ansprache verbrennt
Kontakte, die man in 18 Monaten braucht.

---

## 2. ICP → Modus → Claim

| ICP | Modus | Zulässige Kernaussage | Verboten |
|---|---|---|---|
| Berater | `Standard DACH` | „EU-Betrieb, KI standardmäßig aus, Nachweise strukturiert" | souverän, DSGVO-konform |
| Kanzlei | `Standard DACH` | dito + „Verschwiegenheit vertraglich verankert" | Zertifizierungsandeutungen |
| Mittelstand | `Standard DACH` | dito + „Subprozessoren offengelegt, SCC/TIA dokumentiert" | NIS2-konform |
| MSP | `Standard DACH` | dito + „Mandantentrennung automatisiert geprüft" | white-label vor Verfügbarkeit |
| Enterprise | `EU Sovereign` | „Keine US-kontrollierten Anbieter im Datenpfad" | CLOUD-Act-immun |

---

## 3. Typische Dealbreaker in Security-Reviews

Nach Häufigkeit im DACH-Mittelstand und Enterprise:

| # | Dealbreaker | Status heute | Behebbar durch |
|---|---|---|---|
| 1 | Kein AVV / kein TOM-Dokument | 🔴 fehlt | P0-8 · 1–2 Wochen |
| 2 | Keine Subprozessorenliste | 🔴 fehlt | P0-8 · 2 Tage |
| 3 | Kein Löschkonzept, keine Fristen | 🔴 fehlt | P0-5 · 2–3 Wochen |
| 4 | Kein Exit-/Exportkonzept | 🔴 fehlt | P0-5 |
| 5 | Kein Penetrationstest | 🔴 fehlt | extern · 4–6 Wochen |
| 6 | Kein DR-/Backup-Konzept mit getestetem Restore | 🔴 fehlt | P0-7 |
| 7 | Kein Nachweis der Mandantentrennung | 🔴 fehlt | P0-12 · 3 Tage |
| 8 | US-Anbieter ohne Transferdokumentation | 🔴 fehlt | P0-8 |
| 9 | Kein SAML | 🟠 Entra vorhanden | P1-15 |
| 10 | Keine Referenzkunden | 🔴 | Zeit |
| 11 | Kein ISO 27001 | 🔴 | 12–18 Monate |
| 12 | Keine SLA-Zusage | 🔴 fehlt | Vertrag, nach P0-7 |
| 13 | Uneinheitliche Produktbezeichnung | 🟠 | `10` §7 · 1 Tag |
| 14 | Kein Support-Zugriffskonzept | 🔴 fehlt | P1-10 |
| 15 | Keine Angabe zu Datenklassifizierung | 🔴 fehlt | P1-1 |

**Bemerkenswert:** Acht der zehn wichtigsten Dealbreaker sind **Dokumentation oder
kleine Codeänderungen**, nicht Architektur. Das ist die günstigste Investition im
gesamten Backlog.

---

## 4. Wer fragt was

### Datenschutzbeauftragter

1. Wo werden die Daten verarbeitet, und wer kontrolliert diesen Anbieter?
2. AVV, TOM, Subprozessorenliste — bitte vorab.
3. Wie ist die Mandantentrennung technisch umgesetzt und wie wird sie geprüft?
4. Löschkonzept und Aufbewahrungsfristen je Datenkategorie?
5. Wie unterstützen Sie uns bei Auskunfts- und Löschersuchen?
6. Welche Drittlandtransfers finden statt, auf welcher Grundlage, mit welcher TIA?
7. Werden Daten für KI-Training verwendet?
8. Wer aus Ihrem Support kann auf unsere Daten zugreifen — und sehen wir das?
9. Ist eine DSFA nötig, und liefern Sie Zuarbeit?
10. Was passiert bei Vertragsende?

**Heute beantwortbar: 3 von 10.** Nach P0-5 und P0-8: **10 von 10.**

### CISO

1. Letzter Penetrationstest? Bericht?
2. RPO/RTO, letzter dokumentierter Restore-Test?
3. Verschlüsselung at rest und in transit — welche Schlüssel, wer verwaltet sie?
4. Nachweis der Mandantentrennung?
5. SSO/SAML/SCIM, MFA-Erzwingung, Break-Glass?
6. Security-Monitoring, Incident-Response, Meldepflichten uns gegenüber?
7. Sicherer Softwareentwicklungsprozess, SAST/DAST/SCA, SBOM?
8. Abhängigkeitsmanagement und Patch-Zeiten?
9. Sind Sie selbst NIS2-betroffen — und wenn ja, wie erfüllen Sie das?
10. Verfügbarkeitsstatistik und Statusseite?

**Heute beantwortbar: 3 von 10** (Frage 7 und 8 sogar überdurchschnittlich gut —
gepinnte Actions, CodeQL, Bandit, pip-audit, npm-audit, Dependabot, Dependency Review).

**Vertriebstipp:** Frage 7 ist die einzige, bei der die Antwort heute besser ist als
beim typischen Wettbewerber. Der CI-Auszug gehört ins Trust Center.

### Einkauf

1. Rechtsform, Handelsregister, Bonität, Gesellschafterstruktur?
2. Wie viele Mitarbeitende? Wie lange am Markt?
3. Referenzkunden vergleichbarer Größe?
4. Preismodell, Preisanpassungsklausel, Kündigungsfristen?
5. SLA mit Pönale?
6. Haftung, Versicherungssumme, Cyber-Versicherung?
7. Was passiert bei Insolvenz — Escrow?
8. Auftragsverarbeitung und Subunternehmer?
9. Exit-Unterstützung und Datenmigration?
10. Nachhaltigkeit/ESG-Anforderungen?

**Kritisch:** Fragen 1, 2, 3, 7. Ein junges Unternehmen ohne Referenzen ist im
Konzerneinkauf ein Lieferantenrisiko. **Empfehlung:** Escrow-Vereinbarung frühzeitig
anbieten — sie kostet wenig und entschärft die Insolvenzfrage vollständig.

### ISO-Berater / Auditor

1. Wie mappen Sie auf die ISO-27001-Controls? Ist das Mapping einsehbar?
2. Können Sie Nachweise mit Zeitstempel und Versionsstand exportieren?
3. Ist der Audit-Trail manipulationssicher — und wie weisen Sie das nach?
4. Wie bilden Sie das Risikomanagement nach Kap. 6.1 ab?
5. Wie werden Kontrollwirksamkeit und Review-Zyklen dokumentiert?
6. Können Sie Statusstände zu einem Stichtag rekonstruieren?
7. Wie unterscheiden Sie technische, organisatorische und personelle Maßnahmen?

**Frage 4 und 7 sind heute Schwachstellen** (kein Risikoregister, keine
Maßnahmenklassifizierung). Fragen 2, 3, 5, 6 sind Stärken.

### Betriebsrat

1. Werden Leistungs- oder Verhaltensdaten von Beschäftigten erfasst?
2. Wer kann sehen, wer wann was bearbeitet hat?
3. Können daraus Rückschlüsse auf individuelle Arbeitsleistung gezogen werden?
4. Ist eine Betriebsvereinbarung erforderlich?
5. Können personenbezogene Auswertungen technisch unterbunden werden?
6. Wie lange werden diese Daten gespeichert?

**Diese Fragen werden regelmäßig unterschätzt und verzögern Deals um Monate.**

**Ehrliche Antwort heute:** Ja, das System erfasst Verhaltensdaten. `audit_logs`
enthält `actor`, `ip_address`, `user_agent`, Zeitstempel und vollständige
Zustandsobjekte; `usage_events` und `privileged_action_events` kommen hinzu. Eine
Auswertung auf Personenebene ist technisch möglich. Es gibt keine Löschfrist.

**Empfehlung mit hohem Vertriebswert:**
1. Muster-Betriebsvereinbarung als Trust-Center-Download bereitstellen
2. Rollenkonzept ergänzen, das personenbezogene Auswertungen technisch ausschließt
3. Pseudonymisierungsmodus für Audit-Auswertungen anbieten
   (`COMPLIANCEHUB_AUDIT_PSEUDONYMIZATION_KEY` existiert bereits — daraus ein
   sichtbares Feature machen)
4. Kurze Aufbewahrungsfrist für Zugriffsdaten als Default (P0-5)

Wer als Anbieter von sich aus eine Muster-Betriebsvereinbarung mitbringt, verkürzt
diesen Deal-Abschnitt erheblich.

---

## 5. Due-Diligence-Paket

### Sofort verfügbar (vor jedem Gespräch)

| Dokument | Status | Aufwand |
|---|---|---|
| Produktübersicht (2 Seiten) | ✅ vorhanden | — |
| Sicherheitsübersicht (2 Seiten) | 🔴 fehlt | 1 Tag |
| Subprozessorenliste | 🔴 fehlt | 2 Tage |
| AVV-Muster | 🔴 fehlt | 1 Woche + Prüfung |
| TOM nach Art. 32 | 🔴 fehlt | 3 Tage |
| Architekturdiagramm mit Datenflüssen | 🔴 fehlt | 2 Tage (nach P0-7) |
| Preisliste | 🟠 im Code, nicht als Dokument | 1 Tag |
| Muster-Betriebsvereinbarung | 🔴 fehlt | 3 Tage |

### Auf Anfrage unter NDA

| Dokument | Status |
|---|---|
| Penetrationstestbericht | 🔴 fehlt |
| TIA für US-Subprozessoren | 🔴 fehlt |
| DR-Plan mit Restore-Testprotokoll | 🔴 fehlt |
| SBOM | 🟠 GitHub-Dependency-Graph vorhanden, kein Artefakt |
| Incident-Response-Plan | 🔴 fehlt |
| Beantwortete Standardfragebögen (VDA ISA / BSI) | 🔴 fehlt |
| Ergebnis der Cross-Tenant-Testsuite | 🟠 nach P0-12 |

**Realistische Einschätzung:** Für ICP 1 reichen vier Dokumente. Für ICP 3 braucht es
das vollständige Paket. Die Erstellung ist überwiegend Schreibarbeit auf Basis
vorhandener Fakten — geschätzt **3–4 Personenwochen** plus externe Rechtsprüfung.

---

## 6. Empfohlene GTM-Sequenz

### Phase 1 (Monat 1–3) — Berater-Beta

- **Ziel:** 5–10 zahlende Berater
- **Voraussetzung:** P0-2, P0-3, P0-4, P0-10, P0-11, P0-12 + AVV + Subprozessorenliste
- **Kanal:** Direktansprache über Berufsverbände (GDD, BvD, DGI), LinkedIn, Fachvorträge
- **Preis:** bewusst niedrig (200–400 €/Monat) gegen Referenz und Feedback
- **Was verkauft wird:** Wiederholbarkeit über Mandanten hinweg

### Phase 2 (Monat 4–8) — Kanzleien und erster Mittelstand

- **Ziel:** 20–30 Kunden, erste Mittelstandspilotierung
- **Voraussetzung:** vollständiges P0 + Pentest
- **Kanal:** Berater als Multiplikatoren, Steuerberaterkammern, DATEV-Ökosystem
- **Preis:** 300–1.500 €/Monat

### Phase 3 (Monat 9–15) — MSP-Partnerschaften

- **Ziel:** 3–5 MSP-Partner
- **Voraussetzung:** P1 überwiegend + Provisionierungs-API + SLA
- **Preis:** mandantenbasiert mit Partnerstaffel

### Phase 4 (ab Monat 15) — Enterprise

- **Voraussetzung:** ISO 27001, Modus `EU Sovereign`, drei Referenzen, SAML
- **Vorher nicht ansprechen.**

---

## 7. Preislogik

**Empfohlene Metrik: Anzahl Mandanten bzw. juristische Einheiten** — nicht Nutzerzahl.

Begründung: Der Wert des Produkts skaliert mit der Anzahl der zu governenden
Organisationen, nicht mit der Zahl der Bearbeiter. Nutzerbasierte Preise bestrafen
zudem genau das Verhalten, das man fördern will (mehr Beteiligte, mehr Nachweise).

| Paket | Zielgruppe | Umfang | Indikativ |
|---|---|---|---|
| **Berater** | ICP 1 | bis 10 Mandanten, alle Kernmodule | 249 €/Monat |
| **Kanzlei** | ICP 2 | bis 40 Mandanten, DATEV-Export, Portfolio | 699 €/Monat |
| **Unternehmen** | ICP 3 | 1 Mandant, alle Module, SSO | 1.490 €/Monat |
| **Partner** | ICP 4 | ab 50 Mandanten, API, Provisionierung | ab 2.900 €/Monat |
| **Sovereign** | ICP 5 | Modus `EU Sovereign`, dedizierter Betrieb | Projekt + Lizenz |

**Wichtig:** Die im Code hinterlegten Pläne
(`app/services/stripe_billing_service.py`: starter 49 €, professional 149 €,
enterprise) passen **nicht** zu diesen ICPs. 49 €/Monat signalisiert
Selbstbedienungssoftware und untergräbt die Enterprise-Positionierung. Preise und
Positionierung müssen zusammenpassen — das ist eine der wenigen Stellen, an denen
zu billig aktiv schadet.

**Zusätzlich:** Der Modus als Preisdimension (`Standard DACH` → `EU Sovereign` +40–60 %
→ `Strict Sovereign` Projektgeschäft) ist ein sauberes, ehrliches Upsell-Modell: Der
Kunde zahlt für real erbrachten Mehraufwand, nicht für ein Feature-Gate.

---

## 8. Die drei Dinge, die den größten Unterschied machen

1. **Das Due-Diligence-Paket schreiben.** Drei bis vier Wochen Arbeit, überwiegend
   Dokumentation auf Basis vorhandener Fakten. Sie entscheidet über die Hälfte aller
   Dealbreaker.

2. **Die Claim-Matrix veröffentlichen.** Kein Wettbewerber legt offen, was sein Produkt
   nicht kann. Im DACH-Compliance-Markt, wo die Käufer beruflich Behauptungen prüfen,
   ist das ein Alleinstellungsmerkmal — und es qualifiziert Leads vor dem ersten
   Gespräch.

3. **Das eigene Produkt auf sich selbst anwenden.** ComplyWithAI sollte sein eigenes
   KI-Register, seine eigene Rollenklärung nach KI-VO und seine eigene
   Transfer-Dokumentation in ComplyWithAI führen — und einen Auszug im Trust Center
   veröffentlichen. Das ist der stärkste denkbare Produktbeweis und kostet fast nichts.
