# Azure-Demopfad: Betriebs- und Freigabe-Runbook

Status: **vorbereitet und standardmäßig deaktiviert**. Dieses Runbook beschreibt eine
kundentaugliche, aber ausdrücklich nicht produktive Demonstration mit ausschließlich
synthetischen Daten. Es ist weder ein Nachweis allgemeiner DSGVO-/EU-AI-Act-Konformität noch
eine Freigabe für reale Kunden-, Beschäftigten- oder Betriebsdaten.

## Freigegebener Umfang

- genau drei fest im Backend definierte Governance-Szenarien;
- Datenklasse `public`, Kennzeichnung `synthetic_data_only=true`;
- Azure OpenAI als zwingend erforderlicher Provider, ohne stillen Fallback;
- strukturierter Entwurf mit genau drei Prüfhandlungen und Human-Review-Hinweis;
- keine freie Texteingabe, keine Datei, kein RAG-Korpus und keine Kundendaten;
- keine automatische Rechts-, Risiko- oder Freigabeentscheidung;
- nur ein registrierter `is_demo=true`, `demo_playground=false` Mandant;
- persistiert werden ausschließlich bestehende Audit-/Nutzungsmetadaten, keine Prompt- oder
  Antwortinhalte.

## Technische Freigabekette

Der Backend-Start muss fehlschlagen, wenn der Pfad aktiviert ist und eine der folgenden
Bedingungen fehlt:

1. Sovereignty Mode `standard_dach`;
2. PII-Modus `block`;
3. Azure-EU-Attestierung und Azure-Präferenz;
4. zertifikatsbasierte Entra-Authentifizierung ohne Azure API Key;
5. Chat- und LLM-Master-Feature;
6. unveränderlicher Demo-Modus und explizite Synthetic-only-Attestierung;
7. Tageslimit von 1 bis 100 Aufrufen;
8. Tageslimit von 1 bis 250.000 Token;
9. Promptdeckel bis 12.000 Zeichen und Ausgabedeckel bis 1.024 Token.

Empfohlenes Demo-Profil:

```dotenv
COMPLIANCEHUB_SOVEREIGNTY_MODE=standard_dach
COMPLIANCEHUB_FEATURE_DEMO_MODE=true
COMPLIANCEHUB_DEMO_BLOCK_ALL_MUTATIONS=true
COMPLIANCEHUB_DEMO_AZURE_INFERENCE_ENABLED=true
COMPLIANCEHUB_DEMO_SYNTHETIC_ONLY_ATTESTED=true
COMPLIANCEHUB_FEATURE_LLM_ENABLED=true
COMPLIANCEHUB_FEATURE_LLM_CHAT_ASSISTANT=true
COMPLIANCEHUB_LLM_PREFER_AZURE=true
COMPLIANCEHUB_LLM_ASSUME_AZURE_EU=true
COMPLIANCEHUB_LLM_PII_MODE=block
COMPLIANCEHUB_LLM_MAX_PROMPT_CHARACTERS=12000
COMPLIANCEHUB_LLM_MAX_OUTPUT_TOKENS=800
COMPLIANCEHUB_LLM_DAILY_CALL_LIMIT=20
COMPLIANCEHUB_LLM_DAILY_TOKEN_LIMIT=50000
AZURE_OPENAI_AUTH=client_certificate
NEXT_PUBLIC_FEATURE_DEMO_AZURE_INFERENCE=true
```

Ressourcenamen, Tenant-/Client-IDs und Zertifikatspfade werden hostseitig gesetzt. Private
Schlüssel und Zertifikatsmaterial dürfen nie in `.env`, Images, Git oder Browser-Bundles
gelangen. Das Zertifikat wird read-only mit Modus `0400` in den Backend-Container gemountet.

## Kostenkontrolle

Die Azure-Budgetwarnung von 20 EUR ist eine Benachrichtigung und **kein Hard Cap**. Die
serverseitigen Tageslimits reservieren Aufrufe und Tokenbudgets atomar vor dem Azure-Egress.
Sie begrenzen die Anwendungsnutzung, sind aber keine Abrechnungsgarantie für sonstige Azure-
Kosten. Azure-Quota, ein einzelner freigegebener Demo-Operator und der dokumentierte
Abschaltpfad bleiben deshalb Teil der Kostenkontrolle. Vor jeder Kundendemo werden aktuelle
Azure-Kosten, verbleibendes Tagesbudget und die Empfängerliste der Budgetwarnung geprüft. Bei
80 Prozent der Tagesgrenze wird der Pfad bis zur nächsten Prüfung deaktiviert.

## Abnahme vor einer Demo

1. Azure-Ressource und Modell-Deployment sind weiterhin in der freigegebenen EU Data Zone.
2. Public Network Access steht auf Default Deny; nur die aktuelle Demo-Egress-IP ist erlaubt.
3. Lokale Azure-Key-Authentifizierung ist deaktiviert; das Client-Zertifikat ist gültig und
   nicht abgelaufen.
4. Der Demomandant ist read-only und enthält ausschließlich synthetische Daten.
5. Backend-, Frontend-, Security-, CSP- und Runtime-Storage-Gates sind grün.
6. Alle drei Szenarien werden einmal über UI und Tastatur getestet; Fehlertexte zeigen keinen
   Provider-Fallback oder vertrauliche Diagnosedaten.
7. Ein datierter, redigierter Evidence-Satz wird außerhalb des Repositories abgelegt.

## Sofortige Abschaltung

`COMPLIANCEHUB_DEMO_AZURE_INFERENCE_ENABLED=false` setzen und Backend neu starten. Danach Azure
Role Assignment des Demo-Principals entfernen oder das Zertifikat widerrufen, falls ein
Credential-Vorfall vermutet wird. Audit-/Nutzungsmetadaten gemäß festgelegter Aufbewahrung
sichern; keine Prompt- oder Antwortinhalte sind Teil dieses Stores.

## Grenze zur Produktion

Für eine echte Produktionsfreigabe fehlen bis zur dokumentierten Abnahme insbesondere reale
Hetzner-TLS-/WAF-/Netzwerk-Evidence, Entra-SSO und Conditional Access, PostgreSQL-RLS,
Backup-/Restore-Drill, Secret-Rotation, signierte Images/SBOM sowie AVV/TOM- und rechtliche
Freigaben. Diese Nachweise dürfen nicht durch einen erfolgreichen Demolauf ersetzt werden.
