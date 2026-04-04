# Wave 37 – Mandanten-Readiness-Export (Kanzlei / Berater)

Internes Artefakt für **Steuerberater, Wirtschaftsprüfer und GRC-/ISMS-Berater** in DACH: ein **mandantenbezogener** Kurzexport zur Vorbereitung wiederkehrender Beratungs- oder Prüfgespräche – **nicht** als Ersatz für den Executive-**Board Pack** (Wave 36).

## Zielgruppe und Nutzen

- Kanzleien mit **DATEV-** oder allgemeinem DMS-Workflow: Text/Markdown als **Arbeitspapier** weiterbearbeiten oder anhängen.
- Wiederkehrende **Advisor Check-ins**: gleiche Datenbasis wie Board Readiness, aber **fokussiert auf einen Mandanten** und mit **Kanzlei-Semantik** (Mandant, Prüfpunkt, Ansprechpartner).

## Unterschied zum Board Pack

| Aspekt | Board Pack (Wave 36) | Mandanten-Export (Wave 37) |
|--------|----------------------|----------------------------|
| Perspektive | Portfolio / Board-Vorbereitung | Ein Mandant / Klient |
| Ton | Executive-Memo + Aktionsregister | Beratungs- / Prüfungsnah |
| Umfang | Segmente, viele Mandanten | Nur `client_id` |
| Begriffe | Ampel, Attention | Prüfpunkt, Verantwortliche, letzter Bericht |

## Export-Struktur (4 Teile)

1. **Mandantenstatus kompakt** – Readiness-Kurzfassung (rechnerisch aus EU-AI-Act-Readiness, falls verfügbar), Zahl KI-Systeme und Hochrisiko, Governance-Reife-Orientierung (Wave-33-Logik), Hinweis zu **Ansprechpartnern / Rollen** aus dem Setup.
2. **Offene Punkte** – regelbasierte **Prüfpunkte** (fehlende Verantwortliche, Art. 9, Nachweisdokumentation, veralteter Mandanten-/Board-Report) mit **Referenz-IDs** (`HR-AI-…`, `TENANT-…`).
3. **Nächste Schritte** – kurze Vorschläge für **Mandant**, **Kanzlei** oder **gemeinsam** (manuell zu priorisieren).
4. **Nachweise & Exporthinweise** – Mandanten-ID, letzter Report aus der Liste, Referenzliste, Hinweis **DATEV/manuelle Übergabe** (kein automatischer DATEV-Upload in dieser Wave).

Technische Typen: `frontend/src/lib/mandantReadinessAdvisorTypes.ts`.  
Gemeinsame Lückenlogik mit dem Board-Dashboard: `frontend/src/lib/tenantBoardReadinessGaps.ts` (`computeMandantOffenePunkte`).

## API

`GET /api/internal/advisor/mandant-readiness-export?client_id=<mandanten_id>`

- **Auth:** wie andere interne Admin-Tools (`LEAD_ADMIN_SECRET` / Session, siehe Lead-Inbox).
- **client_id:** technische Mandanten-ID (Tenant), Validierung: alphanumerisch plus `._-`.
- **Antwort:** JSON mit `mandant_readiness_export` (Struktur + `markdown_de`).

Optional werden **Bezeichnung** und **Pilot-Flag** aus `gtm-product-account-map` ergänzt, falls ein Eintrag für dieselbe `tenant_id` existiert.

## UI

`/admin/advisor-mandant-export` – Eingabe Mandanten-ID, Vorschau der Abschnitte, Markdown kopieren / `.md` laden.  
Verlinkung von `/admin/board-readiness` möglich.

## Nutzung in der Praxis

1. Mandanten-ID aus Workspace oder Provisioning übernehmen.
2. Export erzeugen und in **Notion / Confluence / E-Mail / Kanzlei-DMS** einfügen.
3. **Vor Weitergabe** an Endkunden oder Behörden: inhaltlich und rechtlich durch die Kanzlei prüfen (Hinweis im Export).

## Grenzen

- Keine **automatische Rechtsbewertung**; Zahlen und Prüfpunkte stammen aus ComplianceHub-APIs.
- **Owner-Namen** werden nicht zuverlässig aus allen Quellen geladen; Verantwortliche ggf. im Mandantengespräch benennen.
- **DATEV:** nur Hinweis auf manuellen Prozess; spätere Anbindung (Anhänge, Schnittstellen) separat planbar.

## Siehe auch

- `docs/board/wave34-board-readiness-dashboard.md` – Datenquellen.
- `docs/board/wave36-quarterly-board-pack.md` – Portfolio-Board-Pack.
