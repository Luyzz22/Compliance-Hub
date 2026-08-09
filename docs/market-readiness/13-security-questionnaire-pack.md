> **Verwendungshinweis:** Die Antworten spiegeln den Code-Stand vom 2026-08-09 im
> Betriebsmodus `Standard DACH Compliance`. Antworten mit 🔴 dürfen **nicht** verwendet
> werden, solange die Maßnahme offen ist — dann gilt die Ehrlichkeitsregel aus §4.
> Nach jeder P0-Umsetzung ist die betroffene Antwort zu aktualisieren.

# 13 – Security-Questionnaire-Antwortbibliothek

**Legende**

| Symbol | Bedeutung |
|---|---|
| 🟢 | Belegbar — Antwort so verwendbar |
| 🟠 | Teilweise — Antwort mit Einschränkung verwendbar |
| 🔴 | Nicht belegbar — nur die ehrliche Nichtverfügbarkeitsantwort verwenden |

---

## Teil 1 — Antwortbibliothek

### A. Unternehmen und Governance

**A1 · Rechtsform, Sitz, Gründungsjahr?** 🟢
> [Aus dem Impressum]. Sitz in Deutschland. Wir unterliegen deutschem und
> EU-Recht.

**A2 · Haben Sie eine ISO-27001-Zertifizierung?** 🔴
> Nein. Wir haben derzeit keine ISO-27001-Zertifizierung. Wir arbeiten nach den
> Prinzipien der Norm — dokumentiertes Rollenmodell, Zugriffskontrolle,
> Audit-Trail, Schwachstellenmanagement in der CI — aber ein Zertifikat gibt es nicht.
> Den Zeitplan finden Sie im Trust Center.

**A3 · Haben Sie einen Datenschutzbeauftragten?** 🟠
> [Angabe]. Kontakt über datenschutz@[domain].

**A4 · Sind Sie selbst von NIS2 betroffen?** 🟠
> Wir prüfen unsere Betroffenheit anhand von Sektor, Größenschwelle und
> Sonderregelungen. Das Ergebnis mit Begründung stellen wir unter NDA zur Verfügung.

**A5 · Haben Sie eine Cyber-Versicherung?** 🟠
> [Angabe, Deckungssumme]. Nachweis auf Anfrage.

---

### B. Hosting, Datenresidenz, Subprozessoren

**B1 · Wo werden unsere Daten verarbeitet?** 🟠
> In EU-Rechenzentren; die konkrete Region halten wir vertraglich fest. Wichtig für
> Ihre Bewertung: Einige unserer Dienstleister sind US-Unternehmen und unterliegen
> US-Recht, auch wenn sie in EU-Regionen verarbeiten. Wir weisen das offen aus, statt
> es unter „EU-Hosting" zusammenzufassen.

**B2 · Wer sind Ihre Unterauftragsverarbeiter?** 🔴 *(bis P0-8)*
> Nach Umsetzung: Vollständige Liste mit Sitz, kontrollierender Jurisdiktion, Zweck,
> Datenkategorien und Region im Trust Center. Änderungen kündigen wir 30 Tage im Voraus
> an, mit Widerspruchsrecht.

**B3 · Finden Drittlandtransfers statt?** 🟠
> Ja. Wir setzen Dienstleister mit US-Muttergesellschaft ein. Grundlage sind
> EU-Standardvertragsklauseln und eine dokumentierte Transfer-Folgenabschätzung. Beide
> Dokumente erhalten Sie auf Anfrage.

**B4 · Können Sie ohne US-Anbieter betrieben werden?** 🟠
> Im Standardmodus nein. Wir bereiten den Betriebsmodus `EU Sovereign` vor:
> vollständiger Betrieb bei EU-ansässigen Anbietern, keine US-kontrollierten
> Dienstleister im Datenpfad. Verfügbar auf Anfrage mit Projektvorlauf.

**B5 · Ist die Datenresidenz technisch erzwungen oder nur zugesagt?** 🟢
> Technisch erzwungen. Der Betriebsmodus ist eine Deployment-Eigenschaft: Die Anwendung
> startet nicht, wenn ein im Modus verbotener Anbieter konfiguriert ist, und die
> Modellanbieter-Kette wird gefiltert statt nur umsortiert. Sie können den aktiven
> Modus unter `GET /api/v1/sovereignty/profile` selbst abfragen.

