# Wave 23 – Homepage-Content, CTAs & geplante Assets

**Ziel:** Inhalt und Kontaktwege schärfen, **ohne** Layout-, Design- oder CSS-System am Next.js-Frontend umzubauen. Kanonische Homepage: [https://complywithai.de/](https://complywithai.de/).

**Code (Implementierung):**

- Startseite: `frontend/src/app/page.tsx`
- Produktvorschau (Hero rechts): `frontend/src/components/home/HomeProductPreview.tsx`
- Globale Meta-Beschreibung: `frontend/src/app/layout.tsx`
- Öffentlicher Kontakt (eine Quelle): `frontend/src/lib/publicContact.ts` → `PUBLIC_CONTACT_MAILTO`
- Footer-Link „Kontakt“: `frontend/src/components/sbs/SbsFooter.tsx`
- Optionaler Sales-One-Pager (statisch, gleiche Tokens wie Wave 22): `website/sales-one-pager.html` (CSS: `website/css/compliancehub-landing.css`)

---

## 1. Copy-Anpassungen (überblick)

| Bereich | Änderung |
| ------- | -------- |
| **Hero-Lead** | Von „umzusetzen“ zu **Vorbereitung und strukturierte Dokumentation**; Kurzdisclaimer **keine Rechtsberatung** (an Statement Library / Wave 20 angelehnt). |
| **Drei Gründe – Karte 3** | Titel von „Evidence auf Knopfdruck“ zu **„Evidence strukturiert bereitstellen“**; Text um **Review/Prüfung** ergänzt (weniger „Magic“-Konnotation, Tone of Voice). |
| **Datenfluss – Engine** | Klarstellung **unterstützend**, keine automatische Rechtsbewertung. |
| **Integrationen – Fußzeile** | Verweis **„Kontakt aufnehmen“** als `mailto:` statt nur statischem Hinweis. |
| **Mid-CTA-Kachel** | Erster Button **„Demo anfragen“** (`mailto`); Hinweis auf **Pakete** AI Act Readiness bis Enterprise Connectors; **„Mandant öffnen“** ohne Pfeil (Label bereinigt). |
| **Security-Abschnitt** | „adressiert“ → **„unterstützt bei der Einordnung“** (vorsichtigere Regulatory-Formulierung). |
| **Meta-Description** | „DATEV-ready Exporte“ → **Exportpfade für Kanzlei-DMS** + Kurzdisclaimer (Library-konform zu DATEV-Claims). |
| **HomeProductPreview (Tabs)** | EU-AI-Tab: Einsatzszenario; Berater-Tab: **DATEV-taugliche Strukturen projektabhängig**, keine Zertifizierung. |

---

## 2. Geplante visuelle Assets (ohne Layout-Änderung)

Bestehende Slots beibehalten; folgende **Dateien/Konzepte** für spätere Produktion vorgesehen (Platzhalter nur in dieser Doku):

| # | Ort auf der Homepage | Vorschlag Dateiname | Kurzbeschreibung |
| --- | -------------------- | ------------------- | ---------------- |
| 1 | **Hero rechts** (ersetzt/ergänzt die reine `HomeProductPreview`-Mock-UI) | `docs/marketing/screenshots/home-hero-board-kpis.png` (oder `/public/marketing/…`) | Echter Screenshot **Board KPIs** oder **Compliance Overview** (Demo-Mandant, anonymisiert) – Vertrauen ohne neue Raster. |
| 2 | **Zwischen „Drei Gründe“ und „Datenfluss“** oder **unter Datenfluss** | `docs/marketing/diagrams/home-dataflow-scope-to-output.svg` | Einfaches **Architektur-Band**: Scope → Inventory → Engine → Output (Text/Icons wie im UI, exportierbar für Marketing). |
| 3 | **Security-Block rechts** („Infrastruktur-Snapshot“) | `docs/marketing/diagrams/home-hosting-eu-de.svg` | Schematischer **Hosting-/Tenant-Slice** (Vercel EU / Postgres RLS / DE-Compute) – nur inhaltliche Ersetzung der drei Kacheln durch ein Bild *optional*; Layout der Kacheln beibehalten, bis entschieden. |

**Hinweis:** Keine neuen Section-Container eingeführt; Assets ersetzen später Inhalte **innerhalb** bestehender Komponenten oder werden per `next/image` in vorhandene Flächen gelegt (Follow-up-Task).

---

## 3. CTAs – stabil vs. temporär

| CTA / Link | Ziel | Status |
| ---------- | ---- | ------ |
| **Demo anfragen** (Hero, Mid-CTA, One-Pager, statische Wave-22-Seite) | `mailto:kontakt@complywithai.de` via `PUBLIC_CONTACT_MAILTO` | **Temporär stabil**, bis Postfach/Formular/CRM final ist |
| **Board öffnen** | `/board/kpis` | **Stabil** (Produkteintritt) |
| **Board-Ansicht** (Mid-CTA) | `/board/kpis` | **Stabil** |
| **Mandant öffnen** | `/tenant/compliance-overview` | **Stabil** (Workspace-Einstieg) |
| **Kontakt** (Footer) | gleiches `mailto:` | **Temporär stabil** |
| **Kontakt aufnehmen** (Integrationen) | gleiches `mailto:` | **Temporär stabil** |
| **5-Minuten Produkt-Tour** | *entfernt aus Hero zugunsten zweier klarer CTAs*; Tour weiter über **Board/Navigation** erreichbar | Bewusst **vereinfacht**; optional später wieder als dritter Link oder Header-Link |

**SKU-Bezug:** Mid-CTA-Text nennt explizit **AI Act Readiness**, **Governance & Evidence**, **Enterprise Connectors** (Abgleich Wave 19/20).

---

## 4. Sales One-Pager

- **Datei:** `website/sales-one-pager.html`
- **Stil:** Wiederverwendung von `website/css/compliancehub-landing.css` und `landing-theme.js` (kein neues Layout-System).
- **Nutzung:** Direktlink an Prospects (lokal hosten oder statisch deployen); kanonische Referenz bleibt **complywithai.de**.

---

## 5. Abgleich GTM

- **Tone of Voice:** `docs/gtm/tone_of_voice_de.md`
- **Statements:** `docs/gtm/statements/statements.v1.json`, `docs/gtm/compliance-statement-library-de.md`
- **Website-Messaging-Rohbau:** `docs/gtm/wave20-website-messaging-de.md`
- **Statische Referenz-Landing:** `website/compliancehub-landing.html`, `docs/gtm/wave22-landingpage-notes.md`

---

*Wave 23 – Content & Asset-Planung; kein Redesign.*
