# Deep DESIGN.md Template

The template below produces a rich DESIGN.md that prevents AI from defaulting to slop. Fill every section; skip fields only when the brand truly doesn't have an answer.

## YAML Frontmatter

```yaml
version: alpha
name: <brand-name>-design-system
description: <2-3 sentences: brand identity + visual atmosphere + target audience>

# ── COLORS ──────────────────────────────────────────
colors:
  primary:
    hex: "#xxxxxx"
    role: "CTA buttons, active nav, focus rings, links"
    saturation: "< 80% — never oversaturated"
    contrast_on_white: "≥ 4.5:1"
  accent:
    hex: "#xxxxxx"
    role: "hover states, secondary highlights, icons"
    rule: "ONE accent per project. Never two."
  background:
    default: "#xxxxxx"
    elevated: "#xxxxxx"
  ink:
    default: "#xxxxxx"
    muted: "#xxxxxx"
  neutral_system:
    base: "cool-tinted zinc | warm-tinted stone | true-neutral slate"
    chroma_tint: "0.005-0.015 toward brand hue — never default to warm"
  forbidden:
    - "AI purple/blue glow gradients as default bg"
    - "cream/sand/beige/paper body bg (OKLCH L 0.84-0.97, C < 0.06, hue 40-100)"
    - "#f5f1ea, #f7f5f1, #fbf8f1, #efeae0, #ece6db, #faf7f1, #e8dfcb"
    - "brass/clay/oxblood/ochre accent defaults for premium-consumer"
    - "multiple accent colors — one per project"
    - "pure #000000 or pure #ffffff — use tinted off-black / off-white"

# ── TYPOGRAPHY ───────────────────────────────────────
typography:
  display:
    font: "<name>"
    weight: 700
    tracking: "-0.02em to -0.04em (floor: -0.04em)"
    ceiling: "clamp(2.5rem, 5vw, 6rem) — never above 6rem"
    line_height: "1.0-1.1"
  heading:
    font: "<name, often same as display>"
    scale_ratio: 1.25
    tracking: "-0.01em to -0.02em"
    line_height: "1.1-1.2"
    wrap: "text-wrap: balance"
  body:
    font: "<name>"
    weight: 400
    size: "1rem / 16px"
    line_height: "1.5-1.6"
    max_width: "65ch — never wider"
    wrap: "text-wrap: pretty"
  mono:
    font: "<name, for code/data>"
    use: "numbers, code, data labels"
  banned_defaults:
    - "Inter (allowed only when user explicitly asks for neutral/Linear-style)"
    - "Fraunces — LLM-favorite display serif, banned"
    - "Instrument_Serif — same"
  serif_discipline:
    allowed_only_when: "brand brief names a serif OR genuinely editorial/luxury/heritage"
    default_choice: "sans-serif display (Geist Display, Söhne Breit, Cabinet Grotesk Display)"
    emphasis_rule: "italic or bold of SAME font. Never mixed-family emphasis."
  italic_descender_rule: "leading-[1.1] min + pb-1 reserve for y/g/j/p/q in display italic"
  no_all_caps_body: true

# ── SHAPE & ELEVATION ───────────────────────────────
shape:
  strategy: "all-sharp | all-soft (12-16px) | all-pill (interactive only)"
  rule: "ONE corner-radius scale per page. Mixed only with documented rule."
  button_radius: "full-pill or 8-12px"
  card_radius: "12-16px max"
  input_radius: "8-12px"
  forbidden: "border-radius > 16px on cards/sections"
elevation:
  shadow_tint: "tint to background hue — never pure black drop shadow"
  scale: "sm → md → lg, documented as CSS vars"
  card_rule: "use cards only when elevation communicates real hierarchy"
  no_cards_when: "VISUAL_DENSITY > 7 — data breathes in plain layout"

# ── SPACING ──────────────────────────────────────────
spacing:
  unit: "8px (default) | 4px (dense) | 10px (editorial)"
  section_gap: "py-24 to py-32 default, py-40 for airy"
  hero_top_padding: "pt-24 max at desktop"
  card_padding: "p-6 to p-8"
  forbidden: "equal top and bottom padding — bottom often needs +25%"

# ── LAYOUT ───────────────────────────────────────────
layout:
  max_width: "max-w-[1400px] or max-w-7xl"
  breakpoints: "sm 640, md 768, lg 1024, xl 1280, 2xl 1536"
  viewport: "min-h-[100dvh] — never h-screen"
  grid: "CSS Grid for 2D, Flexbox for 1D, never flexbox percentage math"
  hero_constraints:
    headline_lines: "≤ 2 on desktop"
    subtext_words: "≤ 20 words, ≤ 4 lines"
    text_elements: "max 4 (eyebrow OR brand strip + headline + subtext + CTAs)"
    cta_visible: "without scroll"
    font_scale: "text-4xl md:text-5xl lg:text-6xl for most heroes"
  forbidden:
    - "centered hero when DESIGN_VARIANCE > 4"
    - "3 equal feature cards in a row"
    - "zigzag image+text alternation beyond 2 consecutive sections"
    - "eyebrow on more than ceil(sections/3) sections"
    - "split-header (left headline + right explainer) as default"
    - "navigation > 1 line at desktop, height > 80px"

# ── COMPONENTS ───────────────────────────────────────
components:
  buttons:
    height: "44-48px"
    padding: "px-6 py-3"
    label_rule: "verb + object, max 3 words, fits one line"
    contrast: "WCAG AA 4.5:1 text vs bg"
    active: "scale-[0.98] or -translate-y-[1px]"
    no_duplicate_intent: "one label per CTA intent across the page"
  inputs:
    label_position: "above input"
    placeholder_rule: "never placeholder-as-label"
    contrast: "WCAG AA on all parts (placeholder, focus ring, helper, error)"
  cards:
    default: "omit in favor of spacing; use only for real elevation"
    background_diversity: "2-3 cells in any bento grid need real visual variation"
  logo_wall:
    position: "under hero, never inside"
    content: "logos only, no category labels, real SVG from Simple Icons"
  navigation:
    height: "64-72px, cap 80px"
    desktop: "single line, hamburger if items > 5"

# ── MOTION ───────────────────────────────────────────
motion:
  intensity: "<1-10, see dial definitions>"
  easing: "cubic-bezier(0.16, 1, 0.3, 1) — exponential ease-out, no bounce"
  reduced_motion: "mandatory for intensity > 3"
  animate_only: "transform + opacity — never top/left/width/height"
  no_scroll_listener: "use Motion useScroll() / ScrollTrigger / IntersectionObserver"
  marquee: "max one per page"
  motivation_required: "every animation must have a one-sentence purpose"

# ── IMAGERY ──────────────────────────────────────────
imagery:
  priority: "gen-tool → Picsum seed → explicit placeholder slots"
  minimum: "2-3 real images even for minimalist sites"
  logo_source: "Simple Icons CDN (https://cdn.simpleicons.org/{slug}/ffffff)"
  forbidden:
    - "div-based fake screenshots"
    - "hand-rolled decorative SVGs"
    - "text + gradient blob as hero"
    - "fake-engineering-precise numbers (92%, 4.1×, 48k without real data)"

# ── DARK MODE ────────────────────────────────────────
dark_mode:
  required: true
  strategy: "Tailwind dark: variant | CSS variables"
  page_lock: "ONE theme per page, no section-level inversion"
  no_pure_black: true
  no_pure_white: true

# ── THEME LOCK ───────────────────────────────────────
theme_lock:
  one_theme_per_page: true
  no_section_inversion: true
  one_accent_across_all_sections: true
  one_corner_radius_system: true
```

