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
- **Gradient text** (`background-clip: text` + gradient). Use a single solid color. Emphasis via weight or size.

### Layout Refusals

- **Side-stripe borders.** `border-left`/`border-right` > 1px as a colored accent on cards, list items, or callouts. Rewrite with full borders, background tints, or nothing.
- **Identical card grids.** Same-sized cards with icon + heading + text repeated endlessly. At most one such grid per page, and only when it genuinely communicates information hierarchy.
- **Eyebrow on every section.** The small uppercase wide-tracking label above each heading. Maximum 1 eyebrow per 3 sections.
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

### Component Refusals

- **Div-based fake screenshots.** A "hand-built product preview" rendered with `<div>` rectangles, fake task lists, or fake dashboards. Use real images, generated images, or explicit placeholder slots.
- **Hand-rolled decorative SVGs** (custom illustrations, wavy doodles, feTurbulence paper grain). Ship no illustration rather than amateur SVG.
- **Fake-engineering-precise numbers** (92%, 4.1x, 48k without real data sources).
- **Text-only hero** (headline + gradient blob). Hero needs a real visual asset.
- **Empty cells in bento grids.** A bento grid has EXACTLY as many cells as content items. No filler tiles.

