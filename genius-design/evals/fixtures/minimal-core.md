---
schema_version: 1
name: Minimal Core Fixture
mode: recommendation
design_read: "A compact recommendation for a small studio landing page: light paper, one accent, and a single primary action."
scope:
  page_kind: marketing landing page
  audience: First-time visitors comparing a small studio's offer
  themes: [light]
dial_values:
  DESIGN_VARIANCE: 3
  MOTION_INTENSITY: 2
  VISUAL_DENSITY: 5
layout:
  rhythm: single-column-offer
  regions:
    - masthead
    - offer
    - action
  rationale: "Keep one column so the offer, proof line, and primary action stay in a single reading path."
tokens:
  colors:
    light:
      background: "#f7f5f1"
      surface: "#ffffff"
      text: "#1f1c19"
      text-muted: "#6a645c"
      accent: "#c45c26"
      border: "#e4ddd3"
      focus: "#c45c26"
  typography:
    font-body: "Source Serif 4, Georgia, serif"
    font-heading: "Fraunces, Georgia, serif"
    size-body: 18px
    size-heading: 40px
    line-height-body: 1.5
    line-height-heading: 1.15
  spacing:
    small: 8px
    medium: 16px
    large: 32px
components:
  primary-button:
    interactive: true
    states: [default, hover, focus-visible, active, disabled]
evidence:
  - id: brief-quiet-canvas
    kind: Recommended
    source: User brief
    claim: "Use a quiet light canvas and one warm accent instead of a dense product dashboard."
unknowns: []
exceptions: []
---

## Design Read

This is a recommendation for a small studio landing page aimed at first-time visitors, not a reverse-engineered live site. The canvas stays light, variance is modest, motion stays quiet, and density is medium so the offer can be read in one pass.

## Colors

Light theme only. Background is warm paper, surface is white for the offer band, text and muted text keep reading contrast, and the single accent is reserved for the primary action and focus ring. Border stays pale so cards do not compete with type.

## Typography

Headings use a literary serif with Georgia as fallback. Body copy stays at a comfortable reading size with open line-height so a short offer paragraph remains readable. Do not introduce a second display face or a default UI sans for the masthead.

## Spacing and Shape

Small gaps handle inline rules, medium grouping holds a title with its sentence, and large spacing separates masthead, offer, and action. Corners stay tight. Elevation is a 1px border, not a drop shadow, so the page remains paper-quiet.

## Layout

Rhythm `single-column-offer` stacks masthead, offer, and action in that order. The masthead names the studio, the offer states the product in one paragraph, and the action holds the only button. Do not invent a sidebar or a three-up icon row.

## Components

`primary-button` is the only interactive control: default uses the accent fill, hover darkens slightly, focus-visible shows a 2px accent ring with a paper offset, active inks darker, and disabled drops to muted text on border. No loading family is specified.
