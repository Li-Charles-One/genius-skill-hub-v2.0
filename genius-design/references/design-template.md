# DESIGN.md Template

Copy the skeleton into a staged candidate. Replace every `TODO`, including dial integers, with values from this brief. The template does not pass lint until filled. Prose may use the user's language; keep contract keys and H2 names stable. `evals/fixtures/valid-design.md` is a linter gold file for a literary-press brief — do not copy its voice or palette unless this project is that product.

Required H2s: Design Read, Colors, Typography, Spacing and Shape, Layout, Components. Omit optional H2s when they have nothing to add. YAML rules: `references/output-contract.md`.

```yaml
---
schema_version: 1
name: TODO
mode: recommendation # brand-template | reverse-engineer | recommendation
design_read: TODO
scope:
  page_kind: TODO
  audience: TODO
  themes: [light] # Only requested/justified themes
dial_values:
  DESIGN_VARIANCE: TODO # integer 1-10 from this brief
  MOTION_INTENSITY: TODO
  VISUAL_DENSITY: TODO
layout:
  rhythm: TODO
  regions: [TODO, TODO]
  rationale: TODO
tokens:
  colors:
    light:
      background: TODO
      surface: TODO
      text: TODO
      text-muted: TODO
      accent: TODO
      border: TODO
      focus: TODO
  typography:
    font-body: TODO
    font-heading: TODO
    size-body: TODO
    size-heading: TODO
    line-height-body: TODO
    line-height-heading: TODO
  spacing:
    small: TODO
    medium: TODO
    large: TODO
components:
  button:
    interactive: true
    states: [default, focus-visible] # add hover/disabled/etc only if they apply
evidence:
  - id: direction
    kind: Recommended
    source: User brief
    claim: TODO
unknowns: []
exceptions: []
---
```

Markdown body (not inside the YAML fence):

## Design Read
Audience, primary task, vibe, retained constraints, and why each dial has its value. Distinguish measured facts from interpretation.

## Colors
Map each semantic role to its token, theme and usage. Extra accents and status/data colors need distinct roles. Contrast targets: measured or pending.

## Typography
Hierarchy, sizes, line heights, language coverage, licensing and fallbacks. Frontmatter tokens are canonical.

## Spacing and Shape
Spacing tokens, grouping, radius and elevation. Dense screens and editorial pages can use different scales.

## Layout
Named rhythm, real regions, order and content rationale. Unobserved breakpoints stay unknown or Recommended.

## Components
Purpose, variants, applicable states and token usage. No universal requirement that every element has success/error/loading states.

Optional H2s (omit when empty): Decisions and Overrides, Motion, Imagery, Accessibility, Honesty and Refusals, Anti-Patterns, Sources and Inference, Pre-Ship Checklist. If Pre-Ship Checklist is included, copy the 12 items from `references/output-contract.md`.