## Body Sections (Markdown after frontmatter)

After the YAML frontmatter, include these sections in order:

### Overview
2-3 sentences describing the visual atmosphere, design philosophy, and key constraints.

### Colors
Table: `| Semantic Role | Hex | Tailwind Equivalent | OKLCH | Usage Rule |`

Include the forbidden list explicitly.

### Typography
Table: `| Level | Font | Size | Weight | Line-height | Tracking | Notes |`

Include banned defaults, serif discipline, and italic descender rule.

### Shape & Elevation
Document the corner-radius scale and shadow scale. Include the shape consistency lock rule.

### Spacing
Document the spacing scale. Include hero top padding cap.

### Layout
Document max-width container, breakpoints, and specific layout constraints. Include the hero discipline rules.

### Components
For each component family (buttons, inputs, cards, nav, logo wall): states, variants, constraints, and common mistakes.

### Motion
Document the motion intensity, easing curve, reduced-motion policy, and forbidden animation patterns.

### Imagery
Document the image strategy, logo sources, placeholder URLs, and banned visual patterns.

### Do's and Don'ts
5-10 concrete guardrails derived from this specific brand's patterns, not generic advice.

### Anti-Patterns for This Brand
3-5 brand-specific warnings about what AI most commonly gets wrong with this style. These vary by brand category. See `reference/anti-patterns.md` for mappings.

### Pre-Ship Checklist
The 12-item quality gate that must pass before the design is considered done.