---

### C. Mandantentrennung

**C1 · Wie ist die Mandantentrennung umgesetzt?** 🟠
> Gemeinsame Datenbank mit Mandantenkennung auf jedem Datensatz. Jeder Zugriff läuft
> über einen authentifizierten Kontext, der die Mandantenbindung trägt; ein abweichender
> Mandantenparameter führt zu 403. Zugangsschlüssel sind mandantenspezifisch und
> gehasht gespeichert; mandantenübergreifende Schlüssel sind in Produktion deaktiviert
> und der Start bricht ab, wenn sie aktiviert würden.
>
> **Offen:** Datenbankseitige Row-Level-Security wird derzeit eingeführt (P0-1).

**C2 · Wie prüfen Sie das?** 🟠 *(🟢 nach P0-12)*
> Nach Umsetzung: Eine automatisierte Negativtestsuite prüft bei jeder Codeänderung
> für jeden Endpunkt, dass ein als Mandant A authentifizierter Aufruf auf eine
> Ressource von Mandant B nicht mit 200 antwortet. Das Ergebnis stellen wir zur
> Verfügung.

**C3 · Können Sie Single-Tenant anbieten?** 🟠
> Im Modus `Strict Sovereign` ja — dedizierte Instanz oder Betrieb in Ihrer
> Infrastruktur. Projektgeschäft mit Vorlauf.

---

### D. Zugriff und Identität

**D1 · Unterstützen Sie SSO?** 🟠
> Ja, über Microsoft Entra ID (OpenID Connect, Authorization Code Flow mit PKCE). Der
> Identitätsanbieter wird mandantenspezifisch geprüft; die Zuordnung erfolgt über
> unveränderliche Claims (`tid`, `oid`), nicht über die E-Mail-Adresse.
>
> **Nicht verfügbar:** SAML 2.0 und generisches OIDC — beides auf der Roadmap.

**D2 · SCIM?** 🟠
> Nutzerprovisionierung ist implementiert (anlegen, ändern, deaktivieren,
> deprovisionieren) mit Synchronisationsstatus je Nutzer. Die vollständige
> SCIM-2.0-Protokollkonformität verifizieren wir derzeit.

**D3 · MFA?** 🟢
> Ja. TOTP nach RFC 6238 mit Backup-Codes, plus Step-up-Authentifizierung für
> privilegierte Aktionen. Bei Anbindung an Entra ID gelten zusätzlich Ihre eigenen
> Conditional-Access-Richtlinien.

**D4 · Rollenmodell?** 🟢
> Zehn Rollen von Viewer bis Super-Admin mit 47 einzeln zugeordneten Berechtigungen.
> Zusätzlich Funktionstrennungs-Richtlinien, Freigabe-Workflows, wiederkehrende
> Zugriffsüberprüfungen und ein separates Protokoll privilegierter Aktionen.

**D5 · Wer aus Ihrem Team kann auf unsere Daten zugreifen?** 🔴 *(bis P1-10)*
> Ein formalisiertes Support-Zugriffskonzept mit Ticketbezug, zeitlicher Begrenzung und
> für Sie sichtbarer Protokollierung ist in Umsetzung. Bis dahin regeln wir Zugriffe
> vertraglich und protokollieren sie im Audit-Trail. Wir bitten Sie, diesen Punkt in der
> Bewertung als offen zu führen.

**D6 · Break-Glass-Konten?** 🔴
> Ein formalisiertes Break-Glass-Verfahren mit Vier-Augen-Freigabe und
> Zeitbegrenzung ist in Umsetzung.

---

### E. Verschlüsselung und Schlüssel

**E1 · Verschlüsselung in transit?** 🟢
> TLS für alle Verbindungen. HSTS mit zwei Jahren und `includeSubDomains` in
> Produktion. Für Modellanbieter-Aufrufe wird HTTPS erzwungen.

