# Wave 30 – Attribution & Campaign Tracking (DSGVO-orientiert)

## Zweck

ComplianceHub erfasst **minimale, intern nutzbare** Hinweise dazu, **welcher Kanal und welche Kampagne** zu einer Kontaktanfrage geführt haben. Ziel ist operative Steuerung („Was lohnt sich?“), **kein** vollwertiges Ad-Attribution-Produkt und **keine** nutzerbezogenen Werbeprofile.

## Was wird erfasst?

| Datenpunkt | Herkunft | Speicherort |
|------------|----------|-------------|
| **utm_source**, **utm_medium**, **utm_campaign** | URL-Parameter beim ersten Auftreten in der **Browser-Tab-Session** (`sessionStorage`, first-party) + Fallback aus der aktuellen Kontakt-URL beim Absenden | Lead-Outbound (`schema_version` 1.2), JSONL |
| **document.referrer** (gekürzt) | Vom Browser beim Absenden des Formulars im Request-Body | Lead-Outbound |
| **HTTP Referer** (nur **Hostname**) | `Referer`-Header der POST-Anfrage an `/api/lead-inquiry` | Lead-Outbound (`referrer_host`) |
| **cta_id**, **cta_label** | Query-Parameter auf `/kontakt` (von CTAs, z. B. `contactPageHref`) | Lead-Outbound |
| **Abgeleitete Felder** `source`, `medium`, `campaign` | Serverseitige Heuristik aus UTM + Referrer (siehe `buildLeadAttribution`) | Lead-Outbound, Sync-Payload optional |

Die bestehende **Sales-„Quelle“** (`source_page` / Query `quelle`) bleibt unverändert; sie beschreibt **wo auf der Site** der Kontakt ausgelöst wurde, nicht den Marketing-Kanal.

## Was wird bewusst **nicht** gemacht?

- Keine **Drittanbieter-Pixel** oder Social-Pixel auf der Anfrage-Strecke.
- Keine **Cross-Site-Tracking**-IDs, keine **Fingerprinting**-Logik.
- Keine **dauerhaften Marketing-Cookies** für Attribution; nur **sessionStorage** für UTM-First-Touch (Tab-Sitzung).
- Kein **Multi-Touch-Attribution-Modell** (keine gewichteten Journeys).
- Keine automatische **Zuordnung zu Einzelpersonen** über Drittanbieter-Daten.

## Rechtliche Einordnung (Kurz)

- Verarbeitung erfolgt zur **Bearbeitung der Anfrage** und internen **Vertriebs-/Organisationssteuerung**; UTM/Referrer sind typischerweise **Kontext der Anfrage**, keine zusätzliche „Profiling“-Ebene über das hinaus, was ohnehin bei Server-Logs oder Formularübermittlung anfällt.
- **Transparenz:** Datenschutzhinweise sollten erwähnen, dass bei Bedarf **Referrer- und Kampagnenparameter** mitübermittelt werden können (wie üblich bei Webformularen).
- Speicherdauer richtet sich nach den **internen Aufbewahrungsregeln** für Leads (siehe allgemeine Privacy-Dokumentation).

## Interne Nutzung

- **`/admin/gtm`:** Tabellen „Attribution (30 Tage)“: Anfragen, qualifizierte Leads und Pipedrive-Deals (neu angelegt, Sync) **pro abgeleiteter Quelle** bzw. **pro Campaign-Slug** — ohne Conversion-Raten aus unvollständigen Daten.
- **`/admin/leads`:** Spalte Attribution, Detailkasten, Filter nach Quelle/Campaign/Medium.
- **Sync-Payload (optional):** Feld `attribution` im Lead-Sync-JSON für spätere **HubSpot-Feldzuordnung** (manuell in n8n/Connector konfigurierbar).

## Zukünftige Erweiterungen (ohne Tracker-Inflation)

- Mapping der gespeicherten Felder auf **HubSpot custom properties** oder Pipedrive-Felder.
- Einfache **Campaign-ROI-Ansichten** auf Basis qualifizierter Leads und Deals (weiterhin ohne Third-Party-Attribution).
- Serverseitiges **Landing-Log** nur bei Bedarf (z. B. anonymisierte Zähler), weiterhin ohne Cookies.

## Technische Referenz

- `frontend/src/lib/leadAttribution.ts` – Ableitung und Grenzen.
- `frontend/src/lib/attributionSessionClient.ts` – sessionStorage First-Touch.
- `frontend/src/components/marketing/SessionAttributionCapture.tsx` – Einbindung im Root-Layout.
- `frontend/src/app/api/lead-inquiry/route.ts` – Persistenz beim POST.

Siehe auch: [Wave 29 – Founder Dashboard](wave29-founder-dashboard.md).
