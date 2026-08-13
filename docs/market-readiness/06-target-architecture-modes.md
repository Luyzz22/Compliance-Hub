# 06 – Zielarchitektur: Drei Betriebsmodi

> **Architekturhinweis (2026-08-11):** Die Vendor-Topologie dieses ursprünglichen
> Market-Readiness-Baselines bleibt als Übergangs- und Nachweisdokument erhalten. Für
> neue produktive Compliance-Hub-Deployments gilt die Hetzner-first-Entscheidung in
> [ADR 0002](../adr/0002-hetzner-azure-llm-workload-classes.md). Insbesondere sind
> Vercel und Azure-Compute dort kein Ziel-Datenpfad; Azure OpenAI ist nur eine
> klassifizierte, dokumentierte Inferenz-Ausnahme. Bestehende Vercel-Verarbeitung darf
> bis zur tatsächlich belegten Migration nicht aus den Restrisiken entfernt werden.

**Grundidee:** Souveränität ist keine Eigenschaft, die man behauptet, sondern ein
**Betriebsmodus, den man erzwingt und nachweist**. Statt einer weichgezeichneten
Aussage für alle Kunden gibt es drei klar getrennte Modi mit je eigener
Vendor-Allowlist, eigener Startup-Verifikation und **eigenem, freigegebenem
Claim-Set**.

Der Modus ist eine **Deployment-Eigenschaft**, keine Mandanteneinstellung. Ein Kunde
kauft einen Modus; ein Mandant kann sich nicht selbst in einen strengeren Modus
schalten, dessen Infrastruktur nicht existiert.

## Technische Verankerung

```
COMPLIANCEHUB_SOVEREIGNTY_MODE = unrestricted | standard_dach | eu_sovereign | strict_sovereign
```

**Der Default ist `unrestricted`** — bewusst der Modus, der **keine** Aussage
autorisiert. Ein restriktiver Default sähe sicherer aus, würde die Laufzeit aber eine
Haltung behaupten lassen, die niemand gewählt hat: `standard_dach` erlaubt Aussagen wie
„Betrieb in EU-Rechenzentren", die in einer unkonfigurierten Installation durch nichts
gedeckt sind. Ein Modus, der Marketingaussagen freigibt, muss eine bewusste Entscheidung
sein. `unrestricted` wird bei jedem Start als Warnung protokolliert.

Die Variable steuert vier Dinge:

1. **Startup-Verifikation** — der Prozess startet nicht, wenn ein im Modus verbotener
   Vendor konfiguriert ist (`app/sovereignty.py`, neu).
2. **LLM-Provider-Filter** — `llm_router.py` entfernt verbotene Provider **aus der
   Kette**, statt sie nur zu depriorisieren.
3. **Claim-Freigabe** — `/api/v1/sovereignty/profile` liefert die zulässigen
   Marketing-/Trust-Center-Aussagen; das Frontend rendert nur diese.
4. **Trust-Center-Artefakt** — der Modus mit Vendor-Liste und Restrisiken wird
   maschinenlesbar veröffentlicht und ist damit für den Kunden prüfbar.

Damit wird aus einer Marketingaussage eine **testbare Eigenschaft** — genau das, was
`02-claim-vs-proof-matrix.md` als Maßstab fordert.

---

# Modus 1 — `Standard DACH Compliance`

**Zielgruppe:** Steuerberater- und WP-Kanzleien, kleine ISO-/Datenschutzberater, MSPs,
Mittelstand ohne besondere Sensibilität, alle Pilotkunden.
**Anteil des adressierbaren Markts: geschätzt 70 %.**

## Zielarchitektur

```
Browser
  │  HTTPS
  ▼
Next.js @ Vercel (fra1)  ── US-kontrolliert, im Datenpfad
  │  BFF: /api/backend/[...path]
  ▼
FastAPI @ Azure Container Apps / App Service (Region: Germany West Central)
  │
  ├── Azure Database for PostgreSQL Flexible Server (Germany West Central)
  │     · FORCE RLS auf allen mandantenbezogenen Tabellen
  │     · Entra-Token-Auth, Private Endpoint
  │     · PITR 35 Tage, geo-redundantes Backup innerhalb EU
  ├── Azure Blob Storage (Germany West Central) — Evidence
  │     · Versioning + Immutability Policy (WORM) für Audit-Exporte
  ├── Azure Key Vault — Signaturschlüssel, TOTP-Verschlüsselung, DB-Credentials
  ├── Azure OpenAI (Sweden Central / Germany, EU Data Boundary) — nur wenn aktiviert
  └── n8n self-hosted (Azure Container Apps) — Scheduler/Automatisierung
```

