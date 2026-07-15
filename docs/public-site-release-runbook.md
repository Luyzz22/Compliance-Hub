# Public-site production release

## Purpose

The `public_site` release profile publishes only the reviewed marketing, contact,
trust and legal pages on `https://complywithai.de`. It is deliberately isolated
from the authenticated application and from all stateful APIs.

This profile is not an enterprise-runtime waiver. The `enterprise` profile keeps
the complete Entra, Azure Blob, Azure PostgreSQL, CSP reporting and operational
evidence gates.

## Allowed runtime scope

- Public pages: `/`, `/kontakt`, `/trust-center`, `/impressum`, `/datenschutz`
- Public metadata: `/robots.txt`, `/sitemap.xml`, `/manifest.webmanifest`
- Responsible disclosure: `/.well-known/security.txt`
- No authentication, demo session, lead form, marketing telemetry or CSP-report
  ingestion
- No customer, tenant or application data

All other application and API paths return `404` at the proxy boundary before a
route handler executes.

## Required production configuration

Set only the following non-empty `COMPLIANCEHUB_*` variables for the public-site
profile. Optional phone and DPO contact values may be added after review.

```text
COMPLIANCEHUB_RELEASE_PROFILE=public_site
COMPLIANCEHUB_APP_ORIGIN=https://complywithai.de
COMPLIANCEHUB_TRUSTED_HOSTS=complywithai.de
COMPLIANCEHUB_PUBLIC_SITE_READY=true
COMPLIANCEHUB_LEGAL_PUBLISH_READY=true
COMPLIANCEHUB_LEGAL_*=<reviewed public legal data>
COMPLIANCEHUB_PRIVACY_*=<reviewed notice metadata and retention periods>
COMPLIANCEHUB_SECURITY_CONTACT=<reviewed https: or mailto: contact>
```

`COMPLIANCEHUB_PUBLIC_SITE_READY` and
`COMPLIANCEHUB_LEGAL_PUBLISH_READY` are attestations. They must never be set by
automation without the named owner and review evidence in the change record.

## Prohibited production configuration

The build fails if the public profile inherits any application-defined
`NEXT_PUBLIC_*`, `POSTGRES_*`, `SUPABASE_*`, `AZURE_*`, `DATABASE_URL`,
`PGPASSWORD`, or unapproved `COMPLIANCEHUB_*` value. Vercel-generated
`NEXT_PUBLIC_VERCEL_*` deployment metadata is permitted because Vercel injects it
into builds and it contains no application credential. Remove integration-created
variables from the Vercel production environment before deployment; do not replace
them with dummy values.

The following capabilities must be unset or `false`:

- public demo
- public lead capture
- Entra authentication
- CSP report collection

## Release procedure

1. Record legal owner approval for the exact imprint and privacy notice values.
2. Confirm the Vercel data-processing agreement, subprocessor disclosure,
   technically necessary log retention and international-transfer assessment.
3. Remove prohibited production variables and add only the approved public-site
   configuration.
4. Run `npm run lint`, `npm run test:unit` and a production `npm run build` with
   the exact release profile.
5. Deploy the reviewed commit through the protected `main` branch.
6. Verify the five public pages, `security.txt`, response headers and the expected
   `404` response for one app route and one stateful API route.
7. Record deployment ID, commit SHA, approver, test evidence and rollback target.

## Rollback

Promote the last reviewed production deployment in Vercel. Do not relax the
release gate to recover service. If the legal content is in doubt, rollback or
withdraw the affected page and keep stateful capabilities disabled.
