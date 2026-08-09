# 10 – Messaging-Redlines

**Zweck:** Verbindliche Sprachregelung für Website, Pitch-Deck, Angebote,
Ausschreibungsantworten, LinkedIn und Vertriebsgespräche.

**Grundregel:** Ein Claim darf geführt werden, wenn ein Prospect ihn mit vertretbarem
Aufwand prüfen kann. Alles andere ist Werbung mit Haftungsrisiko.

**Rechtlicher Rahmen (kurz):** Irreführende Angaben über Eigenschaften einer Ware oder
Dienstleistung sind nach § 5 UWG unzulässig und von Wettbewerbern abmahnbar. Bei
Compliance-Software kommt hinzu: Ein Kunde, der wegen eines falschen Claims eine
Meldefrist versäumt, hat einen Anknüpfungspunkt für Schadensersatz. Und
Enterprise-Einkauf prüft Claims — ein widerlegter Claim kostet den Deal, nicht nur
Reputation.

**Vorbemerkung:** Die aktuelle Website ist bereits deutlich sorgfältiger formuliert als
im Marktsegment üblich (siehe §6 Positivliste). Diese Redlines schließen die
verbleibenden Lücken und legen die Sprache für die kommende Produktphase fest.

---

## 1. Die Ampel

| 🔴 **NIEMALS** | 🟠 **NUR MIT ZUSATZ** | 🟢 **FREI VERWENDBAR** |
|---|---|---|
| DSGVO-konform | EU-Hosting | KI-System-Register |
| AI Act ready / AI-Act-konform | audit-ready | Risikoklassifizierung (unterstützend) |
| NIS2-ready / NIS2-konform | enterprise-ready | Governance-Workspace |
| ISO-27001-konform | secure by design | Audit-Trail mit Integritätsprüfung |
| zertifiziert | Mandantenfähigkeit | Mandantenfähig |
| souverän / sovereign | Board-ready | Evidence-Verwaltung |
| CLOUD-Act-sicher / -compliant | automatische Klassifizierung | Cross-Regulation-Mapping |
| keine US-Anbieter | Compliance Operating System | Board-Reports |
| Zero Trust | Meldekaskade | KI-Funktionen standardmäßig deaktiviert |
| garantiert / rechtssicher | | Governance-Workflows mit SLA |
| unveränderlich | | Trust Center für Ihre Prüfer |
| vollautomatisch | | EU-Region (Frankfurt) für die Auslieferung |

---

## 2. Verbotene Formulierungen mit Begründung und Ersatz

### 🔴 „DSGVO-konform"

**Warum verboten:** DSGVO-Konformität ist eine Eigenschaft des gesamten
sozio-technischen Systems — Software, Konfiguration, Verträge, Prozesse, Personal,
Nachweise. Keine Software kann sie herstellen. Jeder Datenschutzbeauftragte weiß das,
und die Aussage disqualifiziert den Anbieter im Gespräch sofort.

**Ersatz:**
> „Datenschutzfreundlich konzipiert: KI-Funktionen standardmäßig deaktiviert,
> Mandantentrennung, Audit-Trail mit Integritätsprüfung. Die DSGVO-Konformität des
> Einsatzes verantwortet der Verantwortliche; wir liefern die Nachweisstrukturen."

---

### 🔴 „AI Act ready" / „NIS2-ready"

**Warum verboten:** „Ready" impliziert vollständige Pflichtenabdeckung. Belegbar ist
sie nicht (`03` §3, `04` §12): AI Literacy, Rollenabgrenzung, Serious Incidents,
Lieferkettenrisiko, Meldungsnachweise und Betroffenheitsnachweis fehlen.

**Ersatz:**
> „Unterstützung für die Governance-Pflichten aus KI-VO und NIS2 in den Bereichen
> Register, Klassifizierung, Kontrollen, Evidenz und Berichterstattung."

---

### 🔴 „souverän" / „EU-only" / „keine US-Anbieter"

**Warum verboten:** Vercel Inc. betreibt Frontend **und BFF**. Der Catch-all-Proxy
(`frontend/src/app/api/backend/[...path]/route.ts`) verarbeitet jede authentifizierte
Produktanfrage im Klartext. Vercel ist ein US-Unternehmen; die Region `fra1` ändert
daran nichts, weil für den CLOUD Act die Kontrolle über den Anbieter maßgeblich ist,
nicht der Serverstandort.

**Ersatz im Modus `Standard DACH`:**
> „Betrieb in EU-Rechenzentren. Unsere Subprozessoren und deren Jurisdiktion legen wir
> vollständig offen. Für Kunden mit strengeren Anforderungen bieten wir den
> Betriebsmodus `EU Sovereign` ohne US-kontrollierte Anbieter im Datenpfad an."

