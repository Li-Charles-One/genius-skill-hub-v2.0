# DESIGN.md Template

Copy the document skeleton below into a staged candidate. Keep the full set of headings as guidance; do not delete optional H2s from this template. Replace active `TODO` fields and select applicable themes, components, regions and evidence. The template intentionally does not pass lint until filled. Prose may use the user's language; keep contract keys and section headings stable for validation. The complete working fixture is `evals/fixtures/valid-design.md`.

Required H2s: Design Read, Colors, Typography, Spacing and Shape, Layout, Components. The other H2s are optional unless applicable; omit them from a candidate when they have nothing to add. A core-only candidate with the six required headings can pass lint.

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
Optional unless there are departures or a direction worth stating. Explain the main positive direction. List departures from defaults or supplied references with reasons; “No departures from the supplied brief” is valid. Respect existing stack and theme scope.

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
Optional unless motion applies. A static page may omit this heading. If `MOTION_INTENSITY` is high, include it or accept a WARN. State purpose, timing direction and reduced-motion behavior, or intentional static behavior. Unknown site motion is not evidence of no animation.

## Imagery
Optional unless assets or labelled slots apply. Explain whether assets are needed. Identify provided assets and labelled slots; no quota. Do not create fake product evidence or testimonials.

## Accessibility
Optional as a heading; if omitted, put contrast targets in Colors and focus in Components. Lint WARNs. Specify text/non-text contrast targets, keyboard order, visible focus, non-color cues, target sizing and zoom/reflow. Scope any exceptions honestly. Separate specification requirements from tests on a future implementation.

## Honesty and Refusals
Optional unless there are refusals or honesty constraints to record. No invented metrics, customers, testimonials or measurements. Preserve file versions and source labels. Document any scenario-specific hard constraints and distinguish aesthetic preferences.

## Anti-Patterns
Optional; include when 3–5 brief-specific mistakes are worth stating. Choose 3–5 concrete, brief-specific mistakes and explain the correct alternative. Do not reproduce the entire reference catalog of warnings.

## Sources and Inference
Optional unless evidence provenance needs a readable walkthrough. Explain the evidence records, which choices they support, adaptations and unresolved unknowns. Every observed claim should be traceable to a source and locator. Catalog and CSS source observations have narrower scope than rendered captures.

## Pre-Ship Checklist
Optional. If included, copy all 12 checks from `references/preflight-checklist.md` and annotate actual outcomes. A core-only candidate without this heading can pass lint. Do not tick unperformed implementation tests.
