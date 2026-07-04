---
name: genius-design
description: "Generate production-grade DESIGN.md brand design systems with deep anti-slop rules. Three workflows: (A) pick from 73 brand templates, (B) reverse-engineer a live website, or (C) let the agent infer a design direction from your product type. Every DESIGN.md includes: brief inference + three-dial tuning (VARIANCE/MOTION/DENSITY), complete token definitions with semantic roles and constraints, brand-category-specific anti-pattern warnings, absolute refusal rules, and a 12-item pre-ship checklist. Trigger keywords: 逆向, 品牌, UI设计, 设计规范, DESIGN.md, reverse engineer, brand, design system, 风格."
license: Apache-2.0
metadata:
  version: "2.0.0"
  hermes:
    tags: [design-system, brand, DESIGN.md, anti-slop, frontend, UI, landing-page, template, reverse-engineer]
    related_skills: [taste-skill, impeccable]
---

# Genius Design — Deep Brand Design Systems for AI

Produce a rich, anti-slop DESIGN.md that an AI agent can read and follow without producing generic output. Every DESIGN.md includes: brief inference + three-dial tuning (VARIANCE / MOTION / DENSITY), complete token definitions with semantic roles and constraints, brand-category-specific anti-pattern warnings, absolute refusal rules, and a 12-item pre-ship checklist.

Before any workflow, run the **Brief Inference pre-step**. Then route to the matching workflow.

---

## First: Brief Inference (ALL workflows -- run this before anything else)

### 0.A Read the Room

Before picking a brand, fetching a site, or recommending a direction, read the user's signals:

1. **Page kind** -- landing (SaaS / consumer / agency / event), portfolio (dev / designer / creative studio), dashboard / tool, documentation, redesign (preserve vs overhaul), editorial / blog, e-commerce.
2. **Vibe words** the user used -- "minimalist", "calm", "Linear-style", "Awwwards", "brutalist", "premium consumer", "Apple-y", "playful", "serious B2B", "editorial", "agency-y", "glassy", "dark tech".
3. **Reference signals** -- URLs they linked, screenshots they pasted, products they named, brands they're competing with.
4. **Audience** -- B2B procurement panel vs. design-conscious consumer vs. recruiter scanning a portfolio. The audience picks the aesthetic, not your taste.
5. **Brand assets that already exist** -- logo, color, type, photography. For redesigns, these are starting material, not optional input.
6. **Quiet constraints** -- accessibility-first audiences, public-sector, regulated industries, trust-first commerce, kids' products. These constraints OVERRIDE aesthetic preference.

### 0.B Output a "Design Read" Before Any Action

Before generating anything, state in one line: **"Reading this as: <page kind> for <audience>, with a <vibe> language, leaning toward <design system or aesthetic family>."**

Example reads:
- *"Reading this as: B2B SaaS landing for technical buyers, with a Linear-style minimalist language, leaning toward Tailwind utilities + Geist + restrained motion."*
- *"Reading this as: solo designer portfolio for hiring managers, with an editorial / kinetic-type language, leaning toward native CSS + scroll-driven animation + custom typography."*
- *"Reading this as: redesign of a public-sector service site, with a trust-first language, leaning toward GOV.UK Frontend or USWDS."*

### 0.C If the Brief Is Ambiguous

Ask exactly **one** clarifying question -- never a multi-question dump -- and only when the design read genuinely diverges. Example: *"Should this feel closer to Linear-clean or Awwwards-experimental?"*

If you can confidently infer from context, **do not ask**. Just declare the design read and proceed.

### 0.D Ask the User Which Path

After declaring the Design Read, check first: **if the user has already provided a URL in their request, skip this question and go straight to Workflow B.**

Otherwise ask:

> Choose your path:
> - **A. Brand template** -- pick from 73 brands (Stripe, Apple, Linear, Vercel...)
> - **B. Reverse-engineer** -- give me a URL, I analyze its design and generate DESIGN.md
> - **C. AI recommendation** -- tell me your product type (e.g. "pet hospital management system"), I recommend a design direction

Route to the matching workflow below.

---

## The Three-Dial System (Integrated Into All Workflows)

Every DESIGN.md must set three dial values. These gate every layout, motion, density, and color decision downstream.

| Dial | Range | Meaning |
|---|---|---|
| `DESIGN_VARIANCE` | 1-10 | 1=Perfect Symmetry, 10=Artsy Chaos |
| `MOTION_INTENSITY` | 1-10 | 1=Static, 10=Cinematic/Physics |
| `VISUAL_DENSITY` | 1-10 | 1=Art Gallery/Airy, 10=Cockpit/Packed Data |