**E2 · Verschlüsselung at rest?** 🟠
> Plattformseitige Verschlüsselung durch den Cloud-Anbieter für Datenbank und
> Objektspeicher. Eine zusätzliche applikationsseitige Verschlüsselung für
> Nachweisdateien wird mit dem Modus `EU Sovereign` eingeführt.

**E3 · Kundenverwaltete Schlüssel (BYOK/CMK)?** 🔴
> Nicht verfügbar. Vorgesehen für den Modus `EU Sovereign`.

**E4 · Wie verwalten Sie Schlüssel?** 🟠
> Signaturschlüssel für Nachweispakete werden mit Schlüsselkennung geführt, sodass
> Signaturen auch nach Rotation prüfbar bleiben. Zugangsschlüssel werden nur als Hash
> gespeichert und nie im Klartext protokolliert. Eine Anbindung an einen dedizierten
> Schlüsseldienst ist in Umsetzung.

---

### F. Protokollierung, Audit, Nachweise

**F1 · Werden alle Änderungen protokolliert?** 🟢
> Ja. Der Audit-Trail erfasst je Ereignis Mandant, Handelnden, Rolle, Aktion,
> Objekttyp, Objekt-ID, Vorher-/Nachher-Zustand, Ergebnis, IP-Adresse, User-Agent,
> Korrelations-ID und Zeitstempel.

**F2 · Ist der Audit-Trail manipulationssicher?** 🟠
> Jeder Eintrag ist über eine SHA-256-Kette mit dem vorherigen verknüpft; eine
> Prüffunktion validiert die Kette und benennt den ersten inkonsistenten Eintrag.
> Änderungen und Löschungen sind auf Applikationsebene unterbunden.
>
> **Grenze, die wir offen benennen:** Diese Sperre wirkt auf Applikationsebene.
> Datenbankseitige Unveränderlichkeit und ein externer Zeitstempel-Anker sind in
> Umsetzung. Wir sagen deshalb „Manipulation ist erkennbar", nicht „Manipulation ist
> unmöglich".

**F3 · Können Sie die Unverfälschtheit hochgeladener Nachweise belegen?** 🟢
> Ja. Jede Datei erhält beim Upload einen SHA-256-Prüfwert. Über einen
> Verifikationsaufruf rechnet die Plattform den Wert neu und meldet `verified`,
> `mismatch` oder `unverifiable`.

**F4 · Können Sie einen Stand zu einem Stichtag rekonstruieren?** 🟢
> Ja. Berichte werden als versionierte Momentaufnahmen gespeichert, ergänzt um eine
> Metrik-Historie.

**F5 · Exportieren Sie Logs in ein SIEM?** 🔴
> Ein standardisierter SIEM-Export ist derzeit nicht verfügbar. Audit-Daten können
> über API und Exportfunktionen abgerufen werden.

---

### G. Datenschutz

**G1 · AVV nach Art. 28?** 🔴 *(bis P0-8)*
> Ein AVV-Muster mit Anlagen zu Verarbeitungsübersicht, TOM und Subprozessoren wird
> derzeit erstellt und rechtlich geprüft.

**G2 · TOM nach Art. 32?** 🔴 *(bis P0-8)*

**G3 · Aufbewahrungsfristen?** 🔴 *(bis P0-5)*
> Konfigurierbare Aufbewahrungsregeln je Datenkategorie mit Legal-Hold und
> protokollierter Löschung sind in Umsetzung. **Wir haben derzeit kein implementiertes
> Löschkonzept** und führen diesen Punkt in unserer eigenen Bewertung als offen.

**G4 · Wie unterstützen Sie Betroffenenrechte?** 🔴 *(bis P1-8)*

**G5 · Was passiert bei Vertragsende?** 🔴 *(bis P0-5)*

**G6 · Verwenden Sie unsere Daten für KI-Training?** 🟢
> Nein. Wir trainieren keine Modelle mit Kundendaten und geben keine Kundendaten zu
> Trainingszwecken weiter.

