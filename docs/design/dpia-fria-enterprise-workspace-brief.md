# DSFA/FRIA Enterprise Workspace Brief

1. Primärnutzer sind Datenschutz-, Compliance- und AI-Governance-Verantwortliche, die für ein registriertes KI-System eine prüfbare Scope-, Risiko- und Freigabeentscheidung vorbereiten.
2. Die Oberfläche soll ruhig, präzise, nachvollziehbar und verantwortlich wirken. Sie darf weder Rechtsberatung noch eine automatische Freigabe suggerieren.
3. Visuelle These: Eine Assessment-Akte führt von Scope über acht gesetzlich abgeleitete Prüffelder zu Residualrisiko, Konsultationsstatus und unabhängiger Freigabe.
4. Erhalten bleiben Tenant-Navigation, KI-System-Register, Audit-Log, bestehende Header-, Karten- und Formularmuster sowie die öffentliche/Enterprise-Release-Grenze.
5. Ausgeschlossen sind erfundene Compliance-Scores, automatische Rechtsentscheidungen, generische KPI-Kartenraster, dekorative Gradienten, persönliche Reviewer-Profile und unqualifizierte Konformitätsaussagen.

Design-Dials:

- `DESIGN_VARIANCE 4`
- `MOTION_INTENSITY 2`
- `VISUAL_DENSITY 7`

## Claim-Matrix

| Aussage | Zustand | Evidenzgrenze |
| --- | --- | --- |
| Mandantenscharfe Abfragen und Writes | Verified | Repository-Filter und negative API-Tests |
| Optimistic Concurrency | Verified | Versionierter Write und HTTP-409-Test |
| Vier-Augen-Prinzip | Verified | Modellvalidierung für verschiedene Funktionsrollen |
| Atomarer Assessment- und Audit-Write | Verified | Rollback-Test bei erzwungenem Auditfehler |
| PostgreSQL-RLS | Gated | Produktionsäquivalente Migration und RLS-Test bleiben ein separates Deployment-Gate |
| Vollständige DSGVO-/EU-AI-Act-Konformität | Unsupported | Erfordert rechtliche, organisatorische und instanzbezogene Prüfung |
