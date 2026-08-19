# Runbook: Öffentliche Website auf Hetzner

Ziel: `complywithai.de` läuft im souveränen Hetzner-Profil statt auf Vercel.

Dieses Runbook deckt **Stufe 1** ab — die öffentliche Website im Profil
`public_site`. Der vollständige Enterprise-Stack (Backend, OPA, PostgreSQL,
S3, OpenBao, Entra, Azure OpenAI) ist **Stufe 2** und folgt `README.md` sowie
`compose.yml`.

## Warum zwei Stufen

Der `public_site`-Release ist zustandslos: keine Anmeldung, keine
Mandantendaten, keine Zustands-APIs. `src/proxy.ts` weist jeden nicht
freigegebenen Pfad ab, und das Release-Gate lässt den Container gar nicht
starten, wenn Datenbank-, Storage- oder Identitätsvariablen gesetzt sind.

Damit braucht die Website weder PostgreSQL noch S3, OpenBao, Entra oder Azure
OpenAI. Sie braucht: einen Server, Docker, ein TLS-Zertifikat und DNS. Der
Apparat aus Stufe 2 ist für die Datenebene gedacht und für die Website
überdimensioniert — ihn vorzuziehen würde den Live-Gang um Wochen verzögern,
ohne die Schutzwirkung zu erhöhen.

## Ausgangslage (Stand 19.08.2026)

- `complywithai.de` wird von **Vercel** ausgeliefert.
- Der letzte erfolgreiche Deploy stammt vom **11.08.2026** (Commit `2d57a0a`).
- Seit dem 13.08.2026 schlägt dort **jeder** Build fehl:
  `Enterprise release gate failed: Vercel runtime variables are forbidden in
  the Hetzner-first profile`. Ursache ist PR #290, der das Hetzner-first-Gate
  eingeführt hat. Vercel setzt `VERCEL=1` selbst — der Check ist unbedingt.
- `preproduction-build.yml` ist **noch nie gelaufen**; der self-hosted Runner
  mit dem Label `compliancehub-hetzner-release` existiert nicht.

Die Website hängt damit auf einem Stand von vor mehreren Releases fest.

## Reihenfolge — die Website darf nicht offline gehen

Vercel bleibt bis zum DNS-Cutover die ausliefernde Plattform. Erst wenn der
Hetzner-Stack unter seiner eigenen Adresse verifiziert antwortet, wird DNS
umgestellt. Vercel wird **danach** stillgelegt, nicht vorher.

---

## Schritt 1 — Server

Hetzner-Server in `fsn1` oder `nbg1`, Debian oder Ubuntu LTS, Docker Engine
mit Compose-Plugin.

Host-Firewall: eingehend nur 22 (administrativ, idealerweise auf bekannte
Quell-IPs beschränkt), 80 und 443. Ausgehend genügt der Website DNS und NTP —
sie ruft keine externen Dienste auf. Das `egress_net` aus `compose.yml`
entfällt hier bewusst.

## Schritt 2 — Image bauen

Das Image trägt keine Konfiguration; alle Werte kommen zur Laufzeit. Der Build
selbst braucht daher keine Legal-Angaben.

```bash
git clone https://github.com/Luyzz22/Compliance-Hub.git
cd Compliance-Hub
git checkout main

docker build -f frontend/Dockerfile.hetzner -t compliancehub-frontend:build .
```

Digest festhalten — Compose verlangt eine unveränderliche Referenz:

```bash
docker image inspect compliancehub-frontend:build \
  --format '{{index .RepoDigests 0}}'
```

Ohne interne Registry gibt es noch keinen `RepoDigest`. Für Stufe 1 genügt es,
das lokal gebaute Image über seine Image-ID zu pinnen und Release-ID sowie
Commit in `.env` festzuhalten. Sobald die interne Registry aus Stufe 2 steht,
übernimmt `scripts/sovereign_release_build.py` Build, Scan, Signatur und
Attestierung.

## Schritt 3 — TLS-Zertifikat

Die `Caddyfile` setzt `auto_https off` und liest Zertifikat und Schlüssel aus
Docker-Secrets — bewusst ohne ACME-Abhängigkeit.

```bash
mkdir -p deploy/hetzner/secrets
# Zertifikatskette und privaten Schlüssel ablegen:
#   deploy/hetzner/secrets/tls-certificate.pem
#   deploy/hetzner/secrets/tls-private-key.pem
chmod 600 deploy/hetzner/secrets/tls-private-key.pem
```

`deploy/hetzner/.gitignore` hält `secrets/` aus dem Repository heraus — vor dem
ersten Commit auf dem Server verifizieren.

## Schritt 4 — Konfiguration