Erst nach Umsetzung des Modus `EU Sovereign` (`06`) darf die Souveränitätsaussage
geführt werden — und dann nur für Kunden in diesem Modus.

---

### 🔴 „CLOUD-Act-sicher" / „CLOUD Act compliant"

**Warum verboten:** Zusätzlich zur fehlenden Grundlage ist die Formulierung inhaltlich
sinnlos. Der CLOUD Act ist ein US-Gesetz, das US-Anbieter zur Herausgabe verpflichtet
— es gibt nichts, dem man „entspricht". Wer so formuliert, signalisiert einem
technisch versierten Prospect fehlendes Verständnis.

**Ersatz:** „Kein US-kontrollierter Anbieter im Datenpfad" (nur im Modus
`EU Sovereign`/`Strict Sovereign`).

---

### 🔴 „unveränderliche Audit-Logs"

**Warum verboten:** Der Append-only-Guard (`app/audit_append_only.py`) greift im
SQLAlchemy-`before_flush` — also nur für Schreibvorgänge über die Session. Direkter
SQL-Zugriff, ein DBA, ein Bulk-Statement oder ein Backup-Restore umgehen ihn
vollständig.

**Ersatz:**
> „Audit-Trail mit Hash-Kette und Integritätsprüfung; Änderungen und Löschungen sind
> auf Applikationsebene unterbunden und nachträgliche Manipulation ist über die
> Kettenprüfung erkennbar."

---

### 🔴 „Zero Trust"

**Warum verboten:** Zero Trust ist eine Netzwerk- und Identitätsarchitektur mit
mTLS, Mikrosegmentierung und kontinuierlicher Verifikation. Im Repository existiert
keine Netzwerkarchitektur — es gibt kein Deployment-Artefakt.

**Ersatz:** Konkrete Kontrollen nennen statt des Schlagworts: „Jede Anfrage wird
gegen Session und Mandantenbindung geprüft; globale Schlüssel sind in Produktion
deaktiviert."

---

### 🔴 „vollautomatische Klassifizierung" / „KI bewertet Ihre Compliance"

**Warum verboten:** Doppelt gefährlich. Erstens ist die Einstufung nach Art. 6 KI-VO
eine Rechtsanwendung. Zweitens würde ein System, das Rechtsfolgen automatisch
feststellt, seine eigene AI-Act-Einstufung verändern (`03` Teil 2).

**Ersatz:**
> „Unterstützte Vorklassifizierung entlang der Logik von Art. 6 und Annex I/III. Die
> Einstufung wird von einem Menschen bestätigt und verantwortet."

Diese Formulierung schützt zusätzlich die eigene Rechtsposition.

---

### 🔴 „rechtssicher" / „garantiert" / „100 %"

**Warum verboten:** Absolutversprechen bei Rechtsfolgen. Zudem grenzt es an
Rechtsberatung durch einen Nicht-Rechtsdienstleister (RDG).

---

## 3. Formulierungen, die nur mit Zusatz zulässig sind

| Claim | Notwendiger Zusatz | Vollständige Formulierung |
|---|---|---|
| **EU-Hosting** | Anbieterkontrolle offenlegen | „Auslieferung über EU-Region (Frankfurt). Anbieter Vercel Inc. unterliegt US-Recht — vollständige Subprozessorenliste im Trust Center." |
| **audit-ready** | Wer prüft was | „Vorbereitet für interne Revision und Wirtschaftsprüfer: Audit-Trail, Evidence-Bundles, behördliches Prüfpaket." |
| **enterprise-ready** | Umfang benennen | „Enterprise-Funktionsumfang: SSO (Entra ID), SCIM, RBAC mit 10 Rollen, Audit-Trail, Trust Center, Mandantenfähigkeit." |
| **Mandantenfähigkeit** | Isolationsebene | „Mandantentrennung mit mandantenspezifischen Schlüsseln, Sessions und durchgängiger Datenfilterung." *(nach P0-1: „…und datenbankseitiger Row-Level-Security")* |
| **Meldekaskade** | Was das Produkt tut | „Fristenberechnung ab Kenntniserlangung mit Eskalation und Überfälligkeitsanzeige. Die Meldung an die Behörde nehmen Sie selbst vor." |
| **secure by design** | Belegen statt behaupten | „KI-Funktionen standardmäßig aus, personenbezogene Muster blockieren Modellaufrufe, globale Schlüssel in Produktion deaktiviert, Sicherheitsprüfungen in jeder CI-Pipeline." |
| **Compliance Operating System** | Betriebsvoraussetzung | „Operating-System-Logik von Pflicht über Control und Aufgabe bis Nachweis; die zeitgesteuerte Ausführung erfordert den mitgelieferten Scheduler." |
| **Board-ready** | Was geliefert wird | „Board-Reports mit versionierten Snapshots und Metrik-Historie als Entscheidungsunterlage." |

