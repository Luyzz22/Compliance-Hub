# Wave 22 – Landingpage (statisch)

**Artefakt:** [`website/compliancehub-landing.html`](../../website/compliancehub-landing.html)  
**Assets:** [`website/css/compliancehub-landing.css`](../../website/css/compliancehub-landing.css), [`website/js/landing-theme.js`](../../website/js/landing-theme.js)

**Lokal öffnen:** Datei im Browser laden (relative Pfade zu CSS/JS setzen voraus, dass der Pfad `website/` als Root oder mit lokalem Server dient – z. B. `cd website && python3 -m http.server 8080`).

---

## Kanonische Mainpage (Produktion)

**https://complywithai.de/** ist die **kanonische Mainpage** und **primäre produktionsnahe Homepage** des Compliance-AI-Projekts — die öffentliche, markenführende Website (u. a. Board, Workspace, Produkt-Einstieg).

| | |
| --- | --- |
| **URL** | [https://complywithai.de/](https://complywithai.de/) |
| **Rolle** | Primäre Website-Referenz für GTM- und Website-Dokumentation (Wave 20/22). |

Die statische Datei `website/compliancehub-landing.html` bleibt ein **Quell-Artefakt** im Repository (GTM- und Statement-Alignment); sie ist **kein** Ersatz für die kanonische Homepage und wird nicht automatisch unter derselben Domain ausgeliefert. **Wave 20** und **Wave 22** behandeln **complywithai.de** als **primäre Website-Referenz**; CTAs und Footer im statischen HTML sollten sich an Kontakt- und Rechtstexte der Live-Site angleichen, sobald konsolidiert (z. B. Platzhalter `mailto:kontakt@example.com` ersetzen).

---

## Verwendete GTM- und Compliance-Quellen

| Quelle | Verwendung auf der Seite |
| ------ | ------------------------ |
| [`wave20-website-messaging-de.md`](./wave20-website-messaging-de.md) | Hero-Headline und -Subline, Meta-Description, Paket-Bullets, Drei-Schritte-Logik, Abschlusssatz unter dem Ablauf |
| [`statements/statements.v1.json`](./statements/statements.v1.json) | Hero-Aside: `CSL-DE-CORE-001`, `CSL-DE-CORE-002`, `CSL-DE-CORE-003` wörtlich; Disclaimer-Block: `CSL-DE-DIS-001`, `CSL-DE-DIS-002` inhaltlich (leicht redaktionell mit drittem Absatz zu Werkzeug/Audit-Trail ergänzt) |
| [`tone_of_voice_de.md`](./tone_of_voice_de.md) | Tonalität: sachlich, DACH-Enterprise, keine Hype-Formulierungen |
| [`wave20-sales-deck-outline.md`](./wave20-sales-deck-outline.md) | Produktlandschafts-Streifen (Advisor → Evidence → GRC → KI-Register → Reports) |
| [`compliance-statement-library-de.md`](./compliance-statement-library-de.md) | Abgleich bei zukünftigen Textänderungen |

**Hinweis:** `CSL-DE-DIS-001` und `CSL-DE-DIS-002` sind in der Library mit `needs_legal_review` markiert – vor Go-Live **Legal/Compliance** erneut prüfen lassen.

---

## Bewusst konservative Copy-Entscheidungen

- Keine Kundenzahlen, keine Testimonials, keine Sterne, keine Logo-Leiste.
- Keine „garantierte Konformität“, keine Zertifizierungsclaims für SAP/DATEV.
- Enterprise-/Kanzlei-Abschnitte betonen **Projektumfang**, **Abstimmung mit Steuerberater** bzw. **keine Produktzertifizierung**.
- CTA **„Demo anfragen“** mit **Platzhalter-E-Mail** (`kontakt@example.com`) – vor Produktion ersetzen.
- Fußzeile: **Datenschutz** als toter Link-Platzhalter.

---

## Später ergänzen (nicht Teil von Wave 22)

- Echte **Kontaktdaten**, ggf. Formular oder Kalenderlink.
- Verbindliche **Datenschutz-** und **Impressums**-Seiten (rechtlich).
- **Screenshots** oder kurze Produkt-Visuals (Register, Board-Report) – sobald freigegeben.
- **Case Studies** mit mandantenfreigegebenen Namen.
- Optionale **Pricing**-Seite (verweist auf Wave 19 intern, nicht öffentliche Preise ohne Freigabe).
- Optional: Deployment der statischen HTML-Datei (eigener Pfad/Host) — die **kanonische Mainpage** des Projekts bleibt [complywithai.de](https://complywithai.de/).
- **Canonical / SEO** auf der Live-Site und ggf. `hreflang`, wenn mehrsprachig.

---

## Pflege

- Textänderungen an der Seite: zuerst **Statement Library** aktualisieren oder neue `statement_id` anlegen, dann HTML anpassen und IDs in diesem Dokument notieren.
- Theme-Script speichert Präferenz unter `localStorage` key `compliancehub-theme`.

---

*Wave 22 – erste produktionsnahe Marketing-Landingpage.*
