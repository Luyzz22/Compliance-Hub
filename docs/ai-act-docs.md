# EU-AI-Act-Dokumentation pro High-Risk-System

ComplianceHub bietet mandantenfähige **Dokumentationsbausteine** für High-Risk-KI-Systeme, orientiert an Annex IV bzw. Art. 11 EU AI Act (technische Dokumentation). Die Funktion ist über das Backend-Feature `COMPLIANCEHUB_FEATURE_AI_ACT_DOCS` und spiegelnd `NEXT_PUBLIC_FEATURE_AI_ACT_DOCS` im Frontend schaltbar.

## Nutzung

1. **Voraussetzung:** Das KI-System ist im Register als **Risk Level `high`** geführt.
2. **System-Detail** (`/tenant/ai-systems/[id]`): Abschnitt **EU AI Act Dokumentation** mit fünf Sektionen (Risikomanagement, Daten-Governance, Monitoring/Logging, menschliche Aufsicht, technische Robustheit).
3. **KI-Entwurf:** Button „KI-Entwurf erzeugen“ ruft `POST .../ai-act-docs/{section_key}/draft` auf. Es werden `LLMTaskType.LEGAL_REASONING` und `STRUCTURED_OUTPUT` genutzt (Master `COMPLIANCEHUB_FEATURE_LLM_ENABLED` plus `LLM_LEGAL_REASONING` und `LLM_REPORT_ASSISTANT`). Der Entwurf wird **nicht** automatisch gespeichert.
4. **Bearbeitung & Speichern:** Markdown im Editor anpassen, dann **Speichern** → `POST .../ai-act-docs/{section_key}` mit Versionierung (jede Speicherung erhöht `version`).
5. **Export:** „AI Act Dokumentation herunterladen (MD)“ lädt ein kombiniertes Markdown mit Profil, Klassifikation, NIS2-/KRITIS-KPIs, Maßnahmen und allen Sektionen (`GET .../export?format=markdown`).

## Hinweise

- Ausgaben des KI-Assistenten sind **Prüftexte**, keine Rechtsberatung; Freigabe und fachliche Validierung liegen beim Betreiber.
- PDF-Export ist bewusst nicht implementiert; externe Renderer können später angebunden werden.
