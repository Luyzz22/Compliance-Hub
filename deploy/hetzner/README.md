# Hetzner-Produktionsprofil

Dieses Verzeichnis beschreibt den freigegebenen Zielpfad für Compliance Hub. Es ist
ein Deployment-Blueprint, kein Nachweis einer bereits erfolgten Bereitstellung.

## Dienste und Grenzen

- `edge`: einziger öffentlich exponierter Container; TLS-Zertifikat wird als Secret
  eingebunden, keine automatische ACME-Abhängigkeit.
- `frontend`: Next.js Standalone und BFF; Zugriff auf Backend über `app_net`.
- `backend`: FastAPI; kein veröffentlichter Host-Port.
- `opa`: intern erreichbare, per Multi-Arch-Digest fixierte Policy Engine; read-only,
  ohne Host-Port oder Egress-Netz. Fehlende/unerreichbare Entscheidungen führen zu Deny.
- PostgreSQL: externer, privater Hetzner-Cluster beziehungsweise Dedicated-Host. Die
  Anwendung nutzt eine Rolle ohne Owner-, Superuser- oder `BYPASSRLS`-Rechte.
- Object Storage: privater S3-Bucket in `fsn1` oder `nbg1`.
- Azure OpenAI: einziger vorgesehener externer KI-Pfad; Zertifikatsidentität und
  freigegebene Datenklassen.

Das Frontend enthält keinen Azure-Blob- oder Azure-Identity-Storagepfad mehr. Persistente
Laufzeitobjekte verwenden ausschließlich die S3-kompatible Hetzner-Grenze; Entra bleibt
ein separater OIDC-Identitätspfad und Azure OpenAI eine klassifizierte Inferenz-Ausnahme.

`app_net` ist Docker-intern. `egress_net` ermöglicht technisch ausgehende Verbindungen,
ist aber noch keine Ziel-Allowlist. Vor Produktion muss der Host-Firewall-/Egress-
Proxy-Nachweis ausschließlich DNS, NTP, freigegebene Entra-Endpunkte, Azure OpenAI und
den gewählten Hetzner-S3-Endpunkt erlauben.

## Secret-Vertrag

Die Beispieldatei enthält nur nicht geheime Werte. Zielbetrieb verwendet OpenBao Agent,
der folgende Dateien atomar mit UID/GID des jeweiligen Containers und Modus 0400/0600
materialisiert:

```text
secrets/backend-database-url
secrets/postgres-password
secrets/s3-access-key
secrets/s3-secret-access-key
secrets/azure-openai-client-certificate.pem
secrets/bff-shared-secret
secrets/audit-pseudonymization-key
secrets/credential-pepper
secrets/internal-health-api-key
secrets/entra-client-secret
secrets/auth-transaction-secret
secrets/lead-admin-secret
secrets/tls-certificate.pem
secrets/tls-private-key.pem
```

Dateibasierte Compose-Secrets sind Bind-Mounts; Docker Compose setzt deren deklarierte
UID/GID/Moduswerte nicht um. Deshalb enthält `compose.yml` einen separaten
`x-secret-host-contract`. Der Release-Controller prüft vor jedem mutierenden Schritt,
dass jede Quelldatei regulär, kein Symlink, Eigentum der vorgesehenen numerischen
Container-UID und exakt `0400` ist. Zusätzlich bindet der Vertrag Mindestlänge,
Inhaltstyp, die einzigen zulässigen Verbraucher und eine Rotationsklasse. Der Preflight
gleicht die Verbraucher gegen die tatsächlichen Compose-Mounts ab, prüft einzeilige
opaque Werte, vollständige PostgreSQL-DSNs und PEM-Marker und gibt dabei niemals
Secret-Inhalte aus. Die YAML-Langsyntax selbst wird nicht als Berechtigungsnachweis
behandelt.

Die Rotationsklassen sind verbindliche Betriebsverfahren, keine Behauptung bereits
erfolgter Rotation:

