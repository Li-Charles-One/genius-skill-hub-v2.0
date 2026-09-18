# DESIGN.md Template

Copy the document skeleton below into a staged candidate. Replace active `TODO` fields and select applicable themes, components, regions and evidence. The template intentionally does not pass lint until filled. Prose may use the user's language; keep contract keys and section headings stable for validation. The complete working fixture is `evals/fixtures/valid-design.md`.

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
  DESIGN_VARIANCE: 4
  MOTION_INTENSITY: 2
  VISUAL_DENSITY: 5
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
    states: [default, hover, focus-visible, active, disabled]
evidence:
  - id: direction
    kind: Recommended
    source: User brief
    claim: TODO
unknowns: []
exceptions: []
---
```

The remaining document is Markdown, not part of the YAML fence above:

## Design Read
State audience, primary task, vibe, retained constraints and why each dial has its value. Distinguish measured facts from design interpretation.

## Decisions and Overrides
Explain the main positive direction. List departures from defaults or supplied references with reasons; “No departures from the supplied brief” is valid. Respect existing stack and theme scope.

## Colors
Map each semantic role to its token, theme and usage. Extra brand accents and status/data colors need distinct roles. Record contrast targets and actual checks or pending implementation validation. Do not state that a CSS candidate is a rendered role without evidence.

## Typography
Explain hierarchy, sizes, line heights, language coverage, licensing and fallbacks. Use the frontmatter tokens as the canonical values; do not maintain contradictory copies.

## Spacing and Shape
Explain spacing tokens, grouping, radius and elevation. Supply additional named tokens when needed. Dense screens and editorial pages can use different scales.

## Layout
Describe the named rhythm's real regions, order and content rationale. Specify relevant viewport/resize behavior; mark unobserved breakpoints as unknown or recommendations. Related screens may share a stable structure.

## Components
For each scoped component, describe purpose, variants, applicable states and token usage. Address tables/forms/drawers where relevant. No universal requirement that every element has success/error/loading states.

## Motion
State purpose, timing direction and reduced-motion behavior, or intentional static behavior. Unknown site motion is not evidence of no animation.

## Imagery
Explain whether assets are needed. Identify provided assets and labelled slots; no quota. Do not create fake product evidence or testimonials.

## Accessibility
Specify text/non-text contrast targets, keyboard order, visible focus, non-color cues, target sizing and zoom/reflow. Scope any exceptions honestly. Separate specification requirements from tests on a future implementation.

## Honesty and Refusals
No invented metrics, customers, testimonials or measurements. Preserve file versions and source labels. Document any scenario-specific hard constraints and distinguish aesthetic preferences.

## Anti-Patterns
Choose 3–5 concrete, brief-specific mistakes and explain the correct alternative. Do not reproduce the entire reference catalog of warnings.

## Sources and Inference
Explain the evidence records, which choices they support, adaptations and unresolved unknowns. Every observed claim should be traceable to a source and locator. Catalog and CSS source observations have narrower scope than rendered captures.

## Pre-Ship Checklist
Copy all 12 checks from `references/preflight-checklist.md` and annotate actual outcomes. Do not tick unperformed implementation tests.
