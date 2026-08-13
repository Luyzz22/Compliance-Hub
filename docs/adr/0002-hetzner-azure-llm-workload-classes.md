# ADR 0002: Hetzner-first und datenklassengeführtes LLM-Routing

- Status: angenommen; Infrastrukturmigration weiterhin geplant
- Datum: 2026-08-11
- Scope: Compliance Hub (nicht Kanzlei-AI)

## Entscheidung

Compliance Hub erhält eine Hetzner-first-Zielarchitektur. Azure OpenAI bleibt eine
bewusste, dokumentierte Ausnahme für freigegebene KI-Inferenz in einer regionalen
EU-Bereitstellung oder EU Data Zone. Direkte Modell-APIs von OpenAI, Anthropic und
Google sowie Vercel, Neon und US-Observability gehören nicht in den produktiven
Datenpfad.

Ein lokales Modell ist für Compliance Hub nicht pauschal erforderlich. Ob Azure
verwendet werden darf, entscheidet die höchste Datenklasse im Prompt:

| Klasse | Beispiele | Externe Inferenz |
|---|---|---|
| `public` | öffentliche Normtexte, veröffentlichte Produktinformationen, synthetische Daten | Azure nach Deployment- und Tenant-Policy |
| `internal` | aggregierte Reifegrade, Kontrollstatus ohne Personenbezug, pseudonymisierte Kennzahlen | Azure nach Deployment- und Tenant-Policy |
| `confidential` | nicht öffentliche Systembeschreibungen, Vertrags- oder Geschäftsgeheimnisse | nur nach expliziter Mandantenfreigabe; vorher minimieren/pseudonymisieren, sonst lokal |
| `restricted` | Roh-Evidence, Hinweisgeber-/HR-/Incident-Inhalte, Art.-9/10-Daten, Zugangsdaten, Berufsgeheimnisse | ausschließlich lokales Modell oder keine KI-Verarbeitung |

`restricted` kann durch keine Mandantenrichtlinie für externe Provider freigegeben
werden. Eine fehlende Datenklasse am generischen API-Endpunkt wird als `restricted`
behandelt. Fachliche Aufrufer erhalten konservative Task-Defaults. Heuristische
PII-Erkennung bleibt eine zusätzliche Kontrolle, ersetzt die Datenklassifizierung aber
nicht.

## Zielarchitektur

```text
Browser
  -> Hetzner DE Load Balancer / Reverse Proxy / WAF
     -> Next.js Standalone Frontend + BFF
        -> FastAPI Control Plane (privates Netz)
           -> PostgreSQL mit FORCE RLS
           -> S3-kompatibler Objektstorage mit Löschgraph und Envelope Encryption
           -> lokales OCR/Parsing und lokale Pseudonymisierung
           -> OpenBao (lokale Schlüssel/Secrets)
           -> Grafana/Loki/Tempo ohne Prompt-/Response-Inhalte
           -> Egress-Gateway
              -> Azure OpenAI EU Data Zone/regional, nur für freigegebene Klassen
           -> optional vLLM im privaten Netz für `restricted`
```

Für den Start genügt PostgreSQL plus `pgvector`. Qdrant wird erst eingeführt, wenn
belegte Last-, Filter- oder Retrieval-Anforderungen dies rechtfertigen. Redis, GPU,
Qdrant und ein eigener OCR-Worker sind daher keine pauschalen Day-one-Abhängigkeiten.

## Abgrenzung zu Kanzlei-AI

Kanzlei-AI verarbeitet voraussichtlich Mandats- und Akteninhalte. Für Rechtsanwälte
gelten zusätzlich die Verschwiegenheitspflicht aus § 43a BRAO, die besonderen Regeln
für Dienstleister aus § 43e BRAO und der strafrechtliche Schutz aus § 203 StGB. Dafür
ist ein strenger Stufenplan mit lokalem/dediziertem Pfad für die höchste Klasse
sachgerecht.

Compliance Hub ist nicht allein durch seine Produktkategorie ein
Berufsgeheimnisträger-System. Die genannten Regeln greifen aber, sobald ein Kunde
entsprechend geschützte Inhalte in das Produkt einbringt. Deshalb ist die Datenklasse
eine Eigenschaft jedes Workloads und nicht nur eines Produkttarifs.

DSGVO, EU AI Act und NIS2 verlangen risikoadäquate technische und organisatorische
Maßnahmen, nicht pauschal ein lokales Sprachmodell. Die Rechtsgrundlage, eine DSFA/TIA,
Auftragsverarbeitungsverträge, Lösch- und Berechtigungskonzepte sowie menschliche
Aufsicht bleiben unabhängig vom Hostingmodell erforderlich. Diese Architektur ist
deshalb eine Kontrollbasis und keine pauschale Konformitätszusage.

## Azure-Freigabegate

Azure ist nur freigegeben, wenn alle folgenden Nachweise vorliegen:

1. regionale EU-Bereitstellung oder EU Data Zone; kein `Global` Deployment;
2. `standard_dach` als Deploymentmodus, Azure-only Provider-Allowlist, keine externe
   Fallback-Kette und `COMPLIANCEHUB_LLM_ASSUME_AZURE_EU=true` erst nach Prüfung;
3. Managed Identity, private Anbindung soweit verfügbar, Key Vault nur für
   Azure-seitige Schlüssel und dokumentierte Egress-Regeln;
4. AVV/DPA, SCC und Transfer Impact Assessment einschließlich US-Zugriffsrisiko;
5. dokumentierte Azure Abuse-Monitoring-Konfiguration und keine Zusage, Microsoft sei
   „CLOUD-Act-sicher“ oder „CLOUD-Act-immun“;
