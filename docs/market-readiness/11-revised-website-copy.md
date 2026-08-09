> **Status dieses Dokuments:** Textentwurf. Vor Veröffentlichung durch qualifizierte
> Rechtsberatung prüfen lassen — insbesondere alle Passagen mit Normbezug, das
> Impressum, die Datenschutzerklärung und die AGB. Alle Claims sind gegen
> `02-claim-vs-proof-matrix.md` belegt; ändert sich der Code, ändert sich der Text.

# 11 – Überarbeitete Website-Texte

**Grundlage:** `10-messaging-redlines.md`. Jeder Claim hier ist heute belegbar oder als
Typ B/C/D gekennzeichnet.

**Produktname:** In diesem Entwurf durchgängig **ComplyWithAI** (siehe `10` §7 zur
Namenskonsolidierung).

**Betriebsmodus:** Die Texte gehen vom Modus `Standard DACH Compliance` aus. Formuliert
ist so, dass beim Wechsel in `EU Sovereign` nur ergänzt, nicht widerrufen werden muss.

---

## 1. Homepage Hero

### Variante A — Nutzenversprechen (empfohlen)

> **KI-Governance, die einer Prüfung standhält.**
>
> ComplyWithAI verbindet KI-Systeme, regulatorische Pflichten, Kontrollen und Nachweise
> in einem Arbeitsraum — für EU AI Act, NIS2, DSGVO, ISO 27001/27701 und ISO 42001.
> Sie erfassen einmal und berichten in jede Norm.
>
> Die Plattform strukturiert und bereitet auf. Die Bewertung und die Freigabe bleiben
> bei Ihnen.
>
> [Demo vereinbaren] [Trust Center ansehen]

### Variante B — Differenzierung (für datenschutzsensible Kanäle)

> **Compliance-Software, die bei KI zuerst „nein" sagt.**
>
> KI-Funktionen sind bei ComplyWithAI standardmäßig deaktiviert. Wenn Sie sie
> einschalten, blockiert die Plattform Modellaufrufe, sobald personenbezogene Muster im
> Text erkannt werden. Alles andere — KI-Register, Risikoklassifizierung, Kontrollen,
> Nachweise, Board-Reports — funktioniert ohne jedes Sprachmodell.
>
> [Demo vereinbaren] [Trust Center ansehen]

**Warum Variante B stark ist:** Sie ist prüfbar (`COMPLIANCEHUB_FEATURE_LLM_ENABLED=false`,
`COMPLIANCEHUB_LLM_PII_MODE=block`), sie ist im Markt selten, und sie beantwortet die
erste Frage jedes Datenschutzbeauftragten, bevor sie gestellt wird.

**Vertrauensleiste unter dem Hero:**

> Betrieb in EU-Rechenzentren · KI-Funktionen standardmäßig aus · Audit-Trail mit
> Integritätsprüfung · Subprozessoren vollständig offengelegt

---

## 2. Value Proposition

> ### Ein Kontrollmodell statt fünf Excel-Tabellen
>
> Die meisten Organisationen führen EU AI Act, NIS2, DSGVO und ISO getrennt — mit
> getrennten Listen, getrennten Nachweisen und getrennten Terminen. Dieselbe Kontrolle
> wird dreimal dokumentiert und beim vierten Audit trotzdem nicht gefunden.
>
> ComplyWithAI führt Anforderungen aus allen Normen auf ein gemeinsames Kontrollmodell
> zurück. Sie hinterlegen einen Nachweis einmal und sehen sofort, auf welche
> Anforderungen aus welchen Normen er einzahlt.
>
> **Was das konkret bedeutet:**
> - Ein KI-System erfassen, nicht fünfmal beschreiben
> - Ein Nachweis, mehrere Normbezüge
> - Ein Termin, alle betroffenen Pflichten
> - Ein Board-Report statt fünf Zuarbeiten

---

## 3. Produktmodule

### KI-Register und Risikoklassifizierung