---

## 4. Sprachregelung für die vier Claim-Typen

Verbindlich für alle Texte. Jede Produktaussage bekommt genau eine dieser vier
Kennzeichnungen:

| Typ | Erkennungsmerkmal | Beispiel |
|---|---|---|
| **A – standardmäßig so ausgeliefert** | „standardmäßig", „ab Werk" | „KI-Funktionen sind standardmäßig deaktiviert." |
| **B – konfigurierbar** | „konfigurierbar", „aktivierbar", „im Betriebsmodell festzulegen" | „Aufbewahrungsfristen sind je Datenkategorie konfigurierbar." |
| **C – unterstützend** | „unterstützt", „strukturiert", „bereitet vor" | „Unterstützt die Risikoklassifizierung entlang Art. 6." |
| **D – kundenseitig zu verantworten** | „verantworten Sie", „prüfpflichtig", „mit Ihrem Berater abstimmen" | „Die rechtliche Einstufung verantworten Sie." |

**Redaktionsregel:** In jedem Modulabschnitt der Website muss mindestens eine
Typ-C- oder Typ-D-Aussage stehen. Ein Abschnitt, der nur aus Typ-A-Versprechen
besteht, ist überzogen.

---

## 5. Konkrete Fundstellen mit Redline

| Datei | Ist | Bewertung | Soll |
|---|---|---|---|
| `frontend/src/components/admin/AuditLogClient.tsx` | „DSGVO Art. 30 Verarbeitungsverzeichnis / Automatisch generierter Export aller Verarbeitungstätigkeiten" | 🔴 **Behoben in diesem Change-Set.** Der Export enthielt konstante Werte für Rechtsgrundlage, Aufbewahrungsfrist und TOM — inklusive „Row-Level-Security", die nicht aktiv ist | „Aktivitätsübersicht … Kein Verzeichnis von Verarbeitungstätigkeiten nach Art. 30 DSGVO." |
| `frontend/src/components/admin/VVTExportClient.tsx` | Beispieldaten mit „Art. 30 DSGVO"-Badge und Download-Buttons ohne Funktion | 🔴 **Behoben.** Ersetzt durch `AuditActivityExportClient` mit Abgrenzungshinweis | — |
| `README.md` | „Enterprise-SaaS-Prototyp … E-Rechnung, DSGVO und GoBD in einer integrierten Compliance-Maschine" | 🟠 „Compliance-Maschine" suggeriert Automatik; Positionierung widerspricht zudem der Website (dort: AI Governance) | Positionierung vereinheitlichen (siehe §7) |
| `app/services/trust_center_service.py` | Bundle-Beschreibung „DSGVO / GDPR Evidence Bundle: Verarbeitungsverzeichnis, TOM-Dokumentation und AVV-Nachweise" | 🟠 Verspricht Inhalte, für die keine Entitäten existieren | „Vorlagenstruktur für DSGVO-Nachweise; Inhalte werden vom Mandanten befüllt." |
| `frontend/src/app/trust-center/page.tsx` | „Für die öffentliche Website wird Vercel zur Web-Auslieferung eingesetzt." | 🟢 Heute korrekt, 🔴 **sobald das Produkt live geht** | Vor Produktivstart auf die vollständige Rolle erweitern (BFF, Session-Terminierung) |
| `website/compliancehub-landing.html` | Gesamter Text | 🟢 Vorbildlich zurückhaltend | Unverändert lassen |
| `docs/enterprise-readiness-20260714.md` | „Release-Status: Pre-Production" | 🟢 Ehrlich | Beibehalten, bis P0 abgeschlossen ist |

---

## 6. Positivliste — nicht anfassen

Diese Formulierungen sind belastbar und zeigen, dass im Team bereits ein
funktionierendes Claim-Bewusstsein existiert. Sie sind der Maßstab für alle neuen Texte:

- „Die Plattform unterstützt Analyse und Review; Verantwortung und Freigabe bleiben
  beim Menschen." *(Homepage — perfekte C/D-Abgrenzung)*
- „LLM-Funktionen sind standardmäßig aus." *(Homepage — Typ A, im Code belegt)*
- „Das ist weder eine Zertifizierung noch eine automatische Feststellung der
  Rechtskonformität eines Kunden." *(Trust Center)*