**Baseline: 7 / 6 / 4** (landing page default). Override based on the brief.

### Dial Inference Table

| Signal | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| "minimalist / clean / calm / editorial / Linear-style" | 5-6 | 3-4 | 2-3 |
| "premium consumer / Apple-y / luxury / brand" | 7-8 | 5-7 | 3-4 |
| "playful / wild / Dribbble / Awwwards / experimental / agency" | 9-10 | 8-10 | 3-4 |
| "landing page / portfolio / marketing site (default)" | 7-9 | 6-8 | 3-5 |
| "trust-first / public-sector / regulated / accessibility-critical" | 3-4 | 2-3 | 4-5 |
| "developer tool / SaaS / dashboard" | 5-6 | 4-5 | 4-6 |
| "redesign - preserve" | match existing | +1 | match |
| "redesign - overhaul" | +2 | +2 | match |

### How Dial Values Drive Output

Record these as the DESIGN.md's `dial_values` in the YAML frontmatter. Cross-reference them in every section:

- `VARIANCE` gates layout decisions: centered hero forbidden when >4, asymmetric layouts required when >=8, split-screen and scroll-pinned structures when >=9.
- `MOTION` gates animation depth: hover-only when <=3, scroll-triggered when >=6, magnetic/spring physics when >=9. Reduced-motion policy mandatory when >3.
- `DENSITY` gates whitespace and information packing: section gap py-32+ when <=3, py-16 when >=7. Card containers banned when >=7. Data metrics breathe in plain layout.

---

## Design System Honesty Map

Before generating tokens, decide: real design system, or aesthetic direction?

### When a Real Design System Applies (Use Official Packages)

| Brief reads as... | Reach for (official package) | Why |
|---|---|---|
| Microsoft / enterprise SaaS / dashboards | `@fluentui/react-components` | Official Fluent UI, accessibility done |
| Google-ish UI, Material-flavored product | `@material/web` + Material 3 tokens | Official, theme-able |
| IBM-style B2B / enterprise analytics | `@carbon/react` + `@carbon/styles` | Mature data-density patterns |
| Shopify app surfaces | `polaris.js` / Polaris React | Required for Shopify admin UI |
| Atlassian / Jira-style product | `@atlaskit/*` | Official Atlassian DS |
| GitHub-style devtool / community page | `@primer/css` or `@primer/react-brand` | Official Primer |
| Public-sector UK service | `govuk-frontend` | Legally expected |
| US public-sector / trust-first | `uswds` | Same |
| Modern accessible React foundation | `@radix-ui/themes` | Primitives + polished theme |
| Modern SaaS with full ownership | shadcn/ui | Owner code, easy to customise |
| Tailwind-based modern SaaS / AI marketing | Tailwind v4 utilities + `dark:` variant | Default for indie + small teams |

**Honesty rule:** if the brief reads as one of the systems above, install and use the **official** package. Do not recreate its CSS by hand. Do not import a system's tokens but then override 90% of them. **One system per project** -- do not mix Fluent React with Carbon in the same tree.

### When the Brief Is an Aesthetic, Not a System

For these directions, there is **no single official package**. Build with native CSS + Tailwind + a maintained component library. Be honest about what is borrowed inspiration vs. official material.

| Aesthetic | Honest implementation |
|---|---|
| Glassmorphism / "frosted glass" | `backdrop-filter`, layered borders, highlight overlays. Solid-fill fallback for `prefers-reduced-transparency`. |
| Bento (Apple-style tile grids) | CSS Grid with mixed cell sizes. No single library owns this. |
| Brutalism | Native CSS, monospace, raw borders. No library. |
| Editorial / magazine | Serif type, asymmetric grid, generous whitespace. No library. |
| Dark tech / hacker | Mono + accent neon, terminal motifs. No library. |
| Aurora / mesh gradients | SVG or layered radial gradients. No library. |
| Kinetic typography | Native CSS animations, scroll-driven animations, GSAP for hijacks. No library. |
| Apple Liquid Glass | Apple documents for Apple platforms only. **No official `liquid-glass.css`**. Web approximations use `backdrop-filter` + layered borders + highlights. Label as approximation. |

---

## Code Stack Conventions (For Implementation)

When the DESIGN.md is used to generate code (its intended purpose), the following defaults apply unless the Design System Map overrides them:

