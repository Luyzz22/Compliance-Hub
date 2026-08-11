---
version: alpha
name: Compliance Hub Governance Ledger
description: A precise, evidence-led enterprise interface for regulated AI governance in the DACH market.
colors:
  canvas: "#F6F8FA"
  surface: "#FFFFFF"
  surface-subtle: "#EEF2F6"
  ink: "#1F2328"
  ink-soft: "#32383F"
  muted: "#59636E"
  border: "#D8DEE4"
  border-strong: "#AFB8C1"
  primary: "#0969DA"
  primary-hover: "#0550AE"
  on-accent: "#FFFFFF"
  product-canvas: "#1F2328"
  product-muted: "#CBD5E1"
typography:
  display:
    fontFamily: "SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 60px
    fontWeight: 600
    lineHeight: 0.98
    letterSpacing: -0.04em
  heading-lg:
    fontFamily: "SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 52px
    fontWeight: 600
    lineHeight: 1.08
    letterSpacing: -0.035em
  heading-md:
    fontFamily: "SF Pro Display, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 36px
    fontWeight: 600
    lineHeight: 1.1
    letterSpacing: -0.03em
  heading-sm:
    fontFamily: "SF Pro Text, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 24px
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: -0.02em
  body-lg:
    fontFamily: "SF Pro Text, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 18px
    fontWeight: 400
    lineHeight: 1.75
  body-md:
    fontFamily: "SF Pro Text, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 16px
    fontWeight: 400
    lineHeight: 1.75
  body-sm:
    fontFamily: "SF Pro Text, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 14px
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "SF Pro Text, -apple-system, BlinkMacSystemFont, Segoe UI, sans-serif"
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.35
  technical-label:
    fontFamily: "SFMono-Regular, Cascadia Code, ui-monospace, monospace"
    fontSize: 12px
    fontWeight: 600
    lineHeight: 1.5
rounded:
  none: 0px
  control: 8px
  surface: 16px
spacing:
  hairline: 1px
  micro: 4px
  xs: 8px
  sm: 12px
  md: 16px
  lg: 24px
  xl: 32px
  section-mobile: 80px
  section-desktop: 128px
  page-gutter-mobile: 16px
  page-gutter-desktop: 32px
  max-width: 1440px
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-accent}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.control}"
    padding: 12px
    height: 44px
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-accent}"
  button-secondary:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink}"
    typography: "{typography.body-sm}"
    rounded: "{rounded.control}"
    padding: 12px
    height: 44px
  control-button:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.muted}"
    typography: "{typography.label}"
    rounded: "{rounded.control}"
    height: 44px
  product-preview:
    backgroundColor: "{colors.product-canvas}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.surface}"
    padding: 24px
  page-shell:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.ink}"
  section-subtle:
    backgroundColor: "{colors.surface-subtle}"
    textColor: "{colors.ink-soft}"
  divider:
    backgroundColor: "{colors.border}"
    height: 1px
  divider-strong:
    backgroundColor: "{colors.border-strong}"
    height: 1px
  product-copy-muted:
    textColor: "{colors.product-muted}"
    typography: "{typography.body-sm}"
---

# Compliance Hub Governance Ledger

## Overview

Compliance Hub should feel like an accountable enterprise operating system, not a campaign microsite. The visual thesis is a governance ledger: precise reading order, restrained surfaces, visible boundaries and product evidence placed close to each claim. The primary audiences are board members, compliance teams, information security, procurement and qualified advisors in regulated DACH organizations.

The public site is intentionally calm, credible and inspectable. It must distinguish implemented public-release properties from separately gated enterprise capabilities. Product copy never presents the service as legal advice, certification or an automatic decision maker.

## Colors

The system uses a light institutional canvas, white working surfaces and deep neutral ink. Cobalt is the only interactive accent and signals links, selected states and the highest-priority action. Green, amber and red may appear only when a real product status needs them; they are not decorative brand colors.

The dark `product-canvas` is reserved for bounded product demonstrations. It must not become a second page theme. Text and controls must meet WCAG 2.2 AA contrast in every state.

## Typography

SF Pro is the preferred system face, with native platform fallbacks so the public site adds no external font dependency. Display headings use tight but controlled tracking and a maximum weight of 600. Body text stays generous and readable, normally between 55 and 70 characters per line.

Technical labels use the monospaced stack only for control names, release states and evidence metadata. Avoid uppercase eyebrow labels, ornamental tracking and oversized display type above 96px.

## Layout

The public shell uses a fluid layout capped at 1440px, with 16px mobile gutters and 32px desktop gutters. Primary narratives are asymmetric: one concise claim is paired with one explanatory product or image artifact. Sections use 80px vertical spacing on mobile and up to 128px on desktop.

Use borders and aligned rows to express relationships before introducing cards. Preserve the established routes, anchors and analytics identifiers. At 360px, 768px, 1280px and 1440px there must be no horizontal overflow, clipped actions or hidden legal context.

## Elevation & Depth

Most hierarchy comes from tonal layers, whitespace and 1px borders. Shadows are limited to the hero visual, the bounded product preview and the final conversion surface. A shadow must reinforce an interactive or product artifact, never decorate ordinary prose.

Blur is permitted only on the sticky public header. Decorative grid backgrounds, glowing orbs, glass panels and ambient gradients are excluded from the public marketing system.

## Shapes

Controls use an 8px radius and major media or product surfaces use 16px. Structural sections and data rows remain square. Pill shapes are not a default container and must not be used for ordinary labels, navigation or status copy.

Use one radius per object. Nested containers should reduce or remove their radius instead of repeating concentric rounded cards.

## Components

- Primary buttons use cobalt, white text, a 44px minimum height and a visible pressed state.
- Secondary buttons use a white surface, strong neutral border and identical dimensions to primary buttons.
- Navigation communicates the current route with a simple bottom border; only the contact action receives a filled treatment.
- Hero slides place imagery above an independent caption region. Tabs support arrow, Home and End keys, expose tab semantics and pause when focused or hovered.
- Product previews must be labelled as illustrative unless their data comes from an authenticated product environment. They show relationships and outcomes, never invented performance metrics.
- Governance rows pair an explicit term, plain-language explanation and, when needed, a truthful release state.

## Do's and Don'ts

- Do place evidence, limitations and review responsibility close to the claim they qualify.
- Do use one dominant action per section and keep repeated action labels consistent.
- Do respect reduced-motion preferences and preserve a complete experience without animation.
- Do keep the public release stateless and describe Azure OpenAI and enterprise data handling as gated until dated evidence exists.
- Do not invent customers, logos, certifications, benchmarks, percentages or testimonials.
- Do not present legal interpretation, risk classification or deployment approval as an automatic system decision.
- Do not stack generic three-card feature grids, badges, floating pills or decorative dashboards.
- Do not use em dashes or en dashes in visible interface copy.
