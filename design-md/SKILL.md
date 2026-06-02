---
name: design-md
description: Use when user wants to apply a specific brand style, reverse-engineer a website's design, or generate on-brand UI. Two workflows: (A) pick from 73 pre-built brand DESIGN.md templates, or (B) reverse-engineer any live website's CSS into a fresh DESIGN.md. Trigger keywords: 逆向, 品牌, UI设计, 网页开发, reverse engineer, brand, design system, 风格.
---
# DESIGN.md — Brand Design Systems for AI

Two ways to get a design system into your project.

## ⚡ First: ask the user which path

When this skill activates, **immediately ask the user**:

> 你想要哪种方式？
> - **A. 用现成模板** — 从 73 个品牌里选一个（Stripe, Apple, Linear, Vercel...）
> - **B. 逆向网站** — 给我一个网址，我抓取它的 CSS 然后自动生成 DESIGN.md

Then route to the matching workflow below. If the user has already provided a URL, go straight to Workflow B.

---

## Workflow A: Use a pre-built brand template

Copy an existing DESIGN.md from the awesome-design-md collection into the project root.

### What is DESIGN.md?

Google's open-source format (Apr 2026) — a Markdown file that describes a complete design system: colors, typography, spacing, components, motion. AI agents read it and follow the rules.

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

## How to Use

### Method 1: Fetch from GitHub (recommended)

```bash
# Clone the collection
# Clone the collection (uses your fork as primary, falls back to upstream)
git clone --depth 1 https://github.com/Li-Charles-One/awesome-design-md /tmp/awesome-design-md

# Copy desired brand's DESIGN.md to project root
cp /tmp/awesome-design-md/design-md/apple/DESIGN.md ./DESIGN.md
```

### Method 2: Direct download

```bash
# Download a specific brand
curl -sL "https://raw.githubusercontent.com/Li-Charles-One/awesome-design-md/main/design-md/apple/DESIGN.md" -o ./DESIGN.md
```

### Method 3: On-demand fetch script

```bash
# Use the bundled script
python scripts/fetch_design_md.py apple ./DESIGN.md
```

## Workflow

1. **User picks a brand** (or describes desired aesthetic)
2. **Agent fetches DESIGN.md** from GitHub
3. **Drop into project root** (`./DESIGN.md`)
4. **Claude Code / coding agent** reads it automatically
5. **Generated UI follows brand rules** — colors, fonts, spacing, components

## Custom DESIGN.md

If no brand matches, create a custom one following Google's spec:

```markdown
# Design System

## Colors
- Primary: #007AFF
- Background: #FFFFFF
- Text: #1D1D1F

## Typography
- Font: SF Pro Display
- Headings: 48px bold
- Body: 17px regular

## Spacing
- Unit: 8px
- Section gap: 48px

## Components
- Buttons: rounded-lg, 44px height
- Cards: rounded-xl, shadow-md

## Motion
- Duration: 200ms ease
- Easing: cubic-bezier(0.25, 0.1, 0.25, 1)
```

## Fallback Strategy

Primary: fetch from your fork (`Li-Charles-One/awesome-design-md`). If that fails, fall back to the upstream (`VoltAgent/awesome-design-md`). Once a DESIGN.md is placed in the project root, it has zero external dependencies.

## Pitfalls

### ⚠️ DESIGN.md Must Be in Project Root
AI agents look for `./DESIGN.md` at the project root, not in subdirectories.

### ⚠️ Not All Brands Have Equal Detail
Some DESIGN.md files are more comprehensive than others. Apple/Stripe/Vercel are very detailed; smaller brands may be simpler.

### ⚠️ Custom Overrides
If you have both `DESIGN.md` and custom CSS/tokens, the agent may conflict. Keep DESIGN.md as the single source of truth.

---

## Workflow B: Reverse-engineer a live website

When the user provides a URL or asks to reverse-engineer a site's design.

### Step 1: Fetch the page

Use `web_fetch` to download the target URL. Capture:
- The full visible text content
- Inline CSS (`<style>` blocks and `style=""` attributes visible in the fetched text)
- Class names visible in the HTML structure