- **Framework:** React or Next.js. Default to Server Components (RSC). Wrap providers in `"use client"` components. Interactive components (Motion, scroll listeners, pointer physics) MUST be isolated leaves with `'use client'`.
- **Styling:** Tailwind v4 (default). v3 only if the existing project demands it. For v4: use `@tailwindcss/postcss` or the Vite plugin, NOT the `tailwindcss` plugin in `postcss.config.js`.
- **Animation:** Motion (`import { motion } from "motion/react"`). `framer-motion` still works as legacy alias -- prefer `motion/react` in new code.
- **Fonts:** Always `next/font` (Next.js) or self-host with `@font-face` + `font-display: swap`. Never link Google Fonts via `<link>` in production.
- **Icons (priority order):** `@phosphor-icons/react`, `hugeicons-react`, `@radix-ui/react-icons`, `@tabler/icons-react`. Discouraged: `lucide-react` (acceptable only when user explicitly asks or project depends on it). One family per project.
- **State:** Local `useState`/`useReducer` for isolated UI. Global state (Zustand, Jotai, React context) only for deep prop-drilling. **Never** `useState` for continuous values (mouse position, scroll progress) -- use Motion's `useMotionValue`/`useTransform`/`useScroll`.
- **Dependency Verification (mandatory):** Before importing any 3rd-party library, check `package.json`. If missing, output the install command first. Never assume a library exists.

---

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

---

## Shared Enrichment Pipeline (Steps A3-A5 / B4-B6 / C4-C6)

**Preflight check (run before any enrichment step):** Verify all three reference files exist:
- `reference/design-template.md`
- `reference/anti-patterns.md`
- `reference/preflight-checklist.md`

If any file is missing, stop and report which file(s) are absent. Do not attempt enrichment with incomplete references — the output will be structurally incomplete.

After the base DESIGN.md exists (fetched, extracted, or generated), run this shared pipeline.

### Enrichment Step 1: Expand Every Section

Read `reference/design-template.md`. For each section of the base DESIGN.md, add the following depth:

