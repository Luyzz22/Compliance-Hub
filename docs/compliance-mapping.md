# Compliance Mapping

## DSGVO (GDPR)
- Verzeichnis von Verarbeitungstaetigkeiten (VVT): Aktion `create_or_update_ropa_entry`.
- Drittstaatentransfers: Aktion `trigger_transfer_impact_assessment`.
- Zweckbindung und Minimierung: intake payload erzwingt dokumentierte Metadaten.

## GoBD
- Revisionssichere Archivierung: Aktion `append_worm_archive_record`.
- Nachvollziehbarkeit: Audit-Hash mit Zeitstempel.
- Ordnung und Unveraenderbarkeit: WORM-Archiv als Pflichtintegration.

## EU AI Act Governance Hooks
- Risk Register: Ausbau der Risiko-Scores pro Tenant.
- Human-in-the-Loop: definierte Freigabeschritte bei hoher Severity.
- Dokumentation: Audit-Log als Nachweis fuer Modell- und Regelversionen.