- „Keine behauptete offizielle SAP- oder DATEV-Produktzertifizierung." *(Landingpage)*
- „Keine Rechtsberatung." *(Landingpage)*
- „Die Vorschau zeigt die Produktlogik, nicht einen zertifizierten Kundenbetrieb."
  *(Homepage)*
- „Release-Status: Pre-Production / nicht freigegeben." *(README)*

---

## 7. Positionierungs-Inkonsistenz

**Befund:** Das Produkt führt drei verschiedene Namen und zwei verschiedene
Positionierungen.

| Ort | Name | Positionierung |
|---|---|---|
| `README.md` | „SBS-Nexus ComplianceHub" | E-Rechnung, DSGVO, GoBD für den Mittelstand |
| Website | „Compliance Hub" / „ComplianceHub" | AI Governance für DACH |
| Domain / Auftrag | „ComplyWithAI.de" | AI Governance |
| `pyproject.toml` | `compliancehub` | — |

**Bewertung:** Für einen Enterprise-Einkauf ist Namensuneinheitlichkeit ein
Vertrauenssignal im negativen Sinn — sie deutet auf ein Produkt im Umbau hin. Bei einer
Sicherheitsprüfung fällt es spätestens beim Abgleich von Vertragspartner, Domain und
Software-Bezeichnung auf.

**Empfehlung:** **Eine** Marke wählen und konsequent durchziehen. Naheliegend:
**ComplyWithAI** als Produktname, weil er die Domain, die AI-Governance-Positionierung
und den Kern-Differenzierer trägt. „SBS-Nexus" gehört in die Impressumsangabe des
Betreibers, nicht in den Produktnamen. Der technische Paketname `compliancehub` darf
bleiben.

**Ebenso zu klären: E-Rechnung/GoBD.** Der Code enthält XRechnung-Export, DATEV-EXTF
und GoBD-Audit-Export — Reste der ursprünglichen Positionierung. Zwei Optionen:

1. **Als Differenzierer behalten** und in die Story integrieren: „Wir kennen den
   Kanzleialltag — deshalb sprechen wir DATEV." Für die Zielgruppe Steuerberater
   ist das ein echter Vorteil.
2. **Herausnehmen** und fokussieren.

Option 1 ist stimmiger, weil DATEV-Nähe in DACH ein echter Vertrauensanker ist. Dann
muss die Website die E-Rechnungs-Funktionen aber sichtbar führen, statt sie nur im
README zu erwähnen.

---

## 8. Redaktioneller Freigabeprozess

Ab sofort verbindlich:

1. **Kein neuer Claim ohne Zeile in `02-claim-vs-proof-matrix.md`.** Wer einen Text
   schreibt, trägt den Claim mit Nachweis, Fundstelle und Risikolevel ein.
2. **Vier-Augen-Prinzip** für alle öffentlichen Texte: eine Person aus Produkt/Technik
   prüft die Belegbarkeit, eine aus Vertrieb die Verständlichkeit.
3. **Quartalsweiser Claim-Review**: Stimmen die Nachweise noch? Ein Claim, dessen
   Nachweis wegfällt, muss aus dem Text verschwinden.
4. **Rechtliche Prüfung** vor der ersten produktiven Veröffentlichung durch
   qualifizierte Beratung — insbesondere für Impressum, Datenschutzerklärung, AGB und
   alle Aussagen mit Normbezug.
5. **Vertriebsunterlagen unterliegen derselben Regel.** Der häufigste Ort für
   überzogene Claims ist nicht die Website, sondern die Folie, die ein Vertriebler
   selbst gebaut hat.

---

## 9. Die drei Sätze, die den Verkauf tragen

Aus dem, was heute belegbar ist, lässt sich eine starke, ehrliche Kernbotschaft bauen:

> **„KI-Funktionen sind bei uns standardmäßig aus."**
> Prüfbar, selten, und genau das, was ein deutscher Datenschutzbeauftragter hören will.

> **„Wir sagen Ihnen, was unser Produkt nicht kann."**
> Die Claim-Matrix ist ein Verkaufsargument. Kein Wettbewerber legt sie offen.

> **„Ein Kontrollmodell für fünf Normen — Sie erfassen einmal."**
> Der Cross-Regulation-Layer ist der stärkste belegbare Differenzierer.

**Grundhaltung:** Im DACH-Compliance-Markt ist Zurückhaltung ein Verkaufsargument.
Die Käufer sind Datenschutzbeauftragte, CISOs, Wirtschaftsprüfer und Berater — Menschen,
deren Beruf das Prüfen von Behauptungen ist. Wer bei ihnen einen Claim nicht belegen
kann, verliert den Deal. Wer offen sagt, was er noch nicht kann, gewinnt Vertrauen für
alles, was er behauptet.