- **Colors**: Add semantic roles for every hex value (never "blue: #0064E0" -- always "Primary CTA (#0064E0): all purchase buttons, signup CTAs, active nav links"). Add forbidden hex families from the Absolute Refusals above. Document the neutral system choice (cool-zinc / warm-stone / true-slate) and chroma tint (0.005-0.015 toward brand hue). Enforce one-accent constraint.
- **Typography**: Add scale ratio (>=1.25 between steps), hero clamp ceiling (max 6rem = ~96px), tracking floor (>= -0.04em), banned defaults (Inter, Fraunces, Instrument_Serif), serif discipline rules, italic descender clearance (leading-[1.1] + pb-1 for y/g/j/p/q in display italic). Cap font families at 3. Set body max-width at 65ch.
- **Shape & Elevation**: Document corner-radius scale (one system per page: all-sharp / all-soft-12-16px / all-pill). Shadow tint rule (tint to background hue, never pure black). Card usage constraint: cards only when elevation communicates real hierarchy; banned entirely when VISUAL_DENSITY > 7. Forbidden: border-radius > 16px on cards/sections, ghost-card pattern (1px border + soft wide shadow on the same element).
- **Spacing**: Document base unit (8px default, 4px dense, 10px editorial). Hero top padding cap: pt-24 max at desktop. Section gap defaults (py-24 to py-32). Card padding range (p-6 to p-8).
- **Layout**: Document max-width container (max-w-[1400px] or max-w-7xl), breakpoints (sm 640, md 768, lg 1024, xl 1280, 2xl 1536). Viewport stability: min-h-[100dvh] never h-screen. Grid over flex-math: CSS Grid for 2D, Flexbox for 1D, never complex flexbox percentage math. Hero constraints: headline <=2 lines, subtext <=20 words/<=4 lines, max 4 text elements (eyebrow OR brand strip + headline + subtext + CTAs). Forbidden layout patterns: centered hero when VARIANCE > 4, 3 equal cards, zigzag beyond 2 consecutive, eyebrow on >1/3 of sections, split-header as default.
- **Components**: For buttons: 44-48px height, verb+object label <=3 words fits one line, WCAG AA contrast check, active tactile feedback (scale-[0.98]), no duplicate CTA intent. For inputs: label above input, never placeholder-as-label, WCAG AA on all parts. For cards: omit in favor of spacing; bento cells need real visual variation in 2-3 cells. Logo wall: under hero never inside, logos only no category labels, SVG from Simple Icons CDN. Navigation: 64-72px height cap 80px, single line at desktop.
- **Motion**: Document intensity (from dial), exponential ease-out curve (cubic-bezier(0.16, 1, 0.3, 1)), no bounce/elastic. Reduced-motion policy mandatory when intensity > 3. Animate only transform + opacity (never top/left/width/height). No window.addEventListener('scroll') -- use Motion useScroll / ScrollTrigger / IntersectionObserver. Max one marquee per page. Every animation must have a one-sentence purpose.
- **Imagery**: Priority: gen-tool -> Picsum seed (https://picsum.photos/seed/{descriptive-seed}/{w}/{h}) -> explicit placeholder slots. Minimum 2-3 real images even for minimalist sites. Logo source: Simple Icons CDN (https://cdn.simpleicons.org/{slug}/ffffff). Banned: div-based fake screenshots, hand-rolled decorative SVGs, text+gradient blob as hero, fake-engineering-precise numbers.
- **Dark Mode**: Required. Strategy: Tailwind `dark:` variant or CSS variables. One theme per page, no section-level inversion. No pure black, no pure white.
- **Theme Lock**: One accent across all sections. One corner-radius system. One palette (don't fluctuate between warm and cool grays). One theme per page.

### Enrichment Step 2: Inject Anti-Patterns

Read `reference/anti-patterns.md`. Match the brand to its category (a brand may belong to multiple categories -- e.g., Linear = Developer Tools + Dark Mode + Minimalist). Merge the warnings and pick the 3-5 most relevant. Inject as:

```markdown
## Anti-Patterns for This Brand

When using this DESIGN.md, the most common AI mistakes are:
1. **<title>**: <what the AI does wrong> -> <what to do instead>.
...
```

### Enrichment Step 3: Append Pre-Ship Checklist

Read `reference/preflight-checklist.md`. Append the complete 12-item checklist. If any item cannot be ticked for the current DESIGN.md, fix it before delivering.

### Enrichment Step 4: Run the AI Slop Test

Before delivering, run the two-altitude reflex check:

**First-order:** If someone could guess the theme + palette from the category alone (e.g., "fintech = blue + white, AI = purple glow, premium consumer = beige + brass"), rework the color strategy until the answer isn't obvious from the domain.

**Second-order:** If someone could guess the aesthetic family from category-plus-anti-references ("AI workflow tool that's not SaaS-cream -> editorial-typographic", "fintech that's not navy-and-gold -> terminal-native dark mode"), rework until both answers are not obvious.

If either check fails, redo the color selection or aesthetic direction. This is not optional.

### Enrichment Step 5: Deliver

Tell the user:
- The key design decisions (primary color, font stack, vibe, dial values)
- Where the file was saved (`./DESIGN.md`)
- If any values were inferred (mark them clearly)
- Any decisions the user may want to override

---

## Workflow A: Brand Template (73 brands => deep DESIGN.md)

### Step A1: User Picks a Brand

Show the Selection Guide at the bottom of this file to help the user choose. Or they can name any brand from the catalog. The Brief Inference (Section 0) already produced a Design Read -- use it to recommend 2-3 best-fit brands before asking the user to pick.

### Step A2: Fetch the Base DESIGN.md

**Overwrite check:** If `./DESIGN.md` already exists, notify the user before proceeding. Either ask for confirmation to overwrite, or automatically back up the existing file as `./DESIGN.md.bak` and note that a backup was created.

```bash
# Primary: your fork
curl -sL "https://raw.githubusercontent.com/Li-Charles-One/awesome-design-md/main/design-md/<slug>/DESIGN.md" -o ./DESIGN.md

# Fallback: upstream
curl -sL "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/<slug>/DESIGN.md" -o ./DESIGN.md
```

Alternatively, use the bundled script:
```bash
python scripts/fetch_design_md.py <brand> ./DESIGN.md
```

### Step A3: Infer Customizations

After fetching the base DESIGN.md, read it and infer:

1. **Dial values**: What VARIANCE / MOTION / DENSITY does this brand's aesthetic suggest? Use the Dial Inference Table above. Record these in the YAML frontmatter as `dial_values:`.
2. **Design system mapping**: Does this brand correspond to a real design system (Honesty Map above)? If so, note it. If not, note the honest implementation approach.
3. **Stack convention**: Note any overrides to the default code stack (rare for these brands, but possible).

### Step A4: Run Shared Enrichment Pipeline

Execute all five Enrichment Steps from the Shared Pipeline above.

---

## Workflow B: Reverse-Engineer a Website

### Step B1: Fetch the Page

Use `web_fetch` to grab the rendered page content. Extract HTML/CSS signals from the response. If a Firecrawl CLI is available, use it for richer extraction:

**B1-alt (Firecrawl if available):**
```bash
firecrawl scrape "<url>" --format rawHtml,branding,screenshot --only-main-content --wait-for 3000 -o .firecrawl/design-data.json --json --pretty
```

After scraping, spot-check with quick greps:
```bash
# Dominant font (Linux/GNU grep)
grep -oP "font-family:\s*[^;]+" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -5
# macOS (BSD grep, no -P): use -E instead
grep -oE "font-family:[^;]+" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -5

# Border-radius patterns (Linux)
grep -oP "border-radius:\s*\d+px" .firecrawl/design-data.json | sort | uniq -c | sort -rn
# macOS
grep -oE "border-radius:[[:space:]]*[0-9]+px" .firecrawl/design-data.json | sort | uniq -c | sort -rn

# All hex colors (Linux)
grep -oP "#[0-9a-fA-F]{3,8}" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -15
# macOS
grep -oE "#[0-9a-fA-F]{3,8}" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -15
```

If the page requires login or interaction:
```bash
firecrawl scrape "<url>"
firecrawl interact --prompt "Click the login button, then fill credentials"
firecrawl scrape "<url>" --format rawHtml,branding,screenshot --only-main-content --wait-for 3000 -o .firecrawl/design-data.json --json --pretty
```

### Step B2: Extract Design Tokens

Work through each dimension systematically. For every value, assign a **semantic role** -- never just "blue: #0064E0" but "Primary CTA (#0064E0) -- all purchase buttons, signup CTAs, active nav links."

**Colors**: Map recurring hex values to semantic roles. Count occurrences to separate signal from noise. Identify the color system: monochrome+accent, multi-accent, gradient-driven.

**Typography**: Identify dominant font family, build the size scale, note weight patterns, measure line-height. Detect if the site uses a proprietary font and note the CDN substitution.

**Spacing**: Extract section gaps, card padding, button padding. Detect grid base unit (8px, 10px, 12px).

**Components**: For buttons, cards, inputs, nav -- extract border-radius, min-height, padding, shadow formulas, focus ring styles. Note variants (solid vs outline vs ghost).

**Shapes & Elevation**: Map the 2-3 most common border-radius values to sm/md/lg. Count distinct box-shadow values to build an elevation scale.

**Dial inference**: Based on the extracted patterns, infer VARIANCE (layout symmetry vs asymmetry), MOTION (presence and intensity of animations), and DENSITY (information per viewport, section padding). Note: extraction can't always get MOTION -- infer from the brand category when uncertain.

**Design system detection**: Does the site use a recognizable design system (Material, Fluent, Carbon, Primer, GOV.UK)? If yes, note it for the Honesty Map.

### Step B3: Generate the Deep DESIGN.md

**Overwrite check:** If `./DESIGN.md` already exists, notify the user and back up as `./DESIGN.md.bak` before writing.

Use `reference/design-template.md` as the structure. Fill every section from the extracted tokens. Where extraction can't determine a value, apply the defaults from the template and mark with `<!-- inferred -->`.

### Step B4: Run Shared Enrichment Pipeline

Execute all five Enrichment Steps from the Shared Pipeline above.

### Limitations

- `web_fetch` extracts rendered text -- CSS values may be partial. Firecrawl gives richer data.
- Interactive states (hover, focus, active) are inferred from class name patterns, not directly observed.
- For highly dynamic SPAs, increase `--wait-for` or use `firecrawl interact`.
- The dial values for MOTION are the hardest to extract -- infer from the brand category when the site doesn't signal clearly.

---

## Workflow C: AI Recommendation (No Brand Reference)

### Step C1: Understand the Product

If not already captured during Brief Inference, ask for: industry, product type, target audience. Examples:
- Medical SaaS platform, admin backend for doctors
- Sports brand e-commerce, selling running shoes and fitness gear
- Children's education app, targeting parents

### Step C2: Reason Through the Design Direction

Based on the product description and Brief Inference, systematically reason:

1. **Register**: Is this brand (design IS the product -- landing page, marketing) or product (design SERVES the product -- dashboard, tool, app)?
2. **Vibe**: What aesthetic family fits? Pick from: minimalist/Linear-style, premium-consumer/Apple-y, playful/creative, editorial/luxury, dark-tech, trust-first/public-sector, brutalist/industrial, soft/warm-consumer.
3. **Dial values**: Set DESIGN_VARIANCE, MOTION_INTENSITY, VISUAL_DENSITY using the Dial Inference Table. Justify each value in one sentence tied to the product audience.
4. **Design system**: Does the product map to a real design system (Honesty Map)? If the brief reads "enterprise B2B dashboard," reach for Carbon or Fluent. If "modern SaaS," shadcn/ui or Tailwind v4. If "creative agency landing page," native CSS + aesthetic direction.
5. **Closest brand match**: Which brand(s) from the 73-brand catalog are closest in spirit? Name 2-3 with one-line justifications.

### Step C3: Generate the DESIGN.md

**Overwrite check:** If `./DESIGN.md` already exists, notify the user and back up as `./DESIGN.md.bak` before writing.

Two paths, based on closeness to existing brands:

- **Path C3a (close match exists)**: Fetch the closest brand's DESIGN.md via Workflow A Step A2, then adjust the token values to match the product's specific needs. Change the brand name, adjust accents, swap fonts if needed. Mark changed values with `<!-- adapted from <brand> -->`.

- **Path C3b (genuinely unique)**: Build a fresh DESIGN.md directly from `reference/design-template.md`. Fill every section with the recommended direction. Mark all values as `<!-- generated from product type -->`.

### Step C4: Run Shared Enrichment Pipeline

Execute all five Enrichment Steps from the Shared Pipeline above.

---

## Brand Catalog (73 brands)

### AI & LLM
Claude, Cohere, ElevenLabs, Minimax, Mistral AI, Ollama, OpenCode AI, Replicate, RunwayML, Together AI, VoltAgent, xAI

### Developer Tools
Cursor, Expo, Lovable, Raycast, Superhuman, Vercel, Warp

### Backend & DevOps
ClickHouse, Composio, HashiCorp, MongoDB, PostHog, Sanity, Sentry, Supabase

### Productivity & SaaS
Cal.com, Intercom, Linear, Mintlify, Notion, Resend, Slack, Zapier

### Design Tools
Airtable, Clay, Figma, Framer, Miro, Webflow

### Fintech
Binance, Coinbase, Kraken, Mastercard, Revolut, Stripe, Wise

### E-commerce
Airbnb, Meta, Nike, Shopify, Starbucks

### Media & Tech
Apple, Dell (1996), HP, IBM, NVIDIA, Pinterest, PlayStation, SpaceX, Spotify, The Verge, Uber, Vodafone, WIRED

### Automotive
BMW, BMW M, Bugatti, Ferrari, Lamborghini, Renault, Tesla

---

## Font Substitutions

Brand DESIGN.md files reference proprietary fonts. Use these CDN-available alternatives:

| Original Font | CDN Alternative | Character |
|:--|:--|:--|
| Geist | Geist (Google Fonts) | Geometric, compact |
| sohne-var (Stripe) | Source Sans 3 | Light, elegant |
| Airbnb Cereal | DM Sans | Rounded, friendly |
| Circular (Spotify) | DM Sans | Geometric, warm |
| figmaSans | Inter | Clean, humanist |

---

## Selection Guide

- **Developer tools / dashboards**: Linear, Vercel, Supabase, Raycast, Sentry
- **Documentation / content sites**: Mintlify, Notion, Sanity, MongoDB
- **Marketing / landing pages**: Stripe, Framer, Apple, SpaceX
- **Dark mode**: Linear, Cursor, ElevenLabs, Warp, Superhuman
- **Light / clean**: Vercel, Stripe, Notion, Cal.com
- **Playful / friendly**: PostHog, Figma, Lovable, Zapier, Miro
- **Premium / luxury**: Apple, BMW, Stripe, Superhuman, Revolut

---

## Fallback Strategy

Primary: fetch from Li-Charles-One/awesome-design-md. Fallback: VoltAgent/awesome-design-md. Once a DESIGN.md is placed in the project root, it has zero external dependencies -- it's a standalone Markdown file any AI agent can read.

---

## References

- **Google DESIGN.md spec**: https://stitch.withgoogle.com/docs/design-md/overview/
- **Fork (primary)**: https://github.com/Li-Charles-One/awesome-design-md
- **Upstream (fallback)**: https://github.com/VoltAgent/awesome-design-md
- **Online catalog**: https://getdesign.md
- **Anti-slop rules**: taste-skill by Leonxlnx (https://github.com/Leonxlnx/taste-skill)
- **Impeccable design language**: https://github.com/pbakaus/impeccable