### Step 2: Extract design tokens

From the fetched content, identify and extract:

**Colors** — semantic roles, not just hex values:
- Primary / brand color (CTAs, links, accent elements)
- Background (page background, card surfaces)
- Text / ink (headings, body copy)
- Secondary text (captions, metadata)
- Border / hairline (dividers, input borders)
- Success / warning / error (if present)

**Typography** — build a hierarchy:
- Font family (headings vs body)
- Size scale: Display → H1 → H2 → H3 → Body → Caption
- Weight patterns (bold headings? light body?)
- Line-height and letter-spacing trends

**Spacing & Layout**:
- Section gaps (padding between major blocks)
- Card padding
- Button padding
- Container max-width

**Components** — describe the patterns:
- Buttons (border-radius, padding, hover effects)
- Cards (shadow, border, rounding)
- Inputs (border style, focus ring)
- Navigation (sticky? background? link spacing)

**Shapes & Elevation**:
- Border-radius scale (sm / md / lg)
- Shadow levels (card shadow, modal overlay)
- Border styles

### Step 3: Write the DESIGN.md

Output a complete DESIGN.md file following Google's spec format:

```markdown
---
version: alpha
name: <site-name>-design-analysis
description: <one-sentence site description + design vibe>
colors:
  primary: "#xxxxxx"
  background: "#xxxxxx"
  ink: "#xxxxxx"
  ...
typography:
  display: { fontFamily: "...", fontSize: "...", fontWeight: ... }
  h1: { ... }
  h2: { ... }
  body: { ... }
  caption: { ... }
rounded:
  sm: "..."
  md: "..."
  lg: "..."
spacing:
  sm: "..."
  md: "..."
  lg: "..."
---

## Overview
<2-3 sentences describing the visual atmosphere>

## Colors
<table with semantic name | hex | role>

## Typography
<table with level | font | size | weight | line-height>

## Components
<button, card, input, nav patterns>

## Do's and Don'ts
<3-5 guardrails derived from observed patterns>
```

### Step 4: Save + apply

Write the generated DESIGN.md to the project root, then tell the user it's ready. The agent will automatically reference it for subsequent UI generation.

### Limitations (be transparent)

- `web_fetch` only captures server-rendered HTML and inline styles. External stylesheets, JS-driven styles, and CSS custom properties are often missed.
- The extracted DESIGN.md will be a **best-effort approximation** — less precise than the hand-authored files in Workflow A.
- Always tell the user what was confidently extracted vs what was guessed.

---

## Font Substitutions

Brand DESIGN.md files reference proprietary fonts. Use these CDN-available alternatives:

| 原始字体 | CDN 替代 | 特征 |
|---------|---------|------|
| Geist | Geist (Google Fonts) | 几何、紧凑 |
| sohne-var (Stripe) | Source Sans 3 | 轻盈优雅 |
| Airbnb Cereal | DM Sans | 圆润友好 |
| Circular (Spotify) | DM Sans | 几何温暖 |
| figmaSans | Inter | 干净人文 |

## Selection Guide

- **Developer tools / dashboards**: Linear, Vercel, Supabase, Raycast, Sentry
- **Documentation / content sites**: Mintlify, Notion, Sanity, MongoDB
- **Marketing / landing pages**: Stripe, Framer, Apple, SpaceX
- **Dark mode**: Linear, Cursor, ElevenLabs, Warp, Superhuman
- **Light / clean**: Vercel, Stripe, Notion, Cal.com
- **Playful / friendly**: PostHog, Figma, Lovable, Zapier, Miro
- **Premium / luxury**: Apple, BMW, Stripe, Superhuman, Revolut

## References

- **Google Stitch spec**: https://stitch.withgoogle.com/docs/design-md/overview/
- **Your fork (primary)**: https://github.com/Li-Charles-One/awesome-design-md
- **Upstream (fallback)**: https://github.com/VoltAgent/awesome-design-md
- **Online catalog**: https://getdesign.md