- `standard_90d`: spätestens alle 90 Tage oder unmittelbar nach Expositionsverdacht;
  neuer Wert, abhängige Sitzung/Verbindung, Funktionsprüfung, danach Widerruf des alten.
- `certificate_lifecycle`: Erneuerung vor dem 30-Tage-Ablaufgate, Ketten-/Key-Pair-Prüfung
  und anschließender Widerruf des Vorgängers.
- `coordinated_change_window`: Vier-Augen-Change mit gemeinsamem Neustart abhängiger
  Dienste; bei `credential-pepper` inklusive geplanter API-Key-/Session-Neuausstellung.

API-Keys, Passwörter oder private Schlüssel dürfen weder in `.env.production`, Compose,
Container-Image, CI-Variablen-Ausgabe noch Logs gelangen. BFF-Vertrauensanker,
Pseudonymisierungsschlüssel sowie Entra- und Transaktionsgeheimnisse werden im
Produktionsprofil ausschließlich aus diesen Secret-Dateien gelesen. Globale API-Keys
bleiben im Enterprise-Profil verboten.

`credential-pepper` ist ein eigener, mindestens 32 Zeichen langer OpenBao-Wert. Er
schützt die deterministischen Datenbankindizes von API-Keys und Sessions per HMAC und
darf weder mit dem Audit-Pseudonymisierungsschlüssel geteilt noch nach dem Go-live ohne
eine geplante API-Key-Rotation gewechselt werden.

HubSpot, Pipedrive, Stripe und deren produktive Adapter sind im souveränen
Produktionsprofil technisch gesperrt. Zulässig sind nur selbst betriebene
HTTPS-Webhooks, deren Ziel-URL serverseitig konfiguriert ist und deren Host explizit
in der jeweiligen `COMPLIANCEHUB_*_ALLOWED_HOSTS`-Liste steht. Request-Daten dürfen
kein Netzwerkziel bestimmen. Webhook-Geheimnisse werden ausschließlich als
OpenBao-Datei eingebunden; Query-Secrets sind in Produktion deaktiviert. Der GTM-
Scheduler sendet nur eine fünf Minuten gültige HMAC-Signatur, nicht das Secret selbst.

Optionale Dependency-Telemetrie ist ebenfalls kein freigegebener Egress-Pfad.
`HAYSTACK_TELEMETRY_ENABLED=false` wird bereits vor dem ersten Haystack-Import
erzwungen und zusätzlich durch Container-, Compose- und Startup-Vertrag geprüft.
LangSmith-/LangChain-Tracing wird am gleichen frühen Paket-Rand deaktiviert; API-Key-,
Endpoint- und Tracing-Konfigurationen führen in Produktion zum Startabbruch.
PostHog-Konfiguration ist im `standard_dach`-Profil gesperrt. Anwendungsmetriken dürfen
nur über den selbst betriebenen, inhaltlich minimierten Observability-Pfad laufen.

Temporal ist kein stiller SaaS-Abhängigkeitspfad. Die Referenzkonfiguration hält die
Orchestrierung deaktiviert. Eine spätere Aktivierung ist nur für einen selbst gehosteten,
privaten Cluster mit exakter Host-Allowlist vorgesehen; Temporal-Cloud-API-Keys werden
im restriktiven Produktionsprofil abgewiesen.

Die Container-Startreihenfolge ist ebenfalls fail-closed: Der Backend-Probe liest seinen
Monitoring-Schlüssel ausschließlich aus der OpenBao-Datei und prüft Anwendung,
PostgreSQL-Verbindung, eine echte OPA-Entscheidung und die Konfigurationslage des
optionalen KI-Pfads. Das Frontend
startet erst bei gesundem Backend, der Edge erst bei gesundem Frontend. Der KI-Status ist
kein Nachweis der Azure-Erreichbarkeit. `INTERNAL_HEALTH_AI_PROVIDER_SIGNAL` ist nur ein
statischer, kontrollierter Operator-Override für Wartung oder einen bestätigten Vorfall;
es ist kein dynamischer Monitoring-Rückkanal. Ein getrennter, selbst betriebener
Synthetic Check soll Azure mit einem minimierten, nicht personenbezogenen Testaufruf
überwachen und sein Ergebnis unabhängig an die interne Observability und Alarmierung
melden. Seine Berechtigung und Testdaten werden getrennt vom Anwendungspfad verwaltet.

