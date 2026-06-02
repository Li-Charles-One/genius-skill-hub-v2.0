---
name: document-brand
description: Brand design system catalog for office documents. Drop a brand theme into your project and MiniMax document skills (minimax-docx, minimax-xlsx, pptx-generator, pdf) will generate consistently branded output. Mirrors the design-md philosophy: one theme file, all formats follow. Currently 1 theme available; catalog will expand to 10.
license: MIT
---

# Document Brand — Design Systems for Office Documents

## What is Document Brand?

Just as `design-md` provides brand DESIGN.md files that frontend agents read to generate on-brand UI, **Document Brand** provides brand theme files that document skills read to generate consistently styled reports, spreadsheets, presentations, and PDFs.

One theme file. Three MiniMax skills. Zero design decisions at generation time.

**Keywords**: brand, branding, corporate identity, document design, visual identity, design system, style guide, color palette, typography, document formatting, MiniMax

## Relationship to design-md

| | design-md | document-brand |
|---|---|---|
| **Target** | Web UI, landing pages, React components | Word documents, Excel, PowerPoint, PDF |
| **Consumed by** | `frontend-design`, Claude Code, Codex | `minimax-docx`, `minimax-xlsx`, `pptx-generator`, `pdf` |
| **Format** | Google DESIGN.md spec (colors, typography, spacing, components, motion) | Document Brand spec (colors, typography, spacing + format-specific rules per skill) |
| **Catalog** | 71+ brands (Apple, Stripe, Vercel…) | 10 document themes (1 complete, 9 planned) |

## Architecture

```
document-brand/
├── SKILL.md                 ← This file — catalog + usage guide
├── preview.html             ← Visual preview
└── themes/
    └── editorial-dark.md    ← Theme #1 — 编辑级暗夜 (black + blue accent)

(More themes added here as they are designed)
```

Each theme file is self-contained. The downstream MiniMax skill reads the theme, extracts the parameters for its format, and applies them.

## Brand Theme Catalog

| # | Theme | File | Style | Best For |
|---|-------|------|-------|----------|
| 1 | 编辑级暗夜 | `themes/editorial-dark.md` | Black + blue accent, editorial | Premium proposals, pitch decks, keynotes |
| 2 | 极简商务 | *planned* | White + red accent, traditional | Reports, contracts, whitepapers |
| 3 | 金融专业 | *planned* | Deep green + gold + gray | Financial reports, investment decks |
| 4 | 创意时尚 | *planned* | Morandi muted tones | Brand books, creative proposals |
| 5 | 温暖人文 | *planned* | Earth tones + cream | Newsletters, training, culture |
| 6 | 政务公函 | *planned* | National red + dark gray | Official notices, government docs |
| 7 | 互联网快消 | *planned* | High-saturation contrast | Marketing plans, event decks |
| 8 | 医疗健康 | *planned* | Teal + white + soft green | Medical reports, SOPs |
| 9 | 暗夜奢华 | *planned* | Pure black + gold/white | Premium proposals, CEO letters |
| 10 | 学术经典 | *planned* | Burgundy + ivory + navy | Papers, research, courseware |

## How to Use

### Step 1: Pick a theme

User says:

> 用 **极简商务** 风格，生成一份季度报告。

Or the agent defaults to **极简商务** when no brand is specified.

### Step 2: Agent reads the theme file

The agent opens `themes/{theme}.md` and extracts:

- **Colors** — hex values for primary, secondary, accent, background, surface, text, border
- **Typography** — font families, weights, sizes for each heading level and body
- **Spacing** — margins, line height, cell padding
- **Skill-specific rules** — detailed guidance for the MiniMax skill being used

### Step 3: Agent applies to the MiniMax skill

Each theme file contains dedicated sections for each MiniMax skill. The agent reads only the section relevant to the task:

```
Task: "Generate a Word report"    → Read the ## minimax-docx section
Task: "Build a financial model"   → Read the ## minimax-xlsx section
Task: "Create a pitch deck"       → Read the ## pptx-generator section
Task: "Export as PDF"             → Read the ## pdf section
```