**G7 · Werden personenbezogene Daten an Sprachmodelle übertragen?** 🟢
> KI-Funktionen sind standardmäßig deaktiviert. Sind sie aktiv, prüft die Plattform
> jeden Text vor dem Aufruf auf Muster, die auf personenbezogene Daten hindeuten
> (E-Mail-Adressen, IBAN-ähnliche Zeichenfolgen, Telefonnummern) und **blockiert** den
> Aufruf bei einem Treffer.
>
> **Grenze:** Die Erkennung ist musterbasiert. Namen, Adressen oder Personalnummern im
> Fließtext erkennt sie nicht zuverlässig. Wir kommunizieren das im Produkt an jeder
> KI-Funktion.

---

### H. Betrieb, Verfügbarkeit, Notfall

**H1 · SLA?** 🔴
**H2 · RPO/RTO?** 🔴 *(bis P0-7)*
**H3 · Wann haben Sie den Restore zuletzt getestet?** 🔴 *(bis P0-7)*
> Ein dokumentiertes Restore-Testverfahren wird mit dem produktiven
> Deployment-Modell eingeführt. Ein Backup ohne getesteten Restore ist in einer Prüfung
> wertlos — deshalb sagen wir hier nichts zu, was wir nicht belegen können.

**H4 · Statusseite?** 🔴
**H5 · Incident-Response-Plan?** 🔴
**H6 · Melden Sie uns Sicherheitsvorfälle?** 🟠
> Ja, vertraglich zugesichert. Konkrete Fristen regeln wir im AVV; unser Ziel ist
> unverzüglich, spätestens innerhalb von 24 Stunden nach Kenntnis.

---

### I. Sichere Entwicklung

**I1 · Wie sichern Sie den Entwicklungsprozess?** 🟢 — **Stärke, offensiv nutzen**
> Jede Codeänderung durchläuft automatisiert:
> - statische Sicherheitsanalyse (Bandit, CodeQL)
> - Abhängigkeitsprüfung (pip-audit, npm audit, Dependency Review)
> - Lint- und Formatprüfung ohne Toleranz für Warnungen
> - vollständige Testsuite (Backend und Frontend)
> - Policy-Tests (Open Policy Agent)
> - PostgreSQL-Isolationstest gegen eine echte Datenbank
> - Produktions-Build-Gate, das bei fehlenden Rechts-, Auth-, Host- oder
>   Datenschutzangaben abbricht
>
> Alle externen CI-Aktionen sind auf Commit-Hash gepinnt. Abhängigkeiten werden
> wöchentlich automatisiert aktualisiert. Secret Scanning und Push Protection sind aktiv.

**I2 · SBOM?** 🟠
> Ein Abhängigkeitsgraph ist verfügbar; ein signiertes SBOM-Artefakt je Release ist in
> Umsetzung.

**I3 · Penetrationstest?** 🔴
> Es wurde noch kein externer Penetrationstest durchgeführt. Er ist vor dem ersten
> Enterprise-Einsatz vorgesehen.

**I4 · Melden von Schwachstellen?** 🟢
> Über `/.well-known/security.txt` und unsere Responsible-Disclosure-Seite.

---

## Teil 2 — Die 50 kritischsten Kundenfragen

Sortiert nach Häufigkeit im DACH-Markt. **Status heute: 🟢 20 · 🟠 12 · 🔴 18.**