Zwei Dateien mit unterschiedlicher Rolle. Sie zu verwechseln ist der
naheliegendste Fehler:

| Datei | Rolle | Wirkung |
|---|---|---|
| `.env.public-site` | Container-Umgebung (`env_file`) | Wird vom Release-Gate geprüft |
| `.env` | Compose-Substitution für `${...}` | Erreicht den Container **nicht** |

Die Compose-Parameter (`COMPLIANCEHUB_PUBLIC_HOST`, `…_FRONTEND_IMAGE`,
`…_RELEASE_ID`, `…_RELEASE_COMMIT`) beginnen mit `COMPLIANCEHUB_`, stehen aber
**nicht** auf der Allowlist des `public_site`-Profils. Landen sie in der
Container-Umgebung, bricht der Start ab.

```bash
cd deploy/hetzner
cp .env.public-site.example .env.public-site
cp .env.compose.example .env
```

In `.env.public-site` sind die rechtlichen Pflichtangaben zu ergänzen — nach
dokumentierter rechtlicher Prüfung, nicht vorläufig. Erst danach
`COMPLIANCEHUB_LEGAL_PUBLISH_READY=true` setzen.

## Schritt 5 — Preflight

Prüft dieselben Invarianten wie das Gate im Container, aber bevor irgendetwas
startet:

```bash
python3 deploy/hetzner/preflight-public-site.py \
  deploy/hetzner/.env.public-site --compose-env deploy/hetzner/.env
```

Exit 0 bedeutet ausrollbar. Jeder Befund wird einzeln benannt.

## Schritt 6 — Start und Verifikation

```bash
cd deploy/hetzner
docker compose -f compose.public-site.yml up -d
docker compose -f compose.public-site.yml ps
docker compose -f compose.public-site.yml logs frontend | head -20
```

Im Log muss stehen: `Enterprise release gate passed (public_site)`.

Vor dem DNS-Wechsel gegen die Server-IP prüfen, mit `Host`-Header, damit Caddy
den richtigen Vhost bedient:

```bash
IP=<server-ip>
for p in / /plattform /eu-ai-act-iso-42001 /nis2-kritis /fuer-beratungen \
         /integrationen /sicherheit /ressourcen /produkt-tour /demo \
         /kontakt /trust-center /impressum /datenschutz; do
  code=$(curl -sS -o /dev/null -w '%{http_code}' \
    --resolve "complywithai.de:443:$IP" "https://complywithai.de$p")
  echo "$p -> $code"
done
```

Alle vierzehn Pfade müssen 200 liefern. Zusätzlich prüfen:

- `/auth/login` und `/board/kpis` müssen **404** liefern — der zustandslose
  Release gibt die Anwendung nicht frei.
- `curl -sSI` zeigt `content-security-policy` mit `nonce-…` und **ohne**
  `unsafe-inline`.
- Der Antwort-Header `server: Vercel` ist verschwunden.

## Schritt 7 — DNS-Cutover

Erst wenn Schritt 6 vollständig grün ist:

1. TTL des bestehenden Eintrags vorab auf 300 s senken und die alte TTL
   ablaufen lassen.
2. A- und AAAA-Record auf die Server-IP umstellen.
3. Aus mehreren Netzen verifizieren, dass `server: Vercel` nicht mehr erscheint.
4. Erst danach das Vercel-Projekt stilllegen — Domain trennen und
   Git-Integration deaktivieren, damit keine fehlschlagenden Deploys mehr
   entstehen.

Rollback bis Schritt 4: DNS zurückstellen. Vercel liefert dann wieder den
Stand vom 11.08.2026 aus.

## Schritt 8 — Nachziehen

- `COMPLIANCEHUB_PRIVACY_REVIEWED_AT` muss jährlich erneuert werden; das Gate
  weist eine ältere Prüfung ab und der Container startet dann nicht mehr.
  Wiedervorlage setzen.
- Zertifikatserneuerung: Secret-Dateien ersetzen und `docker compose … up -d
  edge`. Ohne ACME ist das ein bewusster manueller Schritt.
- Stufe 2 (Enterprise-Datenebene) folgt `README.md`; sie verlangt zusätzlich
  self-hosted Runner, interne Registry, Paket-Mirrors, OpenBao, Cosign,
  PostgreSQL und S3.

## Was Stufe 1 bewusst nicht leistet

Signierte, attestierte Releases über `sovereign_release_build.py` setzen die
interne Registry und OpenBao aus Stufe 2 voraus. Bis dahin ist die Herkunft
über Release-ID, Commit und gepinnten Image-Digest nachvollziehbar, aber nicht
kryptografisch attestiert. Das ist für die zustandslose Website vertretbar und
sollte im Betriebskonzept als solches vermerkt werden — für die Datenebene
wäre es das nicht.
