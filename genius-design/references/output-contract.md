# Output Contract v1

A DESIGN.md starts with YAML frontmatter between `---` lines, followed by human-readable Markdown. Keep keys/headings in English; values and prose may use the user's language. YAML is parsed with PyYAML using duplicate-key rejection. Old unversioned files need an explicit, backed-up migration.

## Required Frontmatter

| Field | Type and requirement |
| --- | --- |
| schema_version | Integer exactly `1`; booleans are not integers here |
| name | Nonempty name |
| mode | `brand-template`, `reverse-engineer`, or `recommendation` |
| design_read | Nonempty summary of this specific brief |
| scope | Mapping with nonempty `page_kind`, `audience`, and distinct `themes` chosen from `light`, `dark` |
| dial_values | Mapping with DESIGN_VARIANCE, MOTION_INTENSITY, VISUAL_DENSITY, each integer 1–10 |
| layout | Nonempty `rhythm`, nonempty string list `regions`, and nonempty `rationale` |
| tokens | Semantic `colors`, `typography`, and `spacing` mappings described below |
| components | At least one named component; each has boolean `interactive` and a distinct nonempty `states` list |
| evidence | Nonempty list of records described below |
| unknowns | List, possibly empty, of `{subject, reason}` records |
| exceptions | List, possibly empty, of `{rule, reason}` records |

### Tokens

- `tokens.colors` has a map per declared theme and no undeclared theme. Each needs `background`, `surface`, `text`, `text-muted`, `accent`, `border`, `focus`. Additional semantic roles are allowed, including multiple brand accents, functional status colors and data colors.
- `tokens.typography` needs `font-body`, `font-heading`, `size-body`, `size-heading`, `line-height-body`, `line-height-heading`.
- `tokens.spacing` needs `small`, `medium`, `large`.
- Token names use lowercase kebab-case. Resolved values are nonempty strings or numbers, never booleans. CSS variables and modern color notation are acceptable; lint is not a complete CSS parser or contrast calculator.
- An unmeasured source token can be represented as `{value: null, status: unknown, reason: "not captured"}`. This produces a warning, not a fabricated value. List significant gaps in `unknowns` too. If a usable implementation value is proposed, label its supporting evidence Recommended.
- An `interactive: true` component needs `default` and `focus-visible` states. All components need `default`. Other states are chosen by applicability and explained in Components.

### Evidence

Every record has unique `id`, `kind` (`Observed`, `Inferred`, `Recommended`), `source` and `claim` strings.

Observed additionally requires:
- `method`: `computed-style`, `screenshot`, `supplied-guideline`, `css-source`, or `catalog`.
- `locator`: selector/property/viewport, screenshot region, guideline section, CSS line, or catalog record locator sufficient to locate the evidence.

`css-source` establishes a source declaration only. `catalog` establishes what a third-party snapshot says. Neither independently proves a rendered semantic role. Explain these limits in Sources and Inference. Inferred claims identify their basis; Recommended claims identify the brief or requirement motivating them.

A reverse-engineering document needs at least one Observed record or explicit unknown records explaining why no observation was available. Structural validity does not certify requested fidelity; insufficient evidence may still require draft status.

### Unfinished versus Unknown

Required active values cannot be empty, `TODO`, `TBD`, `FIXME`, `REPLACE_ME`, `#xxxxxx` or template markers like `<brand-name>`. Do not use these as unresolved implementation decisions.

Honest unknown records with a reason are valid. A labelled future content slot is also valid prose: for example, “Metric to confirm with the user; do not invent it.” Discussing prohibited colors, fonts, placeholders or punctuation is never itself a violation.

## Required Markdown Sections

Each exact level-two heading needs substantive content:

1. Design Read
2. Decisions and Overrides
3. Colors
4. Typography
5. Spacing and Shape
6. Layout
7. Components
8. Motion
9. Imagery
10. Accessibility
11. Honesty and Refusals
12. Anti-Patterns
13. Sources and Inference
14. Pre-Ship Checklist

Pre-Ship Checklist has exactly the 12 distinct named checkbox items from `references/preflight-checklist.md`. `[x]` records a specification review; `[ ]` records an unresolved check with an explanation. `N/A` needs a reason. The linter checks item identity/count and warns on unchecked items, but semantic review decides if an actual blocker remains.

## Validation Boundary

FAIL: malformed/duplicate-key YAML, unsupported schema, missing or wrongly typed required fields, illegal dial values, unresolved required markers, incomplete required tokens/components/evidence/sections/checklist.

WARN: explicit unknown tokens/evidence or unresolved checklist items. Review and disclose these; do not silently treat them as completed work.

Not mechanically certified: brand fidelity, correctness of evidence claims, taste, accessible implementation, actual contrast, responsive fit, font licenses, motion behavior. These require source review or testing the eventual UI. A hand-authored passing fixture tests the validator, not generation quality.
