---
schema_version: 1
name: Hearth Folio Seasonal Landing
mode: brand-template
design_read: "Seasonal landing page for Hearth Folio, a small literary press: cream paper field, wine and brass inks, Fraunces headings, and a centered title-page masthead for readers who subscribe to chapbooks."
scope:
  page_kind: marketing landing page
  audience: Readers who buy letterpress chapbooks and subscribe to a seasonal journal
  themes: [light]
dial_values:
  DESIGN_VARIANCE: 6
  MOTION_INTENSITY: 2
  VISUAL_DENSITY: 4
layout:
  rhythm: editorial-title-page
  regions:
    - centered-masthead
    - issue-contents
    - subscription-band
    - colophon
  rationale: "The page should read like a title page that opens into the issue, not like product chrome. A centered masthead carries the issue name; contents, subscribe, and colophon follow in one column."
tokens:
  colors:
    light:
      background: "#f5f1ea"
      surface: "#fbf8f1"
      text: "#23201c"
      text-muted: "#6b6459"
      accent: "#9a2436"
      accent-secondary: "#b08947"
      border: "#e8dfcb"
      focus: "#9a2436"
      success: "#3f6b4a"
  typography:
    font-body: "Source Serif 4, Georgia, serif"
    font-heading: "Fraunces, Source Serif 4, Georgia, serif"
    size-body: 20px
    size-heading: 56px
    line-height-body: 1.45
    line-height-heading: 1.12
  spacing:
    small: 8px
    medium: 16px
    large: 40px
components:
  subscribe-button:
    interactive: true
    states: [default, hover, focus-visible, active, disabled]
  issue-card:
    interactive: true
    states: [default, hover, focus-visible]
  masthead:
    interactive: false
    states: [default]
evidence:
  - id: brief-cream-paper
    kind: Recommended
    source: User brief
    claim: "Use a cream paper field with wine and brass inks rather than a cool-gray software palette."
  - id: brief-centered-masthead
    kind: Recommended
    source: User brief
    claim: "Keep the issue masthead centered like a title page, not a left-aligned dashboard header."
  - id: type-direction
    kind: Inferred
    source: User conversation
    claim: "Fraunces is the intended heading face because the brief named a literary display serif; Inter was rejected as a default sans."
unknowns:
  - subject: Masthead photograph
    reason: "No issue photography was supplied. Use a labelled slot; do not invent a photograph, author portrait, or press run statistic."
exceptions: []
---

## Design Read

This is a seasonal landing page for Hearth Folio readers who already care about chapbooks, not a conversion funnel for a generic SaaS audience. The vibe is letterpress and paper: cream field `#f5f1ea`, wine `#9a2436`, brass `#b08947`. DESIGN_VARIANCE is 6 because the brief asked for a distinctive title page rather than a safe product shell. MOTION_INTENSITY is 2 because the page is mostly static; any fade is decorative, not a measured site behavior. VISUAL_DENSITY is 4 so the masthead and issue title can breathe. These dials are brief interpretations, not captured motion metrics.

## Decisions and Overrides

The positive direction is an editorial title page: centered masthead, serif hierarchy, two brand inks, cream paper. Departures from generic landing defaults are intentional — no left-rail header, no Inter, no cool gray, no three-up icon row. The stack is static HTML and CSS with system serif fallbacks; do not introduce a design-system package or a dark theme. No departures from the supplied cream, dual-accent, and centered-masthead constraints.

## Colors

Light theme only. `background` `#f5f1ea` is the paper field; `surface` `#fbf8f1` is the subscription band and cards. `text` `#23201c` and `text-muted` `#6b6459` set reading contrast targets of 7:1 and 4.5:1 against paper; actual ratios are an implementation check, not a claim in this spec. Brand accents are two distinct roles: `accent` wine `#9a2436` for subscribe and issue number, `accent-secondary` brass `#b08947` for rules and colophon ornaments. `success` `#3f6b4a` is a functional status and must not replace wine. `border` `#e8dfcb` and `focus` wine `#9a2436` keep focus visible on cream. Do not treat these hex values as computed styles from a live site.

## Typography

Headings use Fraunces with Source Serif 4 and Georgia as fallbacks. Body copy uses Source Serif 4 at 20px / 1.45 so long issue descriptions stay readable. Display size is 56px / 1.12 for the masthead title only. Do not substitute Inter; the brief asked for a literary serif and Inter would flatten the title page into a software default. Latin-only coverage is specified; CJK is out of scope. Confirm the Fraunces SIL files before self-hosting; until then, Georgia is the safe fallback. Frontmatter tokens are canonical — do not keep a second size table in CSS comments.

## Spacing and Shape

