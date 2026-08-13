# Compliance Hub Frontend

Next.js-Frontend und serverseitiges BFF für Compliance Hub.

## Lokale Entwicklung

```bash
npm ci
npm run dev
```

Vor Änderungen und Releases:

```bash
npm run lint
npx tsc --noEmit
npm run test:unit
npm run build
```

## Produktionsbetrieb

Der freigegebene Zielpfad ist ein Next.js-Standalone-Container auf Hetzner Deutschland.
Vercel ist kein zulässiger Zielprovider. Das Image wird vom Repository-Root aus gebaut,
damit die Prebuild-Gates auch die versionierten PostgreSQL-Verträge prüfen können:

```bash
docker build -f frontend/Dockerfile.hetzner -t compliancehub-frontend:verify .
```

Netzwerk-, Secret- und Reverse-Proxy-Grenzen stehen unter `../deploy/hetzner/`.

Produktive Laufzeitdaten verwenden:

- privates PostgreSQL mit Tenant-Kontext und `FORCE RLS`;
- privaten S3-kompatiblen Storage in Falkenstein oder Nürnberg;
- als Dateien gemountete, rotierte Secrets aus OpenBao;
- Azure ausschließlich für explizit freigegebene Entra-/LLM-Funktionen.

Die Release-Attestierungen bleiben `false`, bis ihre jeweiligen Runbook-Nachweise
vorliegen. Das Vorhandensein der Containerdateien ist kein Produktionsnachweis.