## Vorbereitungsprüfung

Backend-, Frontend-, Edge- und OPA-Basisimages sind im Blueprint über Multi-Arch-Digests
fixiert. Python-Laufzeitabhängigkeiten werden aus `requirements.lock` mit Paket-Hashes
installiert; Änderungen an `pyproject.toml` erfordern eine kontrollierte Regeneration
und erneute SCA-Prüfung des Locks. CI erzeugt für Backend und Frontend CycloneDX-SBOMs
und bewahrt sie als Release-Vorbereitungsartefakte auf. Eine Signatur beziehungsweise
Attestierung des finalen Container-Digests bleibt Teil des Cutover-Gates.

Die Anwendungsimages verwenden eine digest-fixierte Alpine-3.23-Laufzeit. Build-Werkzeuge
bleiben in getrennten Stages; das Frontend entfernt npm, npx und Corepack, das Backend
pip, setuptools und wheel vor der Runtime. Diese Reduktion ersetzt keinen Scan. Ein
zeitnaher High/Critical-Trivy-Scan beider finalen Images ist bei jedem Build sowie nach
jeder Vulnerability-DB- oder Base-Image-Aktualisierung erneut auszuführen. Neue Findings
blockieren die Freigabe; ein bloß älterer grüner Bericht ist kein aktueller Nachweis.
Die gepinnten Base-Image-Digests werden mindestens monatlich und anlassbezogen nach einem
relevanten CVE-Advisory kontrolliert aktualisiert, vollständig neu gebaut und erneut
unter Non-root-, read-only-, Capability-Drop- und No-new-privileges-Bedingungen geprüft.

Compose baut auf dem Produktionshost keine Anwendung mehr. `COMPLIANCEHUB_BACKEND_IMAGE`
und `COMPLIANCEHUB_FRONTEND_IMAGE` müssen vollständige Registry-Referenzen mit Digest
sein. CI baut beide Dockerfiles und sperrt bei jedem bekannten High- oder Critical-
Finding. Der Trivy-JSON-Bericht wird als Evidence-Artefakt aufbewahrt.

Die Produktionsfreigabe ist an `release-evidence.json` gebunden. Das Dokument enthält
keine vertrauenswürdigen Schlüssel: Builder und unabhängiger Approver signieren denselben
kanonischen Inhalt mit getrennten Ed25519-Identitäten. Deren öffentliche Schlüssel liegen
root-owned außerhalb von Repository, Container und Evidence-Paket. Die `key_id` ist der
lowercase SHA-256-Hash des rohen 32-Byte-Public-Keys. Private Schlüssel bleiben in zwei
getrennten Signer-/HSM-Grenzen und dürfen nicht auf dem Deployment-Host liegen. Das
jeweilige `subject` muss zusätzlich mit `built_by` beziehungsweise `approved_by`
übereinstimmen; damit kann eine gültige Signatur nicht unter fremder Identität erscheinen.

Auf dem Deployment-Host wird der Verifier in einer dedizierten root-owned Python-3.11-
Umgebung betrieben. `cryptography` und seine Transitivabhängigkeiten werden während der
Host-Provisionierung aus dem geprüften `requirements.lock` mit `--require-hashes`
installiert; der Cutover selbst führt keine Paketinstallation und keinen Internetzugriff
aus. `/opt/compliancehub-release-venv` ist nicht durch die Deployment-Rolle beschreibbar.

