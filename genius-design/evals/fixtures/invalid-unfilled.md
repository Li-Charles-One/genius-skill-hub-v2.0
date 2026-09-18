---
schema_version: 1
name: TODO
mode: recommendation
design_read: TODO
scope:
  page_kind: TODO
  audience: TODO
  themes: [light]
dial_values:
  DESIGN_VARIANCE: TODO
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
    states: [default, focus-visible]
evidence:
  - id: direction
    kind: Recommended
    source: User brief
    claim: TODO
unknowns: []
exceptions: []
---

## Design Read
State audience, primary task, vibe, retained constraints and why each dial has its value.

## Decisions and Overrides
Explain the main positive direction. List departures from defaults.

## Colors
Map each semantic role to its token, theme and usage.

## Typography
Explain hierarchy, sizes, line heights, language coverage, licensing and fallbacks.

## Spacing and Shape
Explain spacing tokens, grouping, radius and elevation.

## Layout
Describe the named rhythm's real regions, order and content rationale.

## Components
For each scoped component, describe purpose, variants, applicable states and token usage.

## Motion
State purpose, timing direction and reduced-motion behavior.

## Imagery
Explain whether assets are needed. Identify provided assets and labelled slots.

## Accessibility
Specify text/non-text contrast targets, keyboard order and visible focus.

## Honesty and Refusals
No invented metrics, customers, testimonials or measurements.

## Anti-Patterns
Choose 3–5 concrete, brief-specific mistakes and explain the correct alternative.

## Sources and Inference
Explain the evidence records, which choices they support, and unresolved unknowns.

## Pre-Ship Checklist
Copy all 12 checks from the preflight list and annotate actual outcomes.
