# Quality gates

Run the checks appropriate to the repository and report exact results.

## Source and architecture

- Repository instructions followed
- Dirty worktree inspected and unrelated changes preserved
- Server/client boundaries remain intentional
- Existing routes, anchors, analytics, legal pages, and release profiles preserved
- No unsafe CSP relaxation or secret added to browser code

## Accessibility

- One logical `h1` and ordered headings
- Semantic landmarks and lists
- Keyboard access for every interaction
- Visible focus indicators
- 44px minimum control targets
- Meaningful image alternatives
- Selected, expanded, pressed, and controlled states exposed to assistive technology
- Reduced-motion behavior verified

## Responsive browser matrix

Inspect at 360, 768, 1280, and 1440 CSS pixels.

- `scrollWidth === clientWidth`
- Navigation and primary action remain usable
- No text, table, tab, or media clipping
- Headline wraps intentionally
- Mobile copy remains readable without hidden essential content
- Browser console: zero relevant errors and warnings

## Interaction

- Pointer and keyboard paths both work
- Arrow, Home, and End keys work for tab interfaces where applicable
- Autoplay can be paused
- Focus, hover, active, loading, empty, error, and disabled states are coherent
- Repeated CTAs retain consistent labels and tracking identifiers

## Engineering

Prefer repository-native commands. Common gates:

```bash
npm run lint
npx tsc --noEmit
npm run test:unit
npm run build
npm audit --omit=dev
```

Also run CSP, storage, authentication, tenant-isolation, and release-readiness gates when the repository provides them.

## Design governance

After rendered QA, validate `DESIGN.md` when present:

```bash
npx --yes @google/design.md lint DESIGN.md
```

Target zero errors and zero warnings. Run the bundled audit once on the final changed frontend targets:

```bash
SKILL_DIR="${CODEX_HOME:-$HOME/.codex}/skills/design-evidence-led-enterprise-frontends"
node "$SKILL_DIR/scripts/frontend_design_audit.mjs" --json <changed frontend files or directories>
```

Treat findings as prompts for review, not automatic proof of failure.

## Handoff

Report:

- Changed surfaces and preserved boundaries
- Exact test and build results
- Viewports and browser-console result
- Security and dependency audit result
- Remaining legal, organizational, operational, or deployment gates
- Whether changes are local, committed, pushed, merged, or deployed