## Vendor-Politik

| Erlaubt | Verboten |
|---|---|
| Vercel (Frontend + BFF, `fra1`) | OpenAI direkt |
| Microsoft Azure (Compute, DB, Storage, Key Vault) | Anthropic direkt |
| Microsoft Entra ID | Google Gemini |
| Azure OpenAI (EU-Region) | Jeder Cloud-Dienst ohne EU-Region |
| GitHub (Build, kein Datenpfad) | Jeder Dienst ohne AVV |
| n8n self-hosted | Analytics-/Tracking-Dienste |
| Temporal self-hosted | |

## Datenfluss

Kundendaten passieren: Browser → **Vercel Edge/Serverless (US-kontrolliert, EU-Region)**
→ Azure Deutschland → PostgreSQL/Blob. Prompt-Inhalte zusätzlich → Azure OpenAI EU,
**nur wenn der Mandant LLM aktiviert hat**.

## Schlüsselmanagement

Azure Key Vault, Microsoft-managed Keys für Storage/DB-Verschlüsselung at rest.
Kein BYOK. Signaturschlüssel für Evidence-Bundles im Key Vault mit
`signing_key_id`-Rotation (im Code bereits vorbereitet).

## Logging / Monitoring

Azure Monitor + Log Analytics in EU-Region. OpenTelemetry-Traces ohne
personenbezogene Payloads. Audit-Logs in der Produktdatenbank, Exporte nach Blob
mit Immutability Policy. **Kein Sentry, kein US-APM.**

## AI-Provider-Strategie

Kette hart auf `[AZURE_OPENAI]` beschränkt. `LLAMA` (self-hosted) optional als
Fallback. `_static_fallback_chain` wird nach dem Modusfilter durchgereicht — die
US-Provider erscheinen nicht mehr in der Kette. LLM bleibt **standardmäßig aus**.

## Support-Zugriff

Support-Personal in DE/EU. Zugriff auf Mandantendaten nur über Break-Glass mit
Ticketbezug, Begründung und Zeitfenster; für den Kunden im Audit-Log sichtbar.

## Backup

Azure PITR 35 Tage, Backups innerhalb EU. Quartalsweiser dokumentierter Restore-Test.
Evidence-Blob mit Soft Delete 30 Tage + Versioning.

## Subprozessoren

Microsoft Corporation (Azure, Entra, Azure OpenAI), **Vercel Inc.**, ggf.
Zahlungsdienstleister. SCC + TIA für Vercel und Microsoft erforderlich, DPF-Status
dokumentieren.

## ✅ Zulässiger Marketing-Claim

> „Betrieb in EU-Rechenzentren (Deutschland/EU). Datenverarbeitung nach DSGVO mit
> Auftragsverarbeitungsvertrag, dokumentierten Drittlandtransfers und offengelegten
> Subprozessoren. KI-Funktionen standardmäßig deaktiviert; bei Aktivierung
> ausschließlich über Azure OpenAI in EU-Regionen."

## ❌ Ausdrücklich unzulässig

„Souverän", „EU-only", „keine US-Anbieter", „CLOUD-Act-sicher", „DSGVO-konform".

## Ehrliche Restrisiko-Aussage (gehört ins Trust Center)

> Vercel Inc. und Microsoft Corporation sind US-Unternehmen und unterliegen
> US-Recht, auch bei Verarbeitung in EU-Regionen. Wir dokumentieren diese Transfers
> und setzen Standardvertragsklauseln ein. Wenn Sie dieses Restrisiko ausschließen
> müssen, wählen Sie `EU Sovereign` oder `Strict Sovereign`.

---

# Modus 2 — `EU Sovereign`

**Zielgruppe:** Öffentliche Hand (Kommunen, Landesbehörden), Gesundheitswesen,
Energieversorger, KRITIS-Betreiber, Banken/Versicherungen, Unternehmen mit
Betriebsrat-Sensibilität.
**Anteil des adressierbaren Markts: geschätzt 25 % — mit deutlich höheren
Vertragswerten.**

## Zielarchitektur