Der zu signierende Inhalt wird deterministisch ausgegeben mit:

```bash
/opt/compliancehub-release-venv/bin/python ../../scripts/print_release_hashes.py \
  --deployment-env .env.candidate \
  --deployment-dir .

/opt/compliancehub-release-venv/bin/python ../../scripts/verify_release_evidence.py release-evidence.json \
  --print-signing-payload > release-signing-payload.json
```

Der erste Befehl liefert den kanonischen Hash der vollständigen nicht geheimen
Kandidatenkonfiguration (der zirkuläre Evidence-Hash wird ausgelassen) sowie den Hash
aus `compose.yml`, `Caddyfile` und der OPA-Policy. Beide Werte werden vor den
Builder-/Approver-Signaturen in die Evidence übernommen. Die Env-Datei erlaubt nur den
dokumentierten literalen dotenv-Teilumfang; Quotes, Dollar-Expansion, Backslashes und
Inline-Kommentare sind gesperrt, damit Signatur- und Compose-Auslegung nicht divergieren.
Beim ersten Lauf kann der Helfer den aktuellen Blueprint-Hash mit Fehlerstatus ausgeben;
dieser wird in `COMPLIANCEHUB_RELEASE_BLUEPRINT_SHA256` eingetragen. Erst der zweite,
erfolgreiche Lauf liefert danach den signierbaren Konfigurationshash.

Nach dem Signieren wird zuerst der SHA-256-Hash der final serialisierten
`release-evidence.json` in `COMPLIANCEHUB_RELEASE_EVIDENCE_SHA256` übernommen. Unmittelbar
vor `docker compose pull` und `up` muss dann der vollständige Gate-Befehl erfolgreich sein:

```bash
/opt/compliancehub-release-venv/bin/python ../../scripts/verify_release_evidence.py release-evidence.json \
  --expected-commit HEAD \
  --deployment-env .env.production \
  --builder-public-key /etc/compliancehub/release-trust/builder-ed25519.pem \
  --approver-public-key /etc/compliancehub/release-trust/approver-ed25519.pem \
  --backend-sbom artifacts/backend.cdx.json \
  --frontend-sbom artifacts/frontend.cdx.json \
  --deployment-dir .
```

Der Gate prüft Struktur und Ablaufdatum, Vier-Augen-Trennung, Commit, Image-Digests,
SBOM-Dateihashes und CycloneDX-Struktur, Security-/Restore-/Rollback-Freigaben, beide
Signaturen sowie die exakt von Compose gelesenen Release-ID-, Commit-, Evidence-Hash- und
Image-Werte. Fehlende Argumente,
falsche Schlüssel, ein nachträglich geändertes JSON oder eine abweichende Env-Datei führen
zu einem Fehlerstatus. Das Beispiel bleibt absichtlich nicht freigabefähig.

Der Anwendungscontainer führt in Produktion weder `create_all` noch Migrationen aus.
Schemaänderungen werden zuvor mit einer separaten DDL-Rolle, eigenem Change Window und
Vier-Augen-Freigabe ausgeführt. Der Runtime-Pfad ruft ausschließlich den read-only
`verify_db_schema.py` auf. Die Release-Evidence akzeptiert deshalb nur `none` oder
`backward_compatible_expand`; Contract-/Breaking-Migrationen sind in diesem
In-Place-Verfahren technisch gesperrt.

## Release-Controller

`.env.production` beschreibt die laufende, `.env.candidate` die freigegebene neue
Version; beide sind root-owned und `0600`. Die neue Evidence muss den aktuellen Stand
als exakten Rollback-Zielpunkt binden. Der risikofreie Planlauf lautet:

```bash
/opt/compliancehub-release-venv/bin/python ../../scripts/hetzner_release.py plan \
  --deployment-dir .
```