`small` 8px is for inline gaps and brass rules. `medium` 16px groups a card title with its blurb. `large` 40px separates masthead, contents, and subscribe. Radius is 0 on the masthead and 4px on issue cards so paper edges stay quiet. Elevation is a 1px `#e8dfcb` border, not a drop shadow. The page is airy on purpose; do not compress it into a dense operations density.

## Layout

Rhythm `editorial-title-page` has four regions in this order: `centered-masthead` (issue name, season, wine rule), `issue-contents` (three titled entries, not feature cards), `subscription-band` (one cream surface with the subscribe button), `colophon` (press address and brass ornament). The masthead is centered at every viewport; body text stays in a single column around 36rem. Unobserved breakpoints are unknown; do not invent a tablet composition. Related issue pages may reuse this same structure.

## Components

`masthead` is not interactive; its only state is default, centered, with Fraunces and a wine rule. `issue-card` is a link to an issue essay: default, hover (brass underline), and focus-visible (wine outline). `subscribe-button` is the one true action: wine fill, cream label, hover darkens wine, focus-visible uses a 2px wine ring with a cream offset, active inks slightly darker, disabled drops to muted text on border. No loading or error state is specified because checkout is off-page. Do not force success/error/loading families onto the masthead.

## Motion

The page is intentionally quiet. A 180ms fade on the subscribe hover is optional and must disable under `prefers-reduced-motion`. There is no page-load choreography and no parallax. Unknown site motion from other Hearth Folio properties is not evidence that this landing page is static; this value is a brief recommendation.

## Imagery

No photography was supplied. The masthead may use a labelled slot — “Issue photography to come; do not invent a press floor photo.” Ornamental brass rules are CSS, not assets. Do not create fake author portraits, testimonials, or print-run photographs.

## Accessibility

Text on cream should meet 4.5:1 for body and 3:1 for large Fraunces titles; treat those as specification targets, not measured results. Keyboard order is masthead skip-link, contents links, subscribe, colophon. Focus-visible is a wine ring, never outline:none. Subscribe availability is also written as text, not wine color alone. Targets are at least 44px. Zoom to 200% reflows to a single column; that reflow is a future UI check.

## Honesty and Refusals

Do not invent subscriber counts, blurbs from named critics, or “letterpress since” dates. Do not claim Fraunces is licensed until the file is in the repo. Preserve this document’s versioned frontmatter; do not silently restyle an existing DESIGN.md. Cream, serif headings, two accents, and a centered masthead are brief requirements, not loopholes. Metric to confirm with the user; do not invent it.

## Anti-Patterns

1. Replacing Fraunces with Inter because serifs feel “old” — keep the named heading face.
2. Turning the title page into a hero with a stock library photo — use the labelled slot.
3. Using brass as a success state — brass is a brand accent; `success` is the functional green.
4. Left-aligning the masthead into product chrome — the brief asked for a centered title page.
5. Filling the contents region with three icon cards — list actual issue pieces.

## Sources and Inference

`brief-cream-paper` and `brief-centered-masthead` are Recommended from the user brief; they are not Observed computed styles. `type-direction` is Inferred from the conversation that named a literary serif and rejected Inter. No screenshot, catalog, or CSS source was used. The unknown masthead photograph is listed in `unknowns` rather than filled with a fabricated image. Catalog and CSS observations are out of scope for this brand-template document.

## Pre-Ship Checklist

- [x] **Brief fidelity:** Seasonal landing page for Hearth Folio readers in English; static HTML/CSS; cream paper, two inks, and a centered masthead are retained.
- [x] **Rule priority:** Brief constraints outrank generic landing defaults; Inter, dark mode, and product chrome are rejected with reasons.
- [x] **Evidence:** Three Recommended/Inferred records cite the brief or conversation; no observation was claimed; photography is an explicit unknown.
- [x] **Dials:** Variance 6, motion 2, density 4, each with a scenario rationale; motion is not a measured capture.
- [x] **Color and themes:** Light theme only; wine and brass are brand accents; success is a distinct functional role.
- [x] **Type and spacing:** Fraunces/Source Serif 4 tokens, 20px body, 8/16/40 spacing, Georgia fallback named.
- [x] **Rhythm:** editorial-title-page lists centered-masthead, issue-contents, subscription-band, and colophon with content reasons.
- [x] **Components:** Subscribe and issue-card include default and focus-visible; masthead is non-interactive default only.
- [x] **Accessibility:** Contrast targets, focus ring, non-color cues, 44px targets, and 200% reflow are specified as spec checks, not UI test results.
- [x] **Motion and assets:** Quiet optional hover fade with reduced-motion off; photography is a labelled slot.
- [x] **Honesty and anti-patterns:** No fabricated proof; five brief-specific failure modes with corrections.
- [x] **Handoff:** Contract lint is the mechanical gate for this fixture; source gaps stay in unknowns; implementation contrast checks remain pending.