> Erfassen Sie Ihre KI-Systeme mit den Feldern, nach denen die KI-Verordnung fragt:
> Zweckbestimmung, Herkunft der Trainingsdaten, Anbieter- und Betreiberrolle, Verweis
> auf die Grundrechte-Folgenabschätzung, Status der Nachmarktbeobachtung.
>
> Die Plattform schlägt eine Risikostufe entlang der Logik von Art. 6 und Annex I/III
> vor und macht den Weg zu diesem Vorschlag nachvollziehbar.
>
> **Was Sie verantworten:** Die rechtliche Einstufung bestätigen Sie selbst — mit
> Begründung, Datum und Namen. Die Plattform hält diesen Nachweis fest; sie trifft die
> Entscheidung nicht.

### Kontrollen und Nachweise

> Verknüpfen Sie Anforderungen mit Kontrollen, Kontrollen mit Nachweisen und Nachweise
> mit Verantwortlichen. Reviews wiederholen sich auf derselben Datenbasis, statt jedes
> Mal neu zusammengesucht zu werden.
>
> Jede hochgeladene Datei erhält beim Upload einen SHA-256-Prüfwert. Auf Knopfdruck
> weist die Plattform nach, dass eine Nachweisdatei seit dem Upload unverändert ist.

### Aufgaben, Fristen und Eskalation

> Aus Lücken werden Aufgaben mit Verantwortlichem, Termin und Eskalationsstufe. Bei
> Sicherheitsvorfällen berechnet die Plattform die Meldefristen **ab dem Zeitpunkt
> Ihrer Kenntniserlangung** — nicht ab dem Zeitpunkt der Erfassung im Tool.
>
> **Was Sie verantworten:** Die Meldung an die zuständige Behörde nehmen Sie selbst
> vor. Die Plattform berechnet Fristen, erinnert, eskaliert und dokumentiert.

### Board-Reports und Prüfungsvorbereitung

> Versionierte Berichtsstände mit Metrik-Historie: Sie können belegen, wie der Stand zu
> einem bestimmten Zeitpunkt war. Für Prüfer stellen Sie ein Nachweispaket zusammen —
> mit Zugriffsprotokoll, wer wann was gesehen hat.

### Mandanten-Portfolio für Berater und MSPs

> Beratungshäuser und Managed-Service-Provider führen alle Mandanten in einem Workspace,
> vergleichen deren Reifegrad und erzeugen wiederholbare Berichte. Jeder Mandant bleibt
> vollständig getrennt.

---

## 4. Sicherheit und Hosting

> ## Wo Ihre Daten liegen — und wer darauf zugreifen kann
>
> ### Betrieb
> ComplyWithAI wird in EU-Rechenzentren betrieben. Die konkrete Region halten wir
> vertraglich fest.
>
> ### Unsere Dienstleister und deren Rechtsraum
> Wir setzen Dienstleister ein, die Daten in unserem Auftrag verarbeiten. Einige von
> ihnen sind US-Unternehmen und unterliegen damit US-Recht, auch wenn sie in EU-Regionen
> verarbeiten. Wir sagen das offen, statt es hinter „EU-Hosting" verschwinden zu lassen.
>
> Die vollständige Liste mit Sitz, Rolle und Verarbeitungszweck finden Sie im
> [Trust Center](/trust-center).
>
> ### Wenn Ihnen das nicht genügt
> Für Organisationen mit strengeren Anforderungen bereiten wir den Betriebsmodus
> **EU Sovereign** vor: vollständiger Betrieb bei EU-ansässigen Anbietern, keine
> US-kontrollierten Dienstleister im Datenpfad. Verfügbar auf Anfrage mit
> Projektvorlauf. Sprechen Sie uns an, bevor Sie sich für eine Alternative entscheiden.
>
> ### Künstliche Intelligenz
> KI-Funktionen sind **standardmäßig deaktiviert**. Sie entscheiden je Mandant, ob und
> für welche Aufgaben Sie sie einschalten.
>
> Ist eine KI-Funktion aktiv, prüft die Plattform jeden Text vor dem Modellaufruf auf
> Muster, die auf personenbezogene Daten hindeuten — E-Mail-Adressen, IBAN-ähnliche
> Zeichenfolgen, Telefonnummern. Wird ein solches Muster erkannt, wird der Aufruf
> **blockiert**, nicht durchgelassen.
>
> **Was diese Prüfung nicht leistet:** Sie ist musterbasiert. Namen, Adressen,
> Geburtsdaten oder Personalnummern im Fließtext erkennt sie nicht zuverlässig.
> Behandeln Sie sie als zusätzliche Schutzschicht, nicht als Freibrief für
> personenbezogene Inhalte in Prompts.
>
> ### Zugriffe und Nachvollziehbarkeit
> - Anmeldung über Microsoft Entra ID (OIDC) oder Benutzerkonto mit zweitem Faktor
> - Rollenmodell mit abgestuften Berechtigungen
> - Audit-Trail mit Hash-Kette; Änderungen und Löschungen sind auf Applikationsebene
>   unterbunden und nachträgliche Manipulation ist über die Kettenprüfung erkennbar
> - Nachweisdateien mit Inhalts-Prüfwert und Verifikationsfunktion
>
> ### Was wir noch nicht haben
> Wir sind vor der Zertifizierung. Es gibt heute kein ISO-27001-Zertifikat und kein
> SOC-2-Testat für unseren Betrieb. Den aktuellen Stand und den Zeitplan finden Sie im
> Trust Center. Wenn Ihre Beschaffung ein Zertifikat zwingend voraussetzt, sagen wir
> Ihnen das im ersten Gespräch — nicht in Woche acht.

