---
name: design-md
description: "Use when user wants to apply a specific brand style to a project, needs design system rules, or wants AI to generate on-brand UI. Drop brand design systems into projects for AI coding agents. 71+ real brand DESIGN.md files (Apple, Stripe, Vercel, Figma, Notion, etc.) from Google's open-source spec."
license: MIT
---

# DESIGN.md — Brand Design Systems for AI

Drop real brand design rules into any project so AI coding agents generate pixel-perfect, on-brand UI.

## What is DESIGN.md?

Google's open-source format (Apr 2026) — a Markdown file that describes a complete design system: colors, typography, spacing, components, motion. AI agents read it and follow the rules.

## Brand Catalog (71+ brands)

### AI & LLM
Claude, Cohere, ElevenLabs, Minimax, Mistral AI, Ollama, OpenCode AI, Replicate, RunwayML, Together AI, VoltAgent, xAI

### Developer Tools
Cursor, Expo, Lovable, Raycast, Superhuman, Vercel, Warp

### Backend & DevOps
ClickHouse, Composio, HashiCorp, MongoDB, PostHog, Sanity, Sentry, Supabase

### Productivity & SaaS
Cal.com, Intercom, Linear, Mintlify, Notion, Resend, Zapier

### Design Tools
Airtable, Clay, Figma, Framer, Miro, Webflow

### Fintech
Binance, Coinbase, Kraken, Mastercard, Revolut, Stripe, Wise

### E-commerce
Airbnb, Meta, Nike, Shopify, Starbucks

### Media & Tech
Apple, IBM, NVIDIA, Pinterest, PlayStation, SpaceX, Spotify, The Verge, Uber, Vodafone, WIRED

### Automotive
BMW, BMW M, Bugatti, Ferrari, Lamborghini, Renault, Tesla

## How to Use

### Method 1: Fetch from GitHub (recommended)

```bash
# Clone the collection
git clone --depth 1 https://github.com/VoltAgent/awesome-design-md /tmp/awesome-design-md

# Copy desired brand's DESIGN.md to project root
cp /tmp/awesome-design-md/design-md/apple/DESIGN.md ./DESIGN.md
```

### Method 2: Direct download

```bash
# Download a specific brand
curl -sL "https://raw.githubusercontent.com/VoltAgent/awesome-design-md/main/design-md/apple/DESIGN.md" -o ./DESIGN.md
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

## Integration with Claude Code

```bash
# Before running Claude Code, ensure DESIGN.md exists in project root
Use Linus' available coding agent path, such as Codex or a configured MCP coding agent, and explicitly tell it to follow `./DESIGN.md`.
```

## Pitfalls

### ⚠️ DESIGN.md Must Be in Project Root
AI agents look for `./DESIGN.md` at the project root, not in subdirectories.

### ⚠️ Not All Brands Have Equal Detail
Some DESIGN.md files are more comprehensive than others. Apple/Stripe/Vercel are very detailed; smaller brands may be simpler.

### ⚠️ Custom Overrides
If you have both `DESIGN.md` and custom CSS/tokens, the agent may conflict. Keep DESIGN.md as the single source of truth.

## Popular Web Designs (54 Brands)

除了 DESIGN.md 格式，也提供 54 个真实品牌的 HTML/CSS 设计模板，可直接用于生成页面。

### 使用方法

1. 选择品牌模板
2. 加载：`skill_view(name="design-md", file_path="templates/<brand>.md")`
3. 使用模板中的设计 token 和组件规范生成 HTML

### 品牌目录

**AI & ML**: Claude, Cohere, ElevenLabs, Minimax, Mistral, Ollama, OpenCode, Replicate, RunwayML, Together AI, VoltAgent, xAI

**开发者工具**: Cursor, Expo, Linear, Lovable, Mintlify, PostHog, Raycast, Resend, Sentry, Supabase, Superhuman, Vercel, Warp, Zapier

**基础设施**: ClickHouse, Composio, HashiCorp, MongoDB, Sanity, Stripe

**设计工具**: Airtable, Clay, Figma, Framer, Intercom, Miro, Notion, Pinterest, Webflow

**金融科技**: Coinbase, Kraken, Revolut, Wise

**企业消费**: Airbnb, Apple, BMW, IBM, NVIDIA, SpaceX, Spotify, Uber

### 字体替换参考

| 原始字体 | CDN 替代 | 特征 |
|---------|---------|------|
| Geist | Geist (Google Fonts) | 几何、紧凑 |
| sohne-var (Stripe) | Source Sans 3 | 轻盈优雅 |
| Airbnb Cereal | DM Sans | 圆润友好 |
| Circular (Spotify) | DM Sans | 几何温暖 |
| figmaSans | Inter | 干净人文 |

### 选择指南

- **开发者工具/看板**: Linear, Vercel, Supabase, Raycast, Sentry
- **文档/内容站**: Mintlify, Notion, Sanity, MongoDB
- **营销/落地页**: Stripe, Framer, Apple, SpaceX
- **暗色模式**: Linear, Cursor, ElevenLabs, Warp, Superhuman
- **亮色/简洁**: Vercel, Stripe, Notion, Cal.com
- **活泼/友好**: PostHog, Figma, Lovable, Zapier, Miro
- **高端/奢华**: Apple, BMW, Stripe, Superhuman, Revolut

## References

- **Google Stitch spec**: https://stitch.withgoogle.com/docs/design-md/overview/
- **GitHub collection**: https://github.com/VoltAgent/awesome-design-md
- **DESIGN.md app**: https://designmd.app
