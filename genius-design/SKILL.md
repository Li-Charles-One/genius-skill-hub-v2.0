---
name: genius-design
description: Use when user wants to apply a specific brand style, reverse-engineer a website's design, or generate on-brand UI. Two workflows: (A) pick from 73 pre-built brand DESIGN.md templates, or (B) reverse-engineer any live website's CSS into a fresh DESIGN.md. Trigger keywords: 逆向, 品牌, UI设计, 网页开发, reverse engineer, brand, design system, 风格.
---
# Genius Design — Brand Design Systems for AI

Two ways to get a design system into your project.

## ⚡ First: ask the user which path

When this skill activates, **immediately ask the user**:

> 你想要哪种方式？
> - **A. 用现成模板** — 从 73 个品牌里选一个（Stripe, Apple, Linear, Vercel...）
> - **B. 逆向网站** — 给我一个网址，我抓取它的 CSS 然后自动生成 DESIGN.md
> - **C. 我不知道参考谁** — 告诉我产品类型（如「体育用品」「医疗器械」），我用 UI UX Pro Max 推理出推荐的设计方案

Then route to the matching workflow below. If the user has already provided a URL, go straight to Workflow B.

**配合 `frontend-design` skill**：genius-design 负责产出 DESIGN.md（设计规范），frontend-design 负责照着 DESIGN.md 生成高设计质量的前端代码。两者配合使用：先用 genius-design 确定品牌规则，再调用 frontend-design 执行实现。

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

When the user provides a URL or asks to reverse-engineer a site's design. Uses Firecrawl CLI — handles JS-rendered SPAs, extracts branding info natively.

### Step 1: Scrape with Firecrawl (one command, all formats)

```bash
firecrawl scrape "<url>" \
  --format rawHtml,branding,screenshot \
  --only-main-content \
  --wait-for 3000 \
  -o .firecrawl/design-data.json \
  --json --pretty
```

| Flag | Purpose |
|---|---|
| `rawHtml` | Full rendered HTML — extract class names, inline styles, component structure |
| `branding` | Firecrawl's AI brand extraction — colors, fonts, tone, logos |
| `screenshot` | Visual reference — verify extracted tokens match the actual page |
| `--only-main-content` | Strip nav/footer noise, focus on the design system body |
| `--wait-for 3000` | Wait for JS frameworks to hydrate. Bump to 5000 for heavy SPAs |
| `--json --pretty` | Structured output for parsing |

After the scrape, do a quick grep on the raw HTML to spot recurring patterns:

```bash
# Find the dominant font
grep -oP "font-family:\s*[^;]+" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -5

# Find border-radius patterns
grep -oP "border-radius:\s*\d+px" .firecrawl/design-data.json | sort | uniq -c | sort -rn

# Find box-shadow levels
grep -oP "box-shadow:\s*[^;]+" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -5

# Find all hex colors used
grep -oP "#[0-9a-fA-F]{3,8}" .firecrawl/design-data.json | sort | uniq -c | sort -rn | head -15
```

If the page requires login or interaction:
```bash
firecrawl scrape "<url>"
firecrawl interact --prompt "Click the login button, then fill credentials"
firecrawl scrape "<url>" --format rawHtml,branding,screenshot --only-main-content --wait-for 3000 -o .firecrawl/design-data.json --json --pretty
```

### Step 2: Extract design tokens

Work through each dimension systematically:

**Colors** — cross-reference `branding` output with hex grep results:
- Map every recurring hex to a semantic role. A color that appears on every `<button>` = primary CTA. The most common text color = ink.
- Count occurrences to separate signal from noise (one-off colors are likely errors)
- Identify the color system: monochrome + single accent? multi-accent? gradient-driven?

**Typography** — from `branding` output + font-family grep:
- Dominant font family (body) vs accent font (headings)
- Build the scale: what sizes appear? Look for ratios (1.25x, 1.33x, 1.5x between levels)
- Weight pattern: bold for headings, regular for body? Or light-and-airy?
- Line-height: is it tight (1.1-1.2 for headings) or comfortable (1.5-1.6 for body)?

**Spacing** — from `rawHtml`:
- Section gaps: look for `padding-top`, `padding-bottom`, `margin-bottom` on large containers
- Card padding: the most common `padding` value inside card-like containers
- Button padding: `padding` on `<button>` or `.btn-*` elements
- Grid: detect if the site uses a consistent grid (8px, 10px, 12px base unit)

