# Private synthetische Demo auf Hetzner

Status: Implementierungs- und Prüfpfad, **kein Produktivnachweis**. Der Stack darf nur
synthetische Daten enthalten und bleibt bis zum rechtlichen, TLS-, Backup- und
Restore-Gate auf eine kleine IP-Allowlist begrenzt.

## Zielbild

```text
zugelassene Quell-IP
        |
        v
Caddy (TLS, 80/443) -> Next.js BFF -> FastAPI -> OPA
                              |           |
                              |           +-> Azure OpenAI EU Data Zone
                              +-> Hetzner Object Storage NBG1
                              +-> PostgreSQL TLS, nur internes Docker-Netz
```

- Es gibt genau einen synthetischen Mandanten `demo-mittelstand-ag`.
- Der Mandant ist `is_demo=true`, `demo_playground=false`; alle fachlichen Mutationen
  werden abgewiesen.
- Azure erhält ausschließlich drei feste, öffentliche synthetische Sachverhalte. Freitext,
  Uploads und Kundendokumente sind in diesem Pfad nicht vorgesehen.
- Eine lokale Passwortidentität ist ausschließlich in `synthetic_demo` + `pilot` erlaubt,
  wenn alle Read-only-Attestierungen gesetzt, Selbstregistrierung und anonymer Demozugang
  aber deaktiviert sind. Der normale Produktionspfad bleibt Entra-only.
- PostgreSQL läuft für die Vorschau auf demselben CPX32, ist nicht veröffentlicht, erzwingt
  TLS/SCRAM und getrennte, nicht privilegierte Backend-/Frontend-Rollen. Das ersetzt keinen
  separaten Produktionscluster und keinen PITR-Nachweis.

## Noch offene externe Gates

1. Privaten Hetzner Object-Storage-Bucket in `nbg1` anlegen, Versionierung aktivieren und
   eigene Zugriffsdaten nur für diesen Bucket erzeugen. Dies ist eine zusätzliche bezahlte
   Ressource.
2. Vertrauenswürdiges TLS-Zertifikat eines freigegebenen deutschen/europäischen Anbieters
   bereitstellen. Das temporäre interne Zertifikat dient nur dem technischen IP-Test.
3. Vollständige Angaben für Impressum und Datenschutz anwaltlich prüfen. Solange
   `COMPLIANCEHUB_LEGAL_PUBLISH_READY=false` gilt, bleibt die IP-Allowlist zwingend.
4. `demo.complywithai.de` bei STRATO erst nach erfolgreichem IP-Smoke-Test und mit niedrigem
   TTL auf den Server zeigen lassen. `complywithai.de` bleibt dabei unverändert.
5. Hetzner Cloud Firewall und tägliche Server-Backups im Console-Projekt kontrollieren;
   Server-Backups ersetzen kein getestetes PostgreSQL-/S3-Restore.

## Hostvertrag

- Deployment-Verzeichnis: `/opt/compliancehub`
- Nicht geheime Konfiguration: `/opt/compliancehub/deploy/hetzner/.env.synthetic-demo`,
  Eigentümer `complianceops`, Modus `0600`
- Geheimnisse: `/opt/compliancehub/deploy/hetzner/secrets`, Modus `0700`; jede Datei hat
  Modus `0400` und die vom Preflight geforderte numerische Container-UID.
- Keine Geheimnisse in Git, Compose-Umgebungsvariablen, Shell-History, Image-Layern oder
  Evidence-Ausgaben.

Der Host-Preflight prüft Eigentümer, Dateimodus, Mindestlänge, Zertifikatsketten,
Schlüsselpaare, Zertifikatsablauf, Azure-/S3-Ziel, CIDR-Begrenzung, Image-/Commit-Bindung,
PostgreSQL-DSN und den aufgelösten Compose-Vertrag:

```bash
cd /opt/compliancehub/deploy/hetzner
sudo python3 preflight-synthetic-demo.py --env-file .env.synthetic-demo
```

Er gibt nur Status und Fehlerklasse aus, niemals Secret-Inhalte.

