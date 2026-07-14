# Security parser and SAST hardening — 15 July 2026

Status: implementation verified; independent assurance still required

## Control objective

Remove the complete known Bandit backlog without suppressing findings, while preserving XML export,
database-migration, governance, remediation, IAM and Trust Center behavior.

## Implemented controls

- Central XML boundary in `app/xml_security.py` with a 5 MiB input limit.
- DTD, entity declaration and external reference processing disabled for untrusted XML.
- Generic parser errors prevent local paths or attacker-controlled parser details from entering API
  responses and logs.
- Escaped XML construction shared by XRechnung, GoBD and KI-register exports.
- SQLAlchemy Core reflection and `insert().from_select()` replace dynamic identifier interpolation in
  the SQLite compliance-deadline rebuild.
- Static migration-ledger SQL retains bound parameters for all variable values.
- Runtime error branches replace assertions that disappear under optimized Python execution.
- Trust Center signing accepts only elliptic-curve private keys and fails closed on malformed, RSA or
  encrypted/unavailable key material.

## Verification evidence

- XXE, DTD/entity-expansion, escaping and size-boundary tests.
- Migration regression proves existing tenant data survives the SQLite rebuild.
- Trust Center regression proves a valid RSA private key cannot enter the ECDSA signing boundary.
- Ruff lint and formatting checks passed across `app` and `tests` (577 files).
- The complete backend suite passed (1,538 tests).
- The complete application Bandit scan passed with zero findings and no suppressions.
- `pip-audit` reported no known vulnerabilities in resolvable third-party packages; the unpublished
  local `compliancehub` package is expectedly not present on PyPI and was not audited as a package.

## Residual controls

- Production ingress/WAF request-size limits must be at least as strict as the application limit.
- XML schema/business-rule conformance still requires the approved KoSIT/XRechnung validator; the
  in-application validation is intentionally structural and security-focused.
- Key storage, rotation and recovery require operator evidence from the approved Azure secret store.
- Independent security review and production-equivalent negative testing remain mandatory G3/G4
  evidence.