### Step 4: Consistent output

All documents in the same project use the same theme. A pitch deck, its financial model, and the follow-up report all share one brand identity — no manual coordination needed.

## Theme File Structure

Every theme file follows this schema:

```markdown
# {Theme Name}

> {One-line description of the visual character}

## Design Tokens

### Colors
[Table of color tokens with hex values and roles]

### Typography
[Table of font families, weights, and sizes per role]

### Spacing
[Table of spacing tokens]

## minimax-docx
[Format-specific rules: title page, heading styles, tables, headers/footers, lists]

## minimax-xlsx
[Format-specific rules: header row, data zone, alternate rows, totals, print layout]

## pptx-generator
[Format-specific rules: slide layouts, cover, TOC, content, section divider, charts]

## pdf
[Format-specific rules: page size, font embedding, metadata]
```

## Integration with MiniMax Skills

### minimax-docx

When creating or editing a .docx with MiniMax's OpenXML SDK pipeline:

1. Read the theme's `## minimax-docx` section
2. Apply heading styles using the theme's typography tokens in the SDK's style system
3. Set page margins and paragraph spacing from the Spacing tokens
4. Use the `assets/styles/` template that best matches the theme's character, or build styles programmatically
5. For tables, apply the header/body/alternate-row color rules

### minimax-xlsx

When creating or editing a spreadsheet with MiniMax's XML workflow:

1. Read the theme's `## minimax-xlsx` section
2. Apply header row styling (fill color, font, freeze pane) via the unpack→edit→pack pipeline
3. Set column widths, number formats, and print layout per theme rules
4. Use `style_audit.py` to verify consistency
5. For charts, use the theme's chart color palette

### pptx-generator

When creating a presentation with PptxGenJS:

1. Read the theme's `## pptx-generator` section
2. Use the theme's color tokens in place of the default design system palette
3. Apply the slide layout rules (cover, TOC, content, divider) with theme-specific sizing and positioning
4. Reference `references/design-system.md` for the underlying PptxGenJS mechanics, but override colors and fonts from the theme

### pdf

When processing or creating PDFs:

1. Read the theme's `## pdf` section
2. Apply page geometry and font embedding rules
3. For PDFs generated from docx, the docx rules already carry through

## Custom Themes

To create a new theme, copy `themes/minimal-business.md` and fill in all sections. The schema is:

1. **Design Tokens** — colors, typography, spacing (same structure for every theme)
2. **minimax-docx** — rules that make sense for the OpenXML SDK pipeline
3. **minimax-xlsx** — rules that work with the XML unpack→edit→pack workflow
4. **pptx-generator** — rules compatible with PptxGenJS
5. **pdf** — page geometry and embedding rules

Every rule should be **actionable**: not "use a professional look" but "header row: `#16213e` fill, white bold 11pt, frozen pane".

## Design Principles

1. **System over decoration** — Brand identity comes from consistent parameters, not clip art
2. **MiniMax-native** — Every rule is written for the actual MiniMax skill pipelines (OpenXML SDK, XML editing, PptxGenJS), not abstract design advice
3. **Accessibility first** — All color combinations must pass WCAG AA contrast (4.5:1 for body text)
4. **Format-aware** — A table in xlsx has different constraints than a table in pptx; the rules adapt
5. **Zero decisions** — The user picks a theme once; the agent never asks "what color should this be?"
6. **CJK native** — All themes designed with Chinese typography in mind; Latin fallbacks provided

## References

- `design-md` — the frontend counterpart of this skill (71+ brand DESIGN.md files for web UI)
- `frontend-design` — consumes design-md to generate on-brand web interfaces
- Anthropic `brand-guidelines` — the architectural inspiration (one brand system consumed by multiple output skills)
- MiniMax `minimax-docx` / `minimax-xlsx` / `pptx-generator` — the downstream consumers