| # | Frage | Status |
|---|---|---|
| 1 | Wo liegen unsere Daten? | 🟠 |
| 2 | Wer sind Ihre Subprozessoren? | 🔴 |
| 3 | Bekommen wir einen AVV? | 🔴 |
| 4 | Haben Sie ein TOM-Dokument? | 🔴 |
| 5 | Sind Sie ISO 27001 zertifiziert? | 🔴 |
| 6 | Wann war Ihr letzter Pentest? | 🔴 |
| 7 | Wie ist die Mandantentrennung umgesetzt? | 🟠 |
| 8 | Wie prüfen Sie die Mandantentrennung? | 🟠 |
| 9 | Wie lange speichern Sie unsere Daten? | 🔴 |
| 10 | Was passiert bei Vertragsende? | 🔴 |
| 11 | Verwenden Sie unsere Daten für KI-Training? | 🟢 |
| 12 | Können wir KI-Funktionen abschalten? | 🟢 |
| 13 | Werden personenbezogene Daten an LLMs übertragen? | 🟢 |
| 14 | Welche LLM-Anbieter nutzen Sie? | 🟢 |
| 15 | Unterstützen Sie SSO? | 🟠 |
| 16 | Unterstützen Sie SAML? | 🔴 |
| 17 | Unterstützen Sie SCIM? | 🟠 |
| 18 | Gibt es MFA? | 🟢 |
| 19 | Wie granular ist das Rollenmodell? | 🟢 |
| 20 | Gibt es einen Audit-Trail? | 🟢 |
| 21 | Ist der Audit-Trail manipulationssicher? | 🟠 |
| 22 | Können wir Audit-Logs exportieren? | 🟢 |
| 23 | Können Sie Nachweisintegrität belegen? | 🟢 |
| 24 | Werden Uploads auf Schadsoftware geprüft? | 🔴 |
| 25 | Verschlüsselung at rest? | 🟠 |
| 26 | Verschlüsselung in transit? | 🟢 |
| 27 | Kundenverwaltete Schlüssel? | 🔴 |
| 28 | RPO/RTO? | 🔴 |
| 29 | Wann wurde der Restore zuletzt getestet? | 🔴 |
| 30 | Gibt es eine SLA? | 🔴 |
| 31 | Gibt es eine Statusseite? | 🔴 |
| 32 | Wie melden Sie uns Vorfälle? | 🟠 |
| 33 | Wer im Support sieht unsere Daten? | 🔴 |
| 34 | Ist Support-Zugriff protokolliert und für uns sichtbar? | 🔴 |
| 35 | Support-Standort? | 🟠 |
| 36 | Wie sichern Sie Ihren Entwicklungsprozess? | 🟢 |
| 37 | SAST/DAST/SCA im Einsatz? | 🟢 |
| 38 | Gibt es ein SBOM? | 🟠 |
| 39 | Wie schnell patchen Sie kritische Schwachstellen? | 🟠 |
| 40 | Wie melden wir Schwachstellen? | 🟢 |
| 41 | Können wir Daten exportieren? | 🟠 |
| 42 | Gibt es eine API? | 🟢 |
| 43 | Sind Sie selbst NIS2-betroffen? | 🟠 |
| 44 | Führen Sie ein eigenes KI-Register? | 🔴 |
| 45 | Werden Beschäftigtendaten erfasst? | 🟢 (Antwort: ja, offen benennen) |
| 46 | Sind Leistungsauswertungen möglich? | 🟢 (Antwort: technisch möglich) |
| 47 | Gibt es eine Muster-Betriebsvereinbarung? | 🔴 |
| 48 | Referenzkunden vergleichbarer Größe? | 🔴 |
| 49 | Escrow bei Insolvenz? | 🔴 |
| 50 | Können Sie On-Premises betrieben werden? | 🟠 |

**Nach vollständigem P0 wandern 14 der 18 🔴 auf 🟢 oder 🟠.** Übrig bleiben:
ISO-Zertifizierung (Nr. 5), Referenzen (48), Escrow (49) und BYOK (27) — drei davon
sind Zeit- oder Vertragsfragen, keine technischen.

---

## Teil 3 — Die 20 Sales-Red-Flags

Situationen, in denen der Deal abzubrechen, zu verschieben oder umzuqualifizieren ist.
Ein Vertriebler, der diese Liste kennt, verbrennt weniger Zeit — und weniger Kontakte.

### Sofort abbrechen oder verschieben

1. **„Wir brauchen ISO 27001 vom Anbieter."** — Nicht vorhanden. Ehrlich sagen,
   Wiedervorlage in 12 Monaten setzen.
2. **„Legen Sie den Pentestbericht vor."** — Nicht vorhanden. Nicht durch andere
   Dokumente zu ersetzen versuchen.
3. **„Wir dürfen keine US-Dienstleister einsetzen."** — Im Standardmodus nicht
   erfüllbar. `EU Sovereign` als Projekt anbieten oder gehen.
4. **„Unsere Daten müssen in unserem Rechenzentrum bleiben."** — `Strict Sovereign`
   ist noch nicht verfügbar. Als Design-Partnerschaft qualifizieren oder verschieben.