```
Browser
  │  HTTPS
  ▼
Next.js SELF-HOSTED (Node-Standalone-Build)
  bei Hetzner (Falkenstein/Nürnberg), IONOS Cloud oder OVHcloud (Frankfurt)
  │  → Vercel ist vollständig aus dem Datenpfad entfernt
  ▼
FastAPI (Container, gleicher EU-Anbieter)
  │
  ├── PostgreSQL (managed, EU-Anbieter) mit FORCE RLS
  ├── S3-kompatibler Objektspeicher (EU-Anbieter) — Evidence, SSE
  ├── HashiCorp Vault / OpenBao self-hosted — Secrets & Schlüssel
  ├── Azure OpenAI EU **oder** Mistral (FR) **oder** Aleph Alpha (DE)
  │     · als bewusste Kundenentscheidung, dokumentiert
  └── n8n + Temporal self-hosted
```

**Zentrale Änderung gegenüber Modus 1:** Der Next.js-Standalone-Build ersetzt Vercel.
Das ist ein realistischer, überschaubarer Umbau — Next.js unterstützt
`output: "standalone"`; die 48 Server-Routes laufen unverändert. **Aufwand: 2–3
Wochen inkl. Container, CI-Pipeline und Betriebsdoku.**

## Vendor-Politik

| Erlaubt | Verboten |
|---|---|
| Hetzner Online GmbH (DE) | **Vercel** |
| IONOS SE (DE), OVHcloud (FR), Scaleway (FR), Exoscale (CH) | AWS, GCP |
| StackIT (Schwarz Gruppe, DE) | OpenAI, Anthropic, Google |
| Azure OpenAI EU *(mit dokumentiertem Restrisiko)* | US-SaaS im Datenpfad |
| Mistral AI (FR), Aleph Alpha (DE) | US-Monitoring/APM |
| Entra ID *(nur wenn der Kunde ihn selbst betreibt)* | |
| n8n, Temporal, Vault/OpenBao — self-hosted | |

## Datenfluss

Kundendaten verlassen die EU-Anbieterkette nicht. Einzige mögliche Ausnahme:
Azure OpenAI, falls der Kunde das ausdrücklich wählt — dann als dokumentierte
Ausnahme im Transfer Record.

## Schlüsselmanagement

Vault/OpenBao self-hosted in EU. Verschlüsselung at rest über
Provider-SSE + zusätzlich **applikationsseitige Envelope-Encryption** für
Evidence-Dateien und TOTP-Secrets. Schlüsselrotation dokumentiert.

## Logging / Monitoring

Grafana + Loki + Prometheus self-hosted. OpenTelemetry-Collector in EU.
Keine externen Telemetriedienste.

## AI-Provider-Strategie

Kunde wählt beim Onboarding **eine** Option, die im Transfer Record festgehalten wird:
(a) LLM aus — Default; (b) Mistral EU; (c) Aleph Alpha DE; (d) self-hosted Llama;
(e) Azure OpenAI EU mit dokumentiertem Restrisiko.

## Support-Zugriff

Nur EU/EWR-ansässiges Personal. Break-Glass mit Kundenfreigabe **vor** dem Zugriff
(nicht nur Protokollierung danach). Vier-Augen-Prinzip.

## Backup

Backups beim selben EU-Anbieter, verschlüsselt mit kundenseitig einsehbarem
Schlüsselmaterial-Nachweis. Georedundanz innerhalb der EU. Halbjährlicher,
dokumentierter Restore-Test mit Bericht als Trust-Center-Artefakt.

## Subprozessoren

Ausschließlich EU/EWR-Gesellschaften. Vollständige Liste mit Sitz, Rolle,
Verarbeitungszweck, Datenkategorie.

## ✅ Zulässiger Marketing-Claim

> „Vollständiger Betrieb bei EU-ansässigen Anbietern. Keine US-kontrollierten
> Dienstleister im Datenpfad. Sämtliche Subprozessoren mit Sitz in der EU/im EWR.
> KI-Verarbeitung ausschließlich über EU-Anbieter oder vollständig deaktiviert."

## ❌ Weiterhin unzulässig

„CLOUD-Act-immun", „garantiert kein Behördenzugriff", „DSGVO-konform" als
Absolutaussage.

## Ehrliche Restrisiko-Aussage

