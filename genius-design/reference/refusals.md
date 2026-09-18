# Absolute Refusals

## Absolute Refusals (Match and Rewrite -- ALL Workflows)

The following patterns must NEVER appear in any generated DESIGN.md or its derivative code. If you detect yourself about to produce one, refuse and rewrite with different structure.

### Color Refusals

- **AI-purple/blue glow gradients as default bg.** No automatic purple button glows, no random neon gradients. One accent color, saturation < 80%.
- **Cream/sand/beige/paper body bg.** The warm-neutral band (OKLCH L 0.84-0.97, C < 0.06, hue 40-100) is banned as default. Includes `#f5f1ea`, `#f7f5f1`, `#fbf8f1`, `#efeae0`, `#ece6db`, `#faf7f1`, `#e8dfcb`. "Warmth" is carried by accent + typography + imagery, not body bg.
- **Premium-consumer beige+brass+oxblood palette.** Banned hex families: `#f5f1ea`/bone bg, `#b08947`/brass accent, `#b6553a`/clay, `#9a2436`/oxblood, `#1a1714`/espresso text. Rotate to cold luxury, forest, cobalt+cream, or pure monochrome+pop.
- **Multiple accent colors.** One per project. A warm-grey site does not suddenly get a blue CTA in section 7.
- **Pure #000000 or #ffffff.** Always use tinted off-black / off-white.

### Typography Refusals

- **Inter as default.** Pick Geist, Outfit, Cabinet Grotesk, Satoshi, or a brand-appropriate alternative first. Inter is acceptable ONLY when the user explicitly asks for neutral/Linear-style or public-sector.
- **Fraunces and Instrument_Serif as defaults.** The two LLM-favorite display serifs -- banned as automatic choices.
- **Serif as default for any project.** Serif is only acceptable when the brand brief literally names a serif font, OR the aesthetic family is genuinely editorial/luxury/publication/heritage. Default sans-serif display always.
- **Mixed-family emphasis.** Do not inject a serif word into a sans headline. Use italic or bold of the SAME font.
- **Italic headers.** Headings and display type are roman (`font-style: normal`). Do not italicize one word inside a headline ("Built to *think*") and do not set all-italic display headings. Carry emphasis with weight, accent color, or a drawn underline. Italic is for body-copy emphasis only.
- **Gradient text** (`background-clip: text` + gradient). Use a single solid color. Emphasis via weight or size.

### Structure Refusals

- **Unnamed default landing rhythm.** Hero, then three equal feature cards, then logo wall, then CTA band, then footer -- unless that sequence is the explicitly named page rhythm. Every DESIGN.md must name one page rhythm / macrostructure and forbid the leftover default.
- **Same section order across pages.** Tokens may be shared. Two pages in one system must not reuse the same unnamed outline. If a second page is specified, give it a different rhythm or a documented reason it must match.
- **Hanging section heads.** Tag / number / eyebrow in a left column, heading in a right column (`01 THE TOUR` beside the title). When an eyebrow is used at all, stack it above the heading in the same column.
- **Specimen / editorial scaffolding as default.** Numbered left-margin labels, huge serif display, asymmetric type-only CTA -- only when the brief is actually editorial, foundry, or publication.

### Layout Refusals

- **Side-stripe borders.** `border-left`/`border-right` > 1px as a colored accent on cards, list items, or callouts. Rewrite with full borders, background tints, or nothing.
- **Identical card grids.** Same-sized cards with icon + heading + text repeated endlessly. At most one such grid per page, and only when it genuinely communicates information hierarchy.
- **Eyebrow on every section.** The small uppercase wide-tracking label above each heading. Default OFF. Maximum 1 eyebrow per 3 sections, and only when the content is genuinely ordinal.
- **Numbered section markers as default scaffolding.** `01 . About / 02 . Process / 03 . Pricing` above every section. Numbers only when the section IS a genuine sequence.
- **Hero overflowing viewport.** Headline > 2 lines, subtext > 20 words, CTA not visible without scroll -- all failures.
- **Hero top padding > pt-24 (about 6rem) at desktop.** More reads as a layout bug, not intentional space.
- **3 equal feature cards in a row.** The most generic AI layout pattern.
- **Zigzag alternation beyond 2 consecutive sections.** Max 2 image+text splits in a row.
- **Split-header as default** (left big headline + right small explainer). Stack vertically instead.
- **Navigation > 1 line at desktop, height > 80px.** Two-line nav is broken design.
- **Glassmorphism as default.** One frosted-glass element per page max.

### Content Refusals

- **Em dashes.** Use commas, colons, semicolons, periods, or parentheses instead of em-dashes (---/--).
- **AI marketing buzzwords.** The streamline / empower / supercharge / leverage / unleash / transform / seamless / world-class / enterprise-grade / next-generation / cutting-edge / game-changer / mission-critical family.
- **Aphoristic-cadence body copy.** "Serious statement, then punchy short negation" recurring across sections.
- **Duplicate CTA intent.** "Get in touch" + "Contact us" + "Let's talk" + "Start a project" on the same page -- pick ONE label.
- **Invented metrics and social proof.** No conversion percentages, user counts, speed-up multiples, testimonials, logo walls, or case-study counts unless the user supplied them. Use a labelled placeholder (`--` plus "metric to confirm") or drop the proof slot. A stat-led layout with no real stats is the wrong rhythm.
- **Two-line clickable labels.** Buttons, primary nav, footer links, breadcrumbs, and CTAs stay on one line. Shorten the copy; do not wrap the hit target.

### Component Refusals

- **Div-based fake screenshots.** A "hand-built product preview" rendered with `<div>` rectangles, fake task lists, or fake dashboards. Use real images, generated images, or explicit placeholder slots.
- **Re-drawn UI chrome.** Fake browser bars (URL pill + traffic-light dots), fake phone notches, fake IDE / code-window title bars. Wrap a real screenshot in a figure with at most a hairline border, or omit the frame.
- **Hand-rolled decorative SVGs** (custom illustrations, wavy doodles, feTurbulence paper grain). Ship no illustration rather than amateur SVG.
- **Fake-engineering-precise numbers** (92%, 4.1x, 48k without real data sources).
- **Text-only hero** (headline + gradient blob). Hero needs a real visual asset.
- **Empty cells in bento grids.** A bento grid has EXACTLY as many cells as content items. No filler tiles.
- **Incomplete interactive states.** Buttons, inputs, and other controls must specify default, hover, `:focus-visible`, `:active`, disabled, loading, error, and success. Hover-only affordances are not enough.

### Token Refusals

- **Raw color / font improvisation in implementation notes.** DESIGN.md tokens are the source of truth. Downstream UI must reference named tokens (`--color-accent`, `--font-display`), not new inline hex or a one-off `font-family`. If a value is missing, add a named token first.