5. **„Zeigen Sie drei Referenzen unserer Größe."** — Nicht vorhanden. Als Erstkunde
   mit Konditionsvorteil positionieren oder verschieben.
6. **„Wir brauchen 99,9 % SLA mit Pönale."** — Ohne Deployment-Nachweis nicht
   zusagbar. Niemals aus dem Bauch zusagen.
7. **„Können Sie das bis [Regulierungsfrist] garantieren?"** — Keine Zusagen zu
   Fristerfüllung. Das ist eine Compliance-Aussage über den Kunden, nicht über das
   Produkt.

### Umqualifizieren

8. **„Ersetzt das unseren Datenschutzbeauftragten?"** — Nein, und wer das sucht, ist
   der falsche Kunde. Umlenken auf „macht die Arbeit Ihres DSB wiederholbar".
9. **„Wir wollen, dass die KI die Klassifizierung macht."** — Widerspricht der
   Produktphilosophie und der eigenen AI-Act-Position. Klar abgrenzen.
10. **„Wir brauchen Rechtsberatung dazu."** — RDG-Grenze. An Partner verweisen.
11. **„Können wir das erst mal kostenlos testen, unbegrenzt?"** — Signal fehlender
    Kaufabsicht. Zeitlich begrenzter Pilot mit definiertem Ergebnis.
12. **„Wir wollen das komplett anders — bauen Sie uns das?"** — Custom-Development
    ist ein anderes Geschäftsmodell. Bewusst entscheiden.

### Vorsichtig weiterarbeiten

13. **Betriebsrat wurde nicht eingebunden** — wird den Deal später um Monate
    verzögern. Früh selbst ansprechen und Muster-Betriebsvereinbarung anbieten.
14. **Kein benannter Projektverantwortlicher** — Compliance-Projekte ohne Owner
    scheitern; das fällt auf das Produkt zurück.
15. **Einkauf ist noch nicht involviert bei > 25.000 € Jahreswert** — der Deal ist
    nicht so weit, wie er wirkt.
16. **„Wir haben schon [GRC-Tool] und wollen wechseln"** — Migrationsaufwand und
    Datenübernahme früh klären, sonst platzt es im Rollout.
17. **Ausschreibung mit Zertifizierungsanforderung als K.-o.-Kriterium** — nicht
    teilnehmen; die Zeit ist verloren.
18. **Kunde will alle fünf Normen gleichzeitig einführen** — überfordert jede
    Organisation. Auf einen Bereich fokussieren, sonst wird der Pilot zum Misserfolg.
19. **Kunde erwartet automatische Behördenmeldung** — existiert nicht und ist von
    Behördenschnittstellen abhängig. Früh klarstellen.
20. **Kunde will das Tool als alleinigen Nachweis gegenüber der Aufsicht** —
    gefährliches Missverständnis. Es liefert Nachweisstrukturen, nicht die
    Konformitätsfeststellung. Schriftlich klarstellen.

---

## Teil 4 — Ehrlichkeitsregel für den Vertrieb

**Verbindlich für alle Fragebogenantworten:**

Wenn eine Antwort 🔴 ist, gilt genau ein Muster:

> „Das haben wir heute nicht. [Was stattdessen existiert.] [Wann es kommt, falls
> geplant.] Wir bitten Sie, diesen Punkt in Ihrer Bewertung als offen zu führen."

**Niemals:**
- Ausweichen („das können wir individuell besprechen")
- Umdeuten („wir haben etwas Vergleichbares")
- Auf die Zukunft verschieben ohne Termin („kommt bald")
- Eine Frage mit einer anderen Antwort beantworten

**Warum das kommerziell die bessere Strategie ist:** Der Prospect wird die Lücke ohnehin
finden — spätestens im technischen Deep-Dive oder in der Vertragsverhandlung. Eine früh
zugegebene Lücke kostet ein Feature. Eine spät entdeckte Beschönigung kostet den Deal
**und** die Referenz **und** die Empfehlung im Netzwerk.

Im DACH-Compliance-Markt sind die Käufer Menschen, deren Beruf das Prüfen von
Behauptungen ist. Zurückhaltung ist hier kein Nachteil — sie ist die Eintrittskarte.
