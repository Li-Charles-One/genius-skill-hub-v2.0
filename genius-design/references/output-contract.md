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

Required active values cannot be empty, `TODO`, `TBD`, `FIXME`, `REPLACE_ME`, `#xxxxxx` or hyphenated template markers like `<brand-name>`. Do not use these as unresolved implementation decisions.

YAML string fields may contain HTML such as `<button>`; those tags are allowed. Only hyphenated placeholders such as `<brand-name>` are unfinished markers.

Honest unknown records with a reason are valid. A labelled future content slot is also valid prose: for example, “Metric to confirm with the user; do not invent it.” Discussing prohibited colors, fonts, placeholders or punctuation is never itself a violation.

## Required Markdown Sections

Each of these exact level-two headings needs substantive content. This is the surface a downstream implementer actually reads: Design Read, color/type/spacing tokens, named layout rhythm, and component states.

1. Design Read
2. Colors
3. Typography
4. Spacing and Shape
5. Layout
6. Components

A core-only document with these six headings can pass lint. Missing, empty, or duplicate required sections FAIL. Duplicate level-two headings FAIL.

## Optional Markdown Sections

Include the following exact level-two headings when they apply. If present, each needs the same substantive content as a required section. Lint does not FAIL when they are absent.

- Decisions and Overrides
- Motion
- Imagery
- Accessibility
- Honesty and Refusals
- Anti-Patterns
- Sources and Inference
- Pre-Ship Checklist

Notes:

- If Accessibility is omitted, still place contrast targets in Colors and visible focus in Components. The linter WARNs; it does not FAIL.
- Omitting Motion is fine for a static page. If `MOTION_INTENSITY` is high, include a Motion section or accept a WARN.
- If Pre-Ship Checklist is present, it must contain exactly these 12 distinct named checkbox items. `[x]` is a specification review; `[ ]` needs a reason; `N/A` needs a reason. Lint checks identity/count and warns on unchecked items. An omitted checklist is not a FAIL.

```
- [ ] **Brief fidelity:** audience, page/screen type, language, stack and explicit user constraints are reflected.
- [ ] **Rule priority:** brand observations and requirements are preserved; departures and aesthetic preferences have reasons.
- [ ] **Evidence:** Observed/Inferred/Recommended claims have sources and context; unavailable evidence is explicit.
- [ ] **Dials:** all three values are 1–10 with scenario-specific rationales; no invented motion measurement.
- [ ] **Color and themes:** semantic roles are usable, scoped themes are complete, functional statuses are distinguished from brand accents.
- [ ] **Type and spacing:** named tokens, readable hierarchy, language fallbacks and responsive spacing are specified.
- [ ] **Rhythm:** actual regions and their content rationale are documented; repeated layouts are justified where useful.
- [ ] **Components:** relevant interactive, disabled, validation and async states are specified; irrelevant state families are not forced.
- [ ] **Accessibility:** contrast targets, keyboard/focus, zoom/reflow and non-color cues are specified; measured checks and pending UI checks are distinguished.
- [ ] **Motion and assets:** motion has a purpose and reduced-motion behavior; asset needs are justified with honest provenance or labelled slots.
- [ ] **Honesty and anti-patterns:** no fabricated proof or official-system claims; 3–5 context-specific failure modes are actionable.
- [ ] **Handoff:** contract lint passed; source gaps and implementation checks are disclosed; safe commit and backup paths are recorded in the delivery report.
```

## Validation Boundary

FAIL: malformed/duplicate-key YAML, unsupported schema, missing or wrongly typed required fields, illegal dial values, unresolved required markers, incomplete required tokens/components/evidence/required sections, duplicate level-two headings, or an incomplete Pre-Ship Checklist *if that section is present*. Missing optional sections are not FAILs. Do not treat all 14 headings as mandatory.

WARN: explicit unknown tokens/evidence, unresolved checklist items, omitted Accessibility, or high `MOTION_INTENSITY` without a Motion section. Review and disclose these; do not silently treat them as completed work.

Not mechanically certified: brand fidelity, correctness of evidence claims, taste, accessible implementation, actual contrast, responsive fit, font licenses, motion behavior. These require source review or testing the eventual UI. A hand-authored passing fixture tests the validator, not generation quality.