---

## 5. FAQ

> **Macht ComplyWithAI mein Unternehmen DSGVO-konform?**
> Nein. Das kann keine Software. DSGVO-Konformität ergibt sich aus Ihren Prozessen,
> Verträgen, Entscheidungen und Nachweisen. ComplyWithAI liefert die Strukturen, in
> denen Sie diese Nachweise führen und wiederfinden.
>
> **Ist ComplyWithAI „AI Act ready"?**
> Diese Formulierung vermeiden wir bewusst. Die KI-Verordnung stellt Anforderungen an
> Ihre Organisation, nicht an unsere Software. Wir unterstützen Sie bei Register,
> Klassifizierung, technischer Dokumentation, Transparenzanforderungen und Nachweisen.
> Welche Pflichten Sie konkret treffen, klären Sie mit Ihrer Rechtsberatung.
>
> **Wo liegen unsere Daten?**
> In EU-Rechenzentren. Einige unserer Dienstleister sind US-Unternehmen und unterliegen
> US-Recht. Die vollständige Liste steht im Trust Center. Für Betrieb ohne
> US-kontrollierte Anbieter im Datenpfad bereiten wir den Modus `EU Sovereign` vor.
>
> **Werden unsere Daten für KI-Training verwendet?**
> Nein. Wir trainieren keine Modelle mit Kundendaten und geben keine Kundendaten zu
> Trainingszwecken weiter. KI-Funktionen sind standardmäßig deaktiviert.
>
> **Können mehrere Mandanten unsere Daten sehen?**
> Nein. Jeder Mandant hat eigene Zugangsschlüssel und Sitzungen; jeder Datenzugriff
> wird gegen die Mandantenbindung des angemeldeten Kontos geprüft. Unsere
> Cross-Tenant-Testsuite prüft das automatisiert bei jeder Codeänderung.
>
> **Was passiert mit unseren Daten, wenn wir kündigen?**
> Sie erhalten einen vollständigen Export. Nach einer vereinbarten Karenzzeit löschen
> wir Ihre Daten und bestätigen die Löschung schriftlich. Details im AVV.
>
> **Ersetzt ComplyWithAI unseren Datenschutzbeauftragten oder Berater?**
> Nein — und das ist Absicht. Die Plattform macht die Arbeit Ihres Beraters
> wiederholbar und nachweisbar. Viele unserer Kunden kommen über ihren Berater zu uns.
>
> **Bekommen wir Rechtsberatung?**
> Nein. Wir sind keine Rechtsanwaltskanzlei und erbringen keine Rechtsdienstleistungen.
> Unsere Inhalte sind fachliche Strukturierungshilfe. Rechtliche Bewertungen treffen
> Sie mit qualifizierter Beratung.
>
> **Wie starten wir?**
> Mit einem Pilot: ein klar abgegrenzter Bereich, ein definierter Zeitrahmen, ein
> messbares Ergebnis. Meist ein KI-Register mit Risikoklassifizierung für einen
> Geschäftsbereich, in vier bis sechs Wochen.

---

## 6. Trust Center

### Struktur

