# Frontend CSP and runtime-boundary hardening — 15 July 2026

Status: implementation and local production-browser verification complete; deployed review and
independent assurance still required

## Control objective

Replace the static frontend policy that allowed inline script and style execution with a
request-specific, fail-closed CSP, remove the two known Starlette/FastAPI deprecations at source and
prevent mutable runtime files from entering Next.js output traces.

## Implemented controls

- Every matched request receives a fresh base64 nonce generated from `crypto.randomUUID()`.
- The same nonce is forwarded to Next.js through request headers and returned in the response CSP,
  allowing Next.js to nonce its framework scripts and generated inline assets.
- Production `script-src` uses the nonce and `strict-dynamic`; `unsafe-inline` and `unsafe-eval` are
  absent. Development retains only the React-required `unsafe-eval` exception.
- `script-src-attr 'none'` and `style-src-attr 'none'` explicitly reject executable attributes;
  frame, object and base/form targets are separately constrained.
- Nonce-bearing responses are marked `private, no-store`, and authentication/tenant redirects retain
  the same strict policy.
- API origins are reduced to validated HTTP(S) origins before entering `connect-src`.
- All 21 application React inline-style sites were replaced by static classes or accessible SVG
  geometry. A prebuild gate rejects future inline-style attributes, `dangerouslySetInnerHTML`,
  `unsafe-inline` and static CSP configuration.
- Twelve mutable server-side file stores now use a single `server-only` runtime-I/O boundary that
  requires absolute paths and prevents mutable files from being included in Turbopack output traces.
- Starlette `TestClient` uses the explicit `httpx2` development dependency. All deprecated 422
  constants use `HTTP_422_UNPROCESSABLE_CONTENT`.

## Verification evidence

- Frontend lint and the strict CSP prebuild gate passed.
- All 270 frontend unit tests passed, including policy construction, nonce uniqueness, redirect CSP
  preservation and inline-style-free visualization tests.
- The Next.js 16.2.10 production build completed without TypeScript, Turbopack or NFT warnings.
- All 1,538 backend tests passed with `StarletteDeprecationWarning` promoted to an error.
- Bandit reported zero findings; `pip-audit` reported no known third-party vulnerabilities.
- Two consecutive production-mode HTTP responses carried different nonces and `private, no-store`.
- Browser verification confirmed meaningful rendering, interactive tab navigation, no error overlay,
  no console/page errors, 26 of 26 scripts carrying nonces and the response nonce present in rendered
  HTML.
- Browser injection testing confirmed that an untrusted `style` attribute was not applied. The only
  remaining DOM style attribute belongs to Next.js' internal route announcer; application DOM nodes
  contain none.
- A protected workspace URL returned a policy-bearing 307 and rendered the login route successfully.

## Residual release controls

- Add a privacy-reviewed CSP reporting endpoint and alerting pipeline before production enforcement
  is considered fully observable; reports may contain URLs and therefore require retention and data
  minimization controls.
- Repeat the browser/header checks on the immutable Vercel preview and production candidate.
- The centralized runtime-I/O boundary prevents unsafe tracing but does not make `/tmp` durable.
  Product state must be migrated to approved Azure/Postgres/Blob persistence before production.
- Any future third-party script, frame, font or telemetry integration requires an explicit threat and
  privacy review plus a narrow policy amendment; no wildcard source is approved.
- Independent penetration testing and security-owner approval remain required release evidence.