Er prüft sauberen Git-Checkout, unabhängige Signaturen, SBOMs, komplette Env-/Blueprint-
Bindung, reale Secret-Eigentümer und -Modi, Rollback-Ziel und beide Compose-Auflösungen.
Er startet, zieht und ersetzt keine Container; lediglich das exklusive Lock wird
koordiniert. Erst nach erfolgreichem Change-Window-Review ist die mutierende Form zulässig:

```bash
/opt/compliancehub-release-venv/bin/python ../../scripts/hetzner_release.py apply \
  --deployment-dir . \
  --confirm-release-id REL-YYYY-NNNN
```

Der Apply-Pfad verifiziert zuerst die laufenden Release-Labels und den lokalen TLS-Edge,
zieht beide Rollback-Images und danach den Kandidaten, führt Frontend- und read-only
DB-Preflight im Kandidatenimage aus, ersetzt die Env-Datei atomar und wartet auf die
Readiness-Kette Backend → Frontend → Edge. Bei einem Fehler nach Promotion wird die
vorherige Env atomar restauriert, der alte Digest-Stand neu gestartet und erneut über
Labels und TLS geprüft. Ereignisse bilden eine lokale SHA-256-Hashkette; deren
unveränderliche externe Archivierung bleibt ein Betriebs-Gate.

Der Controller ist absichtlich nur für Application-Releases mit unverändertem
Deployment-Blueprint geeignet. Compose-, Caddy-, OPA- oder breaking DB-Änderungen
benötigen einen gesonderten Blue/Green-Infrastruktur-Change; ein automatischer Rollback
mit einem anderen Blueprint wird verweigert. Ein erstmaliger Hetzner-Bootstrap ist
ebenfalls ein separates, dokumentiertes Verfahren und wird nicht als bestehender
Rollback-Punkt fingiert.

```bash
cd deploy/hetzner
COMPLIANCEHUB_ENV_FILE=.env.production.example \
  docker compose --env-file .env.production.example -f compose.yml config --quiet

cd ../../frontend
npm ci
npm run lint
npx tsc --noEmit
npm run test:unit
npm run build

cd ..
docker build -f Dockerfile.hetzner -t compliancehub-backend:verify .
docker build -f frontend/Dockerfile.hetzner -t compliancehub-frontend:verify .
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest tests/ -q
```

## Cutover-Gate

Ein Merge in `main` oder DNS-Cutover ist erst zulässig, wenn alle Punkte belegt sind:

1. Images aus geprüftem Commit gebaut, signiert, gescannt und über Digest referenziert.
2. Hetzner-Verträge, AVV, Standort `fsn1`/`nbg1` und Subprozessoren dokumentiert.
3. PostgreSQL-Migration, `FORCE RLS`, Cross-Tenant-Negativtests und Least-Privilege-Rollen grün.
4. S3-Bucket privat; Versionierung, Lifecycle, Restore und Credential-Rotation getestet.
5. OpenBao unseal/recovery, Rotation und Break-Glass mit Vier-Augen-Prinzip getestet.
6. Azure EU Deployment-Typ, DPA/SCC/TIA, Abuse-Monitoring und Zertifikatsrotation geprüft.
7. Egress-Allowlist, Host-Firewall, Patch-Prozess, Monitoring und Alarmierung geprüft.
8. Backup-Restore und dokumentierte Rollback-Probe erfolgreich.
9. Vorheriger Vercel-Datenpfad inventarisiert; DNS-TTL, Rückfallfenster und anschließend
   vollständige Deprovisionierung dokumentiert.
10. Trust Center erst nach Cutover von „Vercel“ auf den belegten Hetzner-Stand aktualisiert.

Solange einer dieser Punkte fehlt, bleiben die zugehörigen `*_READY`-Variablen `false`.
Der Frontend-Container prüft die tatsächliche Runtime-Konfiguration unmittelbar vor
dem Start von Next.js. Mit offenen Gates beendet er sich fail-closed; die Compose-Datei
ist daher absichtlich noch kein startfähiger Produktionsnachweis.
