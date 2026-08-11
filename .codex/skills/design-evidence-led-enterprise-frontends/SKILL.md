---
name: design-evidence-led-enterprise-frontends
description: Design, redesign, audit, polish, or harden credible enterprise SaaS frontends for regulated or high-trust products. Use for React, Next.js, HTML/CSS, landing pages, public product sites, trust centers, governance dashboards, compliance software, DACH/EU-facing interfaces, executive workflows, or requests for Apple-, GitHub-, Anthropic-, Google-, NVIDIA-, or consulting-grade visual quality without copying their trade dress. Combines product truth, evidence-led compliance copy, anti-slop visual direction, accessibility, responsive browser QA, security-aware implementation, and machine-readable DESIGN.md governance.
---

# Design Evidence-Led Enterprise Frontends

Create distinctive enterprise interfaces whose credibility comes from product truth, information hierarchy, interaction quality, and verifiable boundaries. Treat regulatory honesty as part of the visual system.

## Load only the required references

- For every regulated or high-trust interface, read `references/evidence-and-compliance-copy.md`.
- For a redesign, new surface, or visual audit, read `references/enterprise-design-system.md`.
- Before validation, read `references/quality-gates.md`.
- When creating or updating `DESIGN.md`, read `references/design-md-template.md`.

Read each selected reference completely before acting. Do not load references that the task does not need.

## Workflow

### 1. Establish authority and scope

Determine whether the request authorizes review, local implementation, dependency changes, deployment, or external publishing. Do not convert a design request into a deploy or legal approval.

Classify the work:

- **Targeted evolution:** Preserve routes, navigation labels, anchors, analytics identifiers, legal copy, product evidence, and brand recognition.
- **New surface:** Extend the existing system and document new tokens or patterns.
- **Rebrand or concept:** Explore distinct directions only when the user authorizes a broader identity change.

Inspect repository instructions, dirty worktree state, framework, release profiles, security headers, CSP constraints, tests, and existing `PRODUCT.md` or `DESIGN.md` before editing.

### 2. Build the truth model before the visual model

Create an internal claim matrix with these states:

1. Verified: directly observable in code, configuration, tests, or dated evidence
2. Configured: implemented but environment-dependent
3. Gated: pending instance-specific or dated evidence
4. Planned: approved direction without a completed release
5. Unsupported or prohibited

Use only states 1 and 2 as present-tense product claims. Label state 3 as gated. Keep states 4 and 5 out of promotional proof.

Never invent customers, logos, certifications, metrics, percentages, integrations, testimonials, audits, legal conclusions, or deployment readiness. Separate public-site properties from enterprise runtime properties.

### 3. Write the five-line experience brief

Before implementing, record:

1. Primary user and decision they need to make
2. Emotional target: calm, precise, inspectable, accountable
3. One visual thesis tied to the product mechanism
4. Existing elements that must remain recognizable
5. Patterns explicitly excluded

Set three dials from 1 to 10:

- `DESIGN_VARIANCE`: layout asymmetry and visual distinctiveness
- `MOTION_INTENSITY`: animation amount and amplitude
- `VISUAL_DENSITY`: information density and operational detail

Default regulated enterprise values are variance 5, motion 4, density 5. Change them only for a product reason.

### 4. Choose a product-specific visual thesis

Derive the design from the product's operating model, such as evidence chain, control plane, release gate, decision ledger, assurance map, or governance graph. Do not default to glass panels, glowing orbs, decorative grids, gradient blobs, generic dashboards, or interchangeable card collections.

Translate references into principles, never copied assets or trade dress:

- GitHub-like precision: compact navigation, strong reading order, proof close to claims
- Apple-like restraint: one dominant idea, controlled type, excellent media treatment
- Anthropic-like clarity: plain language, visible limitations, human responsibility
- Consulting-grade structure: decision framing, progressive disclosure, executive relevance

### 5. Design the page narrative

Prefer this sequence when it matches the product:

1. Asymmetric hero with one clear promise and one product or media artifact
2. Factual assurance rail with only verifiable properties
3. Operating model from scope to decision
4. Interactive product logic or real product evidence
5. Integration and architecture boundaries
6. Release, security, or trust gate
7. One focused conversion surface

Do not force this structure onto product workflows or dashboards. Preserve task efficiency over marketing rhythm inside authenticated applications.

### 6. Apply the visual system

Use a restrained light canvas, one interaction accent, deep neutral ink, and bounded dark product previews when justified. Prefer borders, alignment, whitespace, and tonal layers over shadows.

Use:

- 8px control radii and up to 16px major surface radii
- 44px minimum interactive targets
- Display tracking no tighter than `-0.04em`
- Body lines near 55 to 70 characters
- One dominant action per section
- Real imagery, product captures, diagrams, or authored graphics with meaningful alt text

Avoid:

- Pills for ordinary labels or navigation
- Repeated equal-width three-card grids
- Uppercase eyebrow labels
- Excessive badges, floating panels, or nested rounded cards
- Fake text logos or invented numerical dashboards
- Em dashes and en dashes in visible interface copy
- Display type above 96px without a documented reason
- `transition-all`, perpetual motion, or hover movement that shifts layout

### 7. Implement without weakening the product boundary

Preserve semantic HTML, server/client component boundaries, CSP, security headers, release profiles, deep links, analytics, and legal routes. Keep interactive islands small. Avoid client waterfalls and unnecessary effects.

For carousels, tabs, previews, and disclosure controls:

- Expose correct roles, labels, selected state, and control relationships
- Support keyboard operation
- Pause autoplay on focus, hover, document invisibility, and reduced-motion preference
- Keep all essential content accessible without animation
- Use descriptive button text or accessible names

Do not bypass a strict CSP with unsafe inline script or style allowances merely to simplify a visual component.

### 8. Create durable design context

If product context is missing, create a concise `PRODUCT.md` covering users, purpose, positioning, operating constraints, truthful capabilities, evidence boundaries, and accessibility target.

After visual QA, create or update `DESIGN.md` using the official Google design.md structure. Tokens are normative; prose explains rationale. Document colors, typography, spacing, radii, components, forbidden patterns, motion, and claim integrity.

### 9. Validate the rendered result

Run the repository's lint, type, unit, build, security, and release gates. Do not substitute source inspection for a rendered browser review.

Test at 360, 768, 1280, and 1440 CSS pixels. Verify:

- No horizontal overflow or clipped actions
- Hero message and primary action remain legible
- Navigation stays operable
- All interactive states work by keyboard and pointer
- Reduced motion is respected
- Browser console contains no relevant errors or warnings
- Product limitations and legal boundaries remain visible

Run the bundled static audit once after the UI is finished:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/design-evidence-led-enterprise-frontends"
node "$SKILL_DIR/scripts/frontend_design_audit.mjs" --json <changed frontend files or directories>
```

Resolve each finding or document why it is a deliberate exception. The audit is a review aid, not a substitute for judgment.

### 10. Report evidence, not confidence theater

Lead with what changed and what was verified. Report exact test counts, build gates, viewports, console results, audit findings, and remaining evidence gaps.

Never claim absolute DSGVO, EU AI Act, security, accessibility, or legal compliance from code review alone. State which technical controls are verified and which organizational, contractual, operational, or legal evidence remains gated.

Do not commit, push, merge, deploy, or publish unless the user authorizes that action.