**Components** — from `rawHtml`, grep for recurring class name patterns:
- Buttons: dominant border-radius, min-height, padding. Note variants (solid vs outline vs ghost)
- Cards: shadow formula, border style, rounding. Is there a single pattern or a hierarchy?
- Inputs: border color, border-radius, height. Focus ring color/style if visible
- Navigation: is it sticky? What background? What's the link spacing?

**Shapes & Elevation** — from `rawHtml`:
- Border-radius: the 2-3 most common values → map to sm/md/lg
- Shadows: count distinct box-shadow values → build elevation scale
- Border style: are borders common? What color and width?

**Semantic mapping** — the critical step. Every extracted value gets a role:
- Don't: `blue: #0064E0`
- Do: `Primary CTA (#0064E0) — all purchase buttons, signup CTAs, active nav links`

### Step 3: Write the DESIGN.md

Output a complete DESIGN.md file following Google's YAML+Markdown spec. The `branding` output gives you the token values; the `rawHtml` output gives you the component patterns. Combine both into:

```markdown
---
version: alpha
name: <site-name>-design-analysis
description: <one-sentence site description + design vibe from branding output>
colors:
  primary: "#xxxxxx"
  background: "#xxxxxx"
  ink: "#xxxxxx"
  ...
typography:
  display: { fontFamily: "...", fontSize: "...", fontWeight: ... }
  h1: { ... }
  body: { ... }
rounded:
  sm: "..."
  md: "..."
spacing:
  sm: "..."
  md: "..."
---

## Overview
<2-3 sentences describing the visual atmosphere>

## Colors
<semantic name | hex | role table>

## Typography
<level | font | size | weight | line-height table>

## Components
<button, card, input, nav patterns with states>

## Do's and Don'ts
<3-5 guardrails derived from observed patterns>
```

### Step 4: Save + apply

Write the generated DESIGN.md to `./DESIGN.md` in the project root. Tell the user it's ready and what the key design decisions are (primary color, font stack, vibe).

### Limitations

- Firecrawl extracts computed styles — matches what users see, not necessarily internal design tokens.
- Interactive states (hover, focus, active) are inferred from class name patterns, not directly observed.
- The `branding` format is a best-effort AI analysis; always spot-check against the raw HTML.
- For highly dynamic SPAs, increase `--wait-for` or use `firecrawl interact`.

---

## Workflow C: Generate from product type (via UI UX Pro Max)

When the user doesn't know what brand to reference or what style fits their product.

### Step 1: Ask what they're building

Get a short description: industry, product type, target audience. Examples:
- 「医疗 SaaS 平台，给医生用的管理后台」
- 「运动品牌电商，卖跑鞋和健身装备」
- 「儿童教育 App，面向家长」

### Step 2: Run UI UX Pro Max design system generator

```bash
python3 skills/ui-ux-pro-max/scripts/search.py "<product description>" --design-system -f markdown
```

If the skill is installed elsewhere, find `search.py` under the community-skill-hub path or the upstream repo.

This outputs a complete design recommendation:
- **Layout pattern** (hero-centric, dashboard-grid, etc.)
- **UI style** (glassmorphism, minimalism, soft UI, etc.)
- **Color palette** (primary, background, accent, text with hex values)
- **Typography pairing** (display + body fonts with Google Fonts URL)
- **Key effects** (shadows, transitions, interactions)
- **Anti-patterns to avoid** (industry-specific don'ts)

### Step 3: Convert to DESIGN.md

Take the UI UX Pro Max output and translate it into a standard DESIGN.md file:

```
UI UX Pro Max output          →  DESIGN.md
─────────────────────────────────────────
Style: "Soft UI Evolution"    →  Overview section (design atmosphere)
Primary: #E8B4B8             →  colors.primary in YAML front matter
Typography: Cormorant / Montserrat → typography section
Key effects: soft shadows     →  Components section (button/card patterns)
Anti-patterns: no neon        →  Do's and Don'ts section
```

### Step 4: Save + apply

Write the generated DESIGN.md to `./DESIGN.md`. Tell the user the key design decisions and offer to refine anything they don't like. Then suggest calling `frontend-design` to build the actual UI.

### Example flow

```
User: "我要做个宠物医院的管理系统，不知道长什么样"
  ↓
Step 1: 识别 → 医疗 + 宠物 + 管理后台
Step 2: search.py "veterinary clinic management dashboard" --design-system
Step 3: 输出 → Soft UI, 暖绿配奶油白, M PLUS Rounded 1c + Inter
Step 4: 写成 DESIGN.md, 建议 frontend-design 实现
```

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