## Buildvertrag

Backend und Frontend werden aus demselben geprüften Commit gebaut. Für die Demo werden
release-spezifische lokale Tags verwendet; das ist ein transparenter Vorproduktionspfad,
keine signierte Produktions-Supply-Chain.

```bash
COMMIT="$(git rev-parse HEAD)"
sudo docker build \
  --file Dockerfile.hetzner \
  --label "com.complywithai.release.commit=${COMMIT}" \
  --tag "compliancehub-backend:synthetic-demo-${COMMIT}" \
  .

sudo docker build \
  --file frontend/Dockerfile.hetzner \
  --build-arg NEXT_PUBLIC_FEATURE_DEMO_AZURE_INFERENCE=true \
  --build-arg NEXT_PUBLIC_DEMO_WORKSPACE_TENANT_ID=demo-mittelstand-ag \
  --build-arg NEXT_PUBLIC_TENANT_ID=demo-mittelstand-ag \
  --label "com.complywithai.release.commit=${COMMIT}" \
  --tag "compliancehub-frontend:synthetic-demo-${COMMIT}" \
  .
```

Die beiden Tags und der vollständige Commit kommen danach in `.env.synthetic-demo`.

## Start und Verifikation

```bash
cd /opt/compliancehub/deploy/hetzner
export COMPLIANCEHUB_ENV_FILE=.env.synthetic-demo
sudo docker compose \
  --env-file .env.synthetic-demo \
  -f compose.synthetic-demo.yml \
  up -d

sudo docker compose \
  --env-file .env.synthetic-demo \
  -f compose.synthetic-demo.yml \
  ps
```

Startreihenfolge: PostgreSQL → Schema-/Demo-Bootstrap → RLS-/Rollenvertrag → Backend + OPA
→ Frontend → Caddy. Ein Fehler in einem einmaligen Bootstrap-Schritt blockiert die
nachfolgenden Dienste.

Abnahmekriterien:

1. Alle Langzeitdienste sind `healthy`; beide Bootstrap-Container enden mit Code 0.
2. Von einer nicht zugelassenen Quell-IP antworten HTTP und HTTPS mit 403.
3. Anmeldung funktioniert nur mit dem operatorseitig verwahrten Demokonto; Registrierung
   und anonymer `?demo=1`-Zugang bleiben geschlossen.
4. Tenant-Metadaten melden read-only Demo; mutierende API-Aufrufe ergeben
   `demo_tenant_readonly`.
5. Alle drei festen Azure-Szenarien liefern strukturiertes JSON, Kennzeichnung
   `synthetic_data_only=true` und Human-Review-Hinweis.
6. Der Azure-Deployment-Tageszähler und das 20-Euro-Budgetmonitoring sind sichtbar; die
   Warnung ist ausdrücklich kein technischer Hard Cap.
7. S3-Schreib-/Lese-/Löschprobe arbeitet nur im Demo-Präfix.
8. Ein verschlüsseltes PostgreSQL-Backup wird wiederhergestellt und die synthetischen
   Kontrollsummen stimmen, bevor irgendeine weitere Freigabe diskutiert wird.

## Evidenz und Rückbau

Evidence liegt außerhalb des Repositories unter
`/var/lib/compliancehub/demo-evidence/<UTC-Zeitstempel>/`, Modus `0700/0600`. Mindestens:

- Commit, Image-IDs und Image-Labels
- SHA-256 des aufgelösten Compose-Contracts und der nicht geheimen Konfiguration
- Preflight-, Test-, Trivy- und HTTP-Smoke-Status
- PostgreSQL-Rollen-/RLS-Negativtest ohne Datensätze
- Azure-Resource-/Deployment-/Netzwerkmetadaten ohne Token oder Zertifikate
- Backup-/Restore-Protokoll und Ergebnis-Hashes

Rückbau erfolgt mit `docker compose ... down`; Volumes oder S3-Objekte werden erst nach
einem separat bestätigten Löschauftrag entfernt. Ein normales `down` löscht keine Daten.
