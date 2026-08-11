# DESIGN.md template

Create `DESIGN.md` after the rendered interface is stable. Use YAML tokens as normative values and markdown as rationale.

```yaml
---
version: alpha
name: Product Design System
description: A concise description of the product's visual and interaction character.
colors:
  primary: "#0969DA"
  primary-hover: "#0550AE"
  canvas: "#F6F8FA"
  surface: "#FFFFFF"
  ink: "#1F2328"
  muted: "#59636E"
  border: "#D8DEE4"
typography:
  display:
    fontFamily: "System UI, sans-serif"
    fontSize: 60px
    fontWeight: 600
    lineHeight: 0.98
    letterSpacing: -0.04em
  body:
    fontFamily: "System UI, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.7
rounded:
  control: 8px
  surface: 16px
spacing:
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  section: 96px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    rounded: "{rounded.control}"
    height: 44px
---
```

Use the markdown sections in this exact order:

1. `## Overview`
2. `## Colors`
3. `## Typography`
4. `## Layout`
5. `## Elevation & Depth`
6. `## Shapes`
7. `## Components`
8. `## Do's and Don'ts`

Document product-specific rationale, interaction behavior, responsive layout, motion, evidence boundaries, and forbidden patterns. Reference each color token from at least one component to avoid orphan-token warnings.

Validate with:

```bash
npx --yes @google/design.md lint DESIGN.md
```
