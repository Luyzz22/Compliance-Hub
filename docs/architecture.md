# ComplianceHub Architektur

## Zielbild
ComplianceHub stellt einen offline-faehigen Core bereit und erweitert ihn optional um eine API-Schicht.
Der Fokus liegt auf revisionssicherer Dokumentenaufnahme, Audit-Trails und klaren Governance-Hooks.

## Komponenten
- Core Services: Regel-Engine, Audit-Hashing, Risiko-Scoring
- API Layer (optional): FastAPI-Endpunkte fuer Health und Dokumentenaufnahme
- Data Stores (geplant): WORM-Archiv, Audit-Log, Tenant-Config
- Integrationen (geplant): ERP, E-Rechnung, Datenraum

## Datenfluss (MVP)
1. Dokument wird mit Metadaten aufgenommen.
2. Core bewertet Anforderungen (DSGVO, GoBD, E-Rechnung).
3. Aktionen werden abgeleitet und protokolliert.
4. Audit-Hash wird fuer unveraenderbare Nachweise gespeichert.

## Sicherheit und Compliance
- Offline-faehiger Kern ohne Cloud-Abhaengigkeit.
- Hash-basierte Nachweisfuehrung fuer Revisionssicherheit.
- Governance-Hooks fuer Risiko- und Freigabeprozesse.

## Deployment
- Lokale Installationen oder private Cloud.
- API als optionales Add-on via `.[api]`.