> Auch EU-Anbieter können Muttergesellschaften, Kapitalgeber oder Zulieferer mit
> US-Bezug haben. Wir prüfen die Eigentümerstruktur unserer Subprozessoren und legen
> sie offen. Wählt der Kunde Azure OpenAI als KI-Anbieter, entsteht ein
> dokumentiertes US-Restrisiko.

---

# Modus 3 — `Strict Sovereign / Anti-CLOUD-Act`

**Zielgruppe:** Bundes-/Landesbehörden, Verteidigung, kritische Infrastruktur höchster
Stufe, Konzerne mit expliziter Anti-US-Cloud-Policy, Betriebsräte mit
Mitbestimmungsvorbehalt.
**Anteil des adressierbaren Markts: geschätzt 5 % — höchste Vertragswerte,
längste Zyklen.**

## Zielarchitektur

```
Kunden-Rechenzentrum ODER dedizierte Single-Tenant-Instanz
bei einem deutschen Anbieter mit C5-Testat
  │
  ├── Next.js Standalone (Container)
  ├── FastAPI (Container)
  ├── PostgreSQL (dediziert, FORCE RLS, kundenverwaltete Verschlüsselung)
  ├── MinIO / S3-kompatibel (im Kundennetz) — Evidence
  ├── OpenBao (im Kundennetz) — Schlüssel, kundenverwaltet
  ├── Keycloak / kundeneigener IdP (OIDC/SAML)
  ├── LLM: ausschließlich self-hosted (vLLM/Ollama, Llama/Mistral-Gewichte)
  │      ODER vollständig deaktiviert
  └── n8n + Temporal im Kundennetz
```

**Deployment-Modell:** Single-Tenant-Instanz oder On-Premises. Kein Shared-Multi-Tenant.
Das ist zugleich die stärkste denkbare Mandantenisolation.

## Vendor-Politik

| Erlaubt | Verboten |
|---|---|
| Kundeneigenes RZ | **Jeder US-kontrollierte Anbieter, ausnahmslos** |
| Deutsche Anbieter mit BSI-C5-Testat (Plusserver, noris, Open Telekom Cloud, StackIT) | Jede Managed-SaaS ohne Quellcode-/Betriebskontrolle |
| Ausschließlich Open-Source-Komponenten im Datenpfad | Cloud-LLM-APIs jeder Art |
| Self-hosted Modellgewichte | Externe Monitoring-Dienste |

**Bewusste Konsequenz:** GitHub darf **nicht** im Build-Pfad dieser Instanz liegen.
Für Modus 3 ist eine gespiegelte Build-Kette (GitLab self-hosted / Forgejo) mit
signierten Artefakten erforderlich. Das ist Aufwand, aber ohne diesen Schritt ist der
Modus nicht ehrlich behauptbar.

## Datenfluss

Kundendaten verlassen die Kundeninfrastruktur bzw. das dedizierte deutsche RZ **nicht**.
Es gibt keinen ausgehenden Datenpfad zum Hersteller — auch nicht für Telemetrie,
Fehlerberichte oder Lizenzprüfung. Updates werden als signierte Artefakte
eingebracht, nicht abgerufen.

## Schlüsselmanagement

Vollständig kundenverwaltet. Der Hersteller besitzt keinen Schlüssel und kann die
Daten technisch nicht entschlüsseln. Optional HSM-Anbindung.

## Logging / Monitoring

Vollständig im Kundennetz. Der Hersteller erhält keine Telemetrie. Support arbeitet
mit vom Kunden bereitgestellten, gefilterten Log-Auszügen.

## AI-Provider-Strategie

Ausschließlich self-hosted Inferenz oder LLM aus. Kein API-Aufruf verlässt das Netz.
Der `llm_router` filtert im Modus `strict_sovereign` auf `[LLAMA]`; jede andere
Konfiguration verhindert den Prozessstart.

## Support-Zugriff

**Kein stehender Zugriff.** Der Hersteller erhält Zugriff nur auf ausdrückliche,
zeitlich begrenzte Einladung des Kunden, über kundenkontrollierte Zugangswege,
mit Sitzungsaufzeichnung durch den Kunden.

## Backup

Vollständig kundenverantwortet. Der Hersteller liefert Backup-/Restore-Runbook und
Verifikationswerkzeuge, hält aber selbst keine Kopie.

## Subprozessoren

**Keine** für den Datenpfad. Der Hersteller ist in dieser Konstellation in der Regel
kein Auftragsverarbeiter mehr, sondern Softwarelieferant mit Wartungsvertrag — das
ist vertraglich sauber abzugrenzen.