6. Tenant-Opt-in, Zweckbindung, Löschfristen, Human Review und keine Prompt-/Response-
   Inhalte in Telemetrie;
7. reproduzierbarer Konfigurations-, Security-, Backup- und Restore-Nachweis vor
   Produktionsfreigabe.

## Ausgehende Integrationen

Azure bleibt die einzige freigegebene US-Anbieter-Ausnahme. HubSpot, Pipedrive,
Stripe, Vercel, Neon und US-Observability sind im produktiven Hetzner-Profil nicht
zulässig. Die vorhandenen
CRM-Adapter bleiben ausschließlich für lokale Entwicklung beziehungsweise
Migrationsarbeiten im Quellcode und werden durch Release-Gate, Dispatcher und Adapter
selbst produktiv gesperrt.

Fachliche Webhooks dürfen nur an selbst betriebene HTTPS-Endpunkte gesendet werden.
Der Zielhost muss explizit in `COMPLIANCEHUB_OUTBOUND_WEBHOOK_ALLOWED_HOSTS` stehen;
Credentials, Query-Parameter und URL-Fragmente sind in Endpunkt-URLs unzulässig.
Authentisierung erfolgt über unabhängig rotierte OpenBao-Datei-Secrets. Das
Frontend-Container-Entrypoint wiederholt das Enterprise-Gate mit der tatsächlichen
Runtime-Konfiguration und startet bei einem Policy-Verstoß nicht.

Das vorhandene Stripe-Billing-Modul bleibt eine nicht freigegebene Legacy-Oberfläche:
Stripe-Konfiguration wird in restriktiven Profilen beim Start zurückgewiesen; Webhook-
und Portalpfad verweigern den Produktionsbetrieb. Eine spätere Abrechnung benötigt eine
gesonderte Anbieter-, AVV-, Transfer- und Prozessentscheidung. Selbst betriebene n8n-
und Export-Webhooks verwenden im Backend ebenfalls exakte Host-URL-Allowlisten,
HTTPS ohne Redirect-Folgen und HMAC-Signaturen aus OpenBao-Datei-Secrets.

Dependency-Telemetrie ist kein stillschweigend erlaubter Ausgang. Haystacks optionale
PostHog-Telemetrie wird vor dem Import der Bibliothek standardmäßig deaktiviert und
kann in Produktion nicht aktiviert werden. Die restriktiven Souveränitätsprofile
weisen zudem `POSTHOG_API_KEY` und `POSTHOG_HOST` als Konfigurationskonflikt zurück.
LangSmith-/LangChain-Tracing-Flags, Endpoints und API-Keys werden ebenfalls bereits vor
Dependency-Imports deaktiviert beziehungsweise im Produktionsbetrieb abgewiesen.
Zulässig bleibt nur selbst betriebene, datenminimierte Betriebsbeobachtung ohne Prompt-,
Response- oder personenbezogene Inhaltsdaten.

Temporal bleibt als optionaler Workflow-Baustein standardmäßig deaktiviert. Bei einer
späteren Aktivierung darf nur ein selbst gehosteter Cluster im privaten Hetzner-Netz
verwendet werden; exakte Host-Allowlist und explizites Opt-in sind Pflicht. Temporal
Cloud und dessen API-Key-Pfad sind im restriktiven Produktionsprofil gesperrt.

Der frühere Azure-Blob-Migrationspfad im Next.js-Frontend wurde vollständig entfernt.
Damit enthält dessen Laufzeit-Dependency-Baum weder Azure Storage noch Azure Identity;
persistente Runtime-Daten gehen ausschließlich an den privaten S3-kompatiblen
Hetzner-Endpunkt. Entra-OIDC und die Azure-OpenAI-Ausnahme bleiben getrennte Grenzen.

## Umsetzung im Repository

- `LLMDataClass` und `TenantLLMPolicy.max_external_data_class` bilden das Policy-Gate.
- Der Standard erlaubt externe Verarbeitung höchstens bis `internal`.
- `restricted` wird unabhängig von Fehlkonfigurationen auf `llama`/lokale Inferenz
  begrenzt.
- Ein produktiver Prozess startet nicht mehr im Modus `unrestricted`.
- Der generische Invoke-Endpunkt nutzt Guardrails und ist ohne Klassifizierung
  fail-closed.
- Die tatsächliche Hetzner-Infrastruktur, lokales OCR, OpenBao, Objektverschlüsselung,
  vLLM und private Azure-Netzanbindung sind Zielzustand und dürfen bis zur belegten
  Bereitstellung nicht als implementiert dargestellt werden.

## Normative Primärquellen

- [§ 43a BRAO](https://www.gesetze-im-internet.de/brao/__43a.html)
- [§ 43e BRAO](https://www.gesetze-im-internet.de/brao/__43e.html)
- [§ 203 StGB](https://www.gesetze-im-internet.de/stgb/__203.html)
- [DSGVO](https://eur-lex.europa.eu/eli/reg/2016/679/2016-05-04)
- [NIS2-Richtlinie](https://eur-lex.europa.eu/eli/dir/2022/2555/oj?locale=de)
- [EU AI Act](https://eur-lex.europa.eu/eli/reg/2024/1689/oj?locale=de)
- [EDPB-Empfehlungen zu ergänzenden Transfermaßnahmen](https://www.edpb.europa.eu/documents/recommendation/recommendations-012020-on-measures-that-supplement-transfer-tools-to_en)
- [Azure OpenAI Datenschutz und Datenverarbeitung](https://learn.microsoft.com/en-us/azure/foundry/responsible-ai/openai/data-privacy)
- [Azure-Bereitstellungstypen](https://learn.microsoft.com/en-us/azure/ai-foundry/foundry-models/concepts/deployment-types?view=foundry-classic)
