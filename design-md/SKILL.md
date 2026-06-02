---
name: design-md
description: Use when user wants to apply a specific brand style to a project, needs design system rules, or wants AI to generate on-brand UI. Drop brand design systems into projects for AI coding agents. 73 real brand DESIGN.md files (Apple, Stripe, Vercel, Figma, Notion, etc.) from Google's open-source spec.
---
# DESIGN.md — Brand Design Systems for AI

Drop real brand design rules into any project so AI coding agents generate pixel-perfect, on-brand UI.

## What is DESIGN.md?

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
