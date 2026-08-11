# Evidence and compliance copy

Use this reference for regulated, security-sensitive, public-sector, financial, healthcare, legal, or enterprise governance products.

## Claim ladder

Classify every material statement before publishing it.

| State | Meaning | Allowed phrasing |
|---|---|---|
| Verified | Directly observable in code, configuration, test, or dated evidence | "Strict CSP is active for the public release." |
| Configured | Implemented but dependent on the deployment environment | "Supports Microsoft Entra ID when enabled for the tenant." |
| Gated | Requires instance-specific technical, legal, or operational evidence | "Azure OpenAI is gated pending region, identity, and privacy approval." |
| Planned | Approved direction without a completed release | Use roadmap or future tense only. |
| Unsupported | Not implemented or intentionally excluded | State the boundary plainly. |

## Non-negotiable boundaries

- Never imply legal advice, certification, regulatory approval, or guaranteed compliance.
- Never turn a score, model output, or automation into a legal classification or deployment authorization.
- Attribute final approvals to a qualified human role.
- Keep data region, identity mode, retention, model provider, and integration claims environment-specific.
- Distinguish a stateless public site from an authenticated enterprise runtime.
- Place limitations next to the claim they qualify, not only in a footer.

## Strong copy patterns

Prefer:

- "Bereitet Evidence für qualifizierte Prüfung vor."
- "Offen bis zur dokumentierten Freigabe."
- "Produktive Verbindung wird instanzbezogen geprüft."
- "Keine automatische Rechtsentscheidung."
- "Illustrative Produktlogik."

Avoid:

- "Vollständig DSGVO-konform"
- "EU AI Act zertifiziert"
- "Garantiert revisionssicher"
- "Automatisch rechtssicher"
- "Nahtlose Integration" without implemented, tested evidence

## Evidence proximity

Pair a claim with the nearest useful proof:

- Security claim: control name, release profile, test, or trust-center link
- Product capability: real product view, interaction, or implemented workflow
- Integration: identity/data/AI/operations plane plus exact release state
- Executive outcome: accountable workflow and decision owner, not invented ROI

If public proof is unavailable, reduce the claim rather than manufacturing social proof.