## ✅ Zulässiger Marketing-Claim

> „Betrieb ausschließlich in Ihrer Infrastruktur oder in einem dedizierten deutschen
> Rechenzentrum mit C5-Testat. Keine US-kontrollierten Anbieter im Datenpfad, im
> Betrieb, im Schlüsselmanagement, im Support oder im Backup. KI-Inferenz
> ausschließlich lokal. Wir haben technisch keinen Zugriff auf Ihre Daten."

## ❌ Auch hier unzulässig

„CLOUD-Act-immun" als Absolutaussage — der CLOUD Act adressiert Anbieter unter
US-Jurisdiktion; die korrekte Aussage ist „kein US-kontrollierter Anbieter im
Datenpfad", nicht „immun".

## Ehrliche Restrisiko-Aussage

> Verbleibende Restrisiken: Hardware- und Firmware-Lieferketten enthalten
> US-Komponenten. Open-Source-Abhängigkeiten stammen teilweise von US-Projekten oder
> Registries. Die Modellgewichte quelloffener Sprachmodelle können von
> US-Organisationen stammen. Wir legen unsere Software-Stückliste (SBOM) offen, damit
> Sie diese Risiken selbst bewerten können.

---

# Vergleichsmatrix

| Kriterium | Standard DACH | EU Sovereign | Strict Sovereign |
|---|---|---|---|
| Frontend-Hosting | Vercel (US, fra1) | EU-Anbieter self-hosted | Kunde / DE-RZ |
| Backend | Azure DE | EU-Anbieter | Kunde / DE-RZ |
| Datenbank | Azure PostgreSQL DE | EU managed PostgreSQL | Dediziert |
| Mandantenmodell | Shared + RLS | Shared + RLS | Single-Tenant |
| Schlüssel | Microsoft-managed | Vault (Hersteller) | Kunde (BYOK/HYOK) |
| IdP | Entra ID | Kundenwahl | Kunde |
| LLM | Azure OpenAI EU / aus | EU-Anbieter / aus | Self-hosted / aus |
| Support | EU-Personal, Break-Glass | EU, Freigabe vorab | Nur auf Einladung |
| Herstellertelemetrie | Ja (pseudonymisiert) | Reduziert | Keine |
| US-Subprozessoren | Ja, offengelegt | Nein | Nein |
| Souveränitäts-Claim | ❌ | ✅ eingeschränkt | ✅ stark |
| Zielpreis (indikativ) | Listenpreis | +40–60 % | +150–250 %, Projektanteil |
| Time-to-Value | Tage | Wochen | Monate |
| Betriebsaufwand Hersteller | Niedrig | Mittel | Hoch |

---

# Umsetzungsreihenfolge

| Schritt | Modus | Aufwand | Voraussetzung |
|---|---|---|---|
| 1. `COMPLIANCEHUB_SOVEREIGNTY_MODE` + Startup-Verifikation + Provider-Filter | alle | S | — |
| 2. Backend-Container + IaC + Azure-Deployment | Standard DACH | L | P0-7 |
| 3. Blob-Storage-Backend für Evidence | Standard DACH | M | P0-4 |
| 4. Postgres-RLS auf alle Mandantentabellen | Standard DACH | L | P0-1 |
| 5. Next.js-Standalone-Build + Container | EU Sovereign | M | Schritt 2 |
| 6. Vault/OpenBao-Integration | EU Sovereign | M | Schritt 5 |
| 7. Self-hosted-Inferenz-Provider im Router | EU Sovereign | M | Schritt 1 |
| 8. Single-Tenant-Deployment-Paket + Offline-Build-Kette | Strict Sovereign | XL | Schritte 2–7 |

**Empfehlung zur Sequenz:** Modus 1 vollständig fertigstellen und **belegen**,
bevor Modus 2 vermarktet wird. Ein halbfertiger Souveränitätsmodus ist gefährlicher
als keiner — er erzeugt genau die Claim-Risiken, die dieses Review beseitigen soll.

**Vertriebliche Empfehlung:** Modus 2 bereits jetzt als „auf Anfrage, mit
Projektvorlauf" im Trust Center listen. Das qualifiziert Leads und signalisiert
Ernsthaftigkeit, ohne etwas zu versprechen, das noch nicht existiert.