```
/trust-center
├── Überblick                    · Betriebsmodus, Stand, Verantwortliche
├── Sicherheit                   · Kontrollen mit Belegstelle
├── Datenschutz                  · Rollen, Rechtsgrundlagen, Betroffenenrechte
├── Subprozessoren               · Liste mit Sitz, Rolle, Jurisdiktion, Änderungshistorie
├── Datenresidenz                · Betriebsmodi und was jeder bedeutet
├── Zertifizierungen             · Was wir haben und was nicht — mit Zeitplan
├── Dokumente (NDA)              · AVV, TOM, Pentest, Architektur, DR-Plan
├── Was wir nicht können         · Bewusst prominent
├── Sicherheit melden            · security.txt, PGP, Reaktionszeiten
└── Status                       · Verfügbarkeit, letzter Restore-Test, Vorfälle
```

### Seite „Was wir nicht können"

Diese Seite ist der stärkste Vertrauensbaustein und im Markt praktisch einzigartig.

> ## Was wir heute nicht können
>
> Sie werden das in einer Sicherheitsprüfung ohnehin herausfinden. Wir sagen es lieber
> vorher.
>
> | Thema | Stand | Geplant |
> |---|---|---|
> | ISO-27001-Zertifizierung | Nicht vorhanden | In Vorbereitung |
> | SOC 2 Typ II | Nicht vorhanden | Nicht geplant (EU-Fokus) |
> | Externer Penetrationstest | Nicht durchgeführt | Vor dem ersten Enterprise-Kunden |
> | SAML 2.0 | Nicht verfügbar (Entra ID / OIDC vorhanden) | Auf Roadmap |
> | Kundenverwaltete Schlüssel (BYOK) | Nicht verfügbar | Mit Modus `EU Sovereign` |
> | Betrieb ohne US-Dienstleister | Nicht im Standardmodus | Modus `EU Sovereign`, auf Anfrage |
> | Automatische Behördenmeldung | Nicht verfügbar | Abhängig von Behördenschnittstellen |
> | Rechtsberatung | Erbringen wir nicht | Nicht geplant — wir sind keine Kanzlei |
>
> Fehlt Ihnen etwas Entscheidendes? Schreiben Sie uns. Wenn wir es nicht liefern können,
> sagen wir das im ersten Gespräch.

### Seite „Subprozessoren"

> ## Unsere Unterauftragsverarbeiter
>
> Stand: TT.MM.JJJJ · Änderungen kündigen wir 30 Tage im Voraus an.
>
> | Dienstleister | Sitz | Kontrolliert von | Zweck | Datenkategorien | Region |
> |---|---|---|---|---|---|
> | Vercel Inc. | USA | 🇺🇸 US | Auslieferung Weboberfläche, serverseitige Anfrageverarbeitung | Alle Anwendungsdaten im Transit | EU (Frankfurt) |
> | Microsoft Corporation | USA | 🇺🇸 US | Cloud-Infrastruktur, Datenbank, Objektspeicher | Alle Anwendungsdaten | EU (Deutschland) |
> | Microsoft Corporation | USA | 🇺🇸 US | Identitätsdienst (Entra ID), sofern genutzt | Anmeldedaten | EU |
> | Microsoft Corporation | USA | 🇺🇸 US | Azure OpenAI — **nur bei aktivierter KI-Funktion** | Prompt-Inhalte | EU |
>
> **Warum wir die Jurisdiktion getrennt ausweisen:** Der Serverstandort entscheidet
> nicht darüber, welches Recht auf den Anbieter anwendbar ist. Ein US-Unternehmen
> unterliegt US-Recht auch dann, wenn es in Frankfurt verarbeitet. Wir halten es für
> redlicher, das offen auszuweisen, statt es hinter „EU-Hosting" zu verbergen.
>
> **Drittlandtransfers:** Für Dienstleister mit US-Kontrolle setzen wir
> EU-Standardvertragsklauseln ein und führen eine dokumentierte
> Transfer-Folgenabschätzung. Beide Dokumente erhalten Sie auf Anfrage.

---

## 7. Datenschutzhinweise auf Produktebene

Als Einblendung im Produkt, nicht nur in der Datenschutzerklärung:

