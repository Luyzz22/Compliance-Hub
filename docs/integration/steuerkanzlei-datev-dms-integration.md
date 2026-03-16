# Steuerkanzlei / DATEV-DMS – Board-Report-Export

**Blueprint-Dokumentation.** Beschreibung der auf Steuerberater und WP-Kanzleien ausgerichteten Export-Variante für den AI-Governance-Board-Report: Mandanten-Akte, Prüfungsdokumentation, Nachweise zu EU AI Act, NIS2 und ISO 42001. **DATEV-/DMS-Ready-Format** – keine offizielle DATEV-API-Integration, aber klar strukturiert für spätere Anbindung (z. B. DATEV-Connector, Kanzlei-DMS).

---

## 1. Anwendungsfall

- **Mandanten-Akten:** Board-Report als Prüfungs-/Governance-Dokument einem Mandanten (Mandantennummer, -name, Aktenzeichen) zuordnen.
- **Prüfungsdokumentation:** Nachweis für WP-Prüfungen und Compliance-Reporting (EU AI Act, NIS2, ISO 42001).
- **DMS/Archiv:** Ablage in Kanzlei-DMS oder DATEV-nahen Systemen mit strukturierten Metadaten (Zeitraum, Normbezug, Dokumenttyp).

ComplianceHub erzeugt einen deterministischen JSON-Payload und sendet ihn per HTTP POST an eine konfigurierbare Callback-URL (z. B. Middleware oder Connector zur DATEV-/DMS-Anbindung).

---

## 2. target_system: datev_dms_prepared

Beim Anlegen eines Export-Jobs wird `target_system: "datev_dms_prepared"` gewählt. **callback_url** ist Pflicht. Optionale **metadata**-Felder steuern Mandant, Aktenzeichen, Zeitraum und Normbezug (siehe Abschnitt 3).

---

## 3. Metadaten-Schema (Job-metadata)

Die folgenden Keys können im Request-Body unter `metadata` (dict) übergeben werden. Alle Werte sind optional; fehlende werden mit Defaults gefüllt.

| Key | Typ | Beschreibung | Default |
|-----|-----|--------------|---------|
| `mandant_nr` | string | Mandantennummer / Kanzlei-Referenz | `tenant_id` |
| `mandant_name` | string | Anzeigename Mandant | leer |
| `aktenzeichen` | string | Aktenzeichen für die Ablage | leer |
| `pruefungsauftrag_id` | string | Alternative zu Aktenzeichen (Prüfungsauftrag) | – |
| `berichtszeitraum_von` | string | Beginn Berichtszeitraum (z. B. YYYY-MM-DD) | leer |
| `berichtszeitraum_bis` | string | Ende Berichtszeitraum | leer |
| `normbezug` | string | Kommagetrennte Normen | „EU AI Act,NIS2,ISO 42001“ |
| `dokument_typ` | string | Dokumenttyp für DMS | „AI Governance Board Report“ |

---

## 4. Payload-Schema (HTTP POST)

Der an die **callback_url** gesendete JSON-Body hat folgende Struktur. Keine personenbezogenen Daten, nur Aggregat- und Systemdaten.

| Top-Level-Key | Inhalt |
|---------------|--------|
| **mandant** | `mandant_nr`, `mandant_name`, `aktenzeichen` |
| **bericht** | `typ` (Dokumenttyp), `zeitraum` (period, von, bis, generated_at), `normbezug` (Array) |
| **content** | `markdown` (vollständiger Report), `summary` (z. B. ai_systems_total, board_maturity_score, risiko_level) |
| **technisch** | `tenant_id`, `export_job_id` |

**Header:** `X-ComplianceHub-Integration: datev_dms_prepared`

---

## 5. Mapping-Vorschlag auf DATEV-/DMS-Felder

| ComplianceHub-Payload | Typisches DATEV-/DMS-Feld / Verwendung |
|-----------------------|----------------------------------------|
| `mandant.mandant_nr` | Mandantennummer / Mandanten-ID |
| `mandant.mandant_name` | Bezeichnung Mandant / Akte |
| `mandant.aktenzeichen` | Aktenzeichen / Vorgangsnummer |
| `bericht.typ` | Dokumentart / Belegtyp |
| `bericht.zeitraum.von` / `.bis` | Zeitraum für Archiv/Prüfung |
| `bericht.normbezug` | Schlagwörter / Normen (EU AI Act, NIS2, …) |
| `content.markdown` | Dokumentinhalt (z. B. für PDF-Erzeugung) |
| `content.summary` | Kurzinfos für Listen/Übersichten |
| `technisch.export_job_id` | Referenz für Nachverfolgbarkeit |

Konkrete Zuordnung hängt vom jeweiligen DMS bzw. DATEV-Connector ab.

---

## 6. Hinweis zur DATEV-Integration

Dieses Format ist **„DATEV-/DMS-Ready“**: strukturiert und für die Weiterverarbeitung durch einen späteren **DATEV-Connector** oder Kanzlei-DMS vorbereitet. Es **ersetzt keine** offizielle DATEV-API-Integration. Für eine produktive Anbindung an DATEV sind die offiziellen DATEV-Schnittstellen und -Vereinbarungen zu beachten.

---

*Dokumentation: ComplianceHub Integration Blueprint – Steuerkanzlei / DATEV-DMS.*