> **Beim Upload von Nachweisen**
> Laden Sie keine besonderen Kategorien personenbezogener Daten nach Art. 9 DSGVO hoch
> (Gesundheitsdaten, biometrische Daten, Gewerkschaftszugehörigkeit u. a.), sofern das
> nicht ausdrücklich mit uns vereinbart ist. Schwärzen Sie Personendaten, die für den
> Nachweis nicht erforderlich sind.

> **Bei Aktivierung einer KI-Funktion**
> Diese Funktion überträgt den eingegebenen Text an ein Sprachmodell des konfigurierten
> Anbieters. Die Plattform blockiert den Aufruf, wenn sie personenbezogene Muster
> erkennt — diese Erkennung ist musterbasiert und nicht vollständig. Geben Sie keine
> personenbezogenen Daten ein. Das Ergebnis ist ein Entwurf und muss vor Verwendung
> geprüft werden.

> **Bei jedem KI-generierten Ergebnis** *(Art. 50 KI-VO)*
> Dieser Text wurde mit Unterstützung eines Sprachmodells erstellt. Bitte inhaltlich
> prüfen und freigeben.

---

## 8. Disclaimer

**Kurzform** (Fußzeile jeder Seite):

> ComplyWithAI ist Software zur Strukturierung von Compliance-Arbeit. Wir erbringen
> keine Rechtsdienstleistungen im Sinne des RDG.

**Langform** (eigene Seite, im Footer verlinkt):

> ## Rechtlicher Hinweis
>
> **Keine Rechtsberatung.** ComplyWithAI ist ein Softwarewerkzeug. Wir sind keine
> Rechtsanwaltskanzlei, keine Steuerberatung und keine Zertifizierungsstelle und
> erbringen keine Rechtsdienstleistungen im Sinne des Rechtsdienstleistungsgesetzes.
> Sämtliche Inhalte — Klassifizierungsvorschläge, Anforderungszuordnungen,
> Reifegradbewertungen, Textentwürfe — sind fachliche Strukturierungshilfen und ersetzen
> keine qualifizierte rechtliche Prüfung.
>
> **Keine Konformitätsfeststellung.** Die Nutzung von ComplyWithAI stellt nicht fest,
> dass Ihre Organisation die Anforderungen der KI-Verordnung, der NIS2-Richtlinie, der
> DSGVO oder einer ISO-Norm erfüllt. Diese Feststellung treffen die zuständigen
> Behörden, Prüfstellen und Zertifizierer.
>
> **Keine Zertifizierung.** ComplyWithAI ist nicht zertifiziert und zertifiziert nicht.
> Bezugnahmen auf Normen beschreiben, welche Anforderungen die Software strukturiert
> abbildet.
>
> **Verantwortung für Inhalte und Entscheidungen.** Sie verantworten die Richtigkeit der
> eingegebenen Daten, die rechtliche Bewertung, die Freigabe von Dokumenten und die
> fristgerechte Erfüllung Ihrer Melde- und Nachweispflichten. Die Plattform berechnet
> Fristen aus den von Ihnen eingegebenen Zeitpunkten und erinnert daran; sie meldet
> nicht selbst an Behörden.
>
> **KI-gestützte Funktionen.** Soweit Sie KI-Funktionen aktivieren, werden Ergebnisse
> von Sprachmodellen erzeugt. Diese können unvollständig oder sachlich falsch sein. Sie
> sind als Entwurf zu behandeln und vor Verwendung zu prüfen.

---

## 9. Was ausdrücklich nicht in die Texte gehört

- Zertifizierungslogos oder -andeutungen ohne Zertifikat
- Kundenlogos ohne schriftliche Freigabe
- Erfundene oder aggregierte Kennzahlen („95 % weniger Aufwand")
- Vergleichende Aussagen über Wettbewerber ohne belastbare Grundlage
- Zeitangaben zu Regulierungsfristen ohne rechtliche Prüfung — die Anwendungszeitpunkte
  der KI-Verordnung waren zuletzt Gegenstand laufender Gesetzgebungsverfahren
- Countdown-Timer zu Regulierungsfristen (rechtlich riskant und im Zielsegment als
  Angstverkauf abgelehnt)
- „Marktführer", „führende Plattform" o. Ä. ohne Beleg
