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
    └── editorial-dark/      ← Theme #1 — 编辑级暗夜 (black + blue accent)
        ├── tokens.md        ← Shared design tokens (colors, typography, spacing)
        ├── docx-template.md ← minimax-docx instructions
        ├── xlsx-template.md ← minimax-xlsx instructions
        ├── pptx-template.md ← pptx-generator instructions
        └── pdf-template.md  ← pdf instructions

(More themes added here as they are designed)
```

Each theme is a **directory** with shared design tokens in `tokens.md` and one template file per output format. The agent reads only the two files it needs — `tokens.md` + the format template — never the whole catalog.

## Brand Theme Catalog

| # | Theme | Directory | Style | Best For |
|---|-------|-----------|-------|----------|
| 1 | 编辑级暗夜 | `themes/editorial-dark/` | Black + blue accent, editorial | Premium proposals, pitch decks, keynotes |
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

### Step 2: Agent reads TWO files — no more

For any given task, the agent reads exactly two files:

1. `themes/{theme}/tokens.md` — colors, typography, spacing (shared by all formats)
2. `themes/{theme}/{format}-template.md` — format-specific instructions

```
Task: "Generate a Word report"  → tokens.md + docx-template.md
Task: "Build a financial model" → tokens.md + xlsx-template.md
Task: "Create a pitch deck"     → tokens.md + pptx-template.md
Task: "Export as PDF"           → tokens.md + pdf-template.md
```

This keeps context minimal — the agent never loads unrelated format instructions.

### Step 3: Agent applies to the MiniMax skill

The format template contains concrete, actionable rules written for the specific MiniMax skill pipeline. Apply them directly.

### Step 4: Consistent output

All documents in the same project use the same theme. A pitch deck, its financial model, and the follow-up report all share one brand identity — no manual coordination needed.

## Theme Directory Structure

Every theme directory follows this structure:

```
themes/{theme}/
├── tokens.md          ← Design tokens: colors, typography, spacing (shared by all formats)
├── docx-template.md   ← minimax-docx: title page, heading styles, tables, lists
├── xlsx-template.md   ← minimax-xlsx: header row, data zone, totals, charts, print
├── pptx-template.md   ← pptx-generator: slide layouts, color mapping, design checklist
└── pdf-template.md    ← pdf: page size, font embedding, print notes
```

**Why split?** When generating a docx, the agent only needs tokens + docx-template — loading xlsx and pptx rules wastes context. One format, two files, zero noise.

## Integration with MiniMax Skills

### minimax-docx

When creating or editing a .docx with MiniMax's OpenXML SDK pipeline:

1. Read `tokens.md` + `docx-template.md`
2. Apply heading styles using the typography tokens
3. Set page margins and paragraph spacing from the Spacing tokens
4. For tables, apply the header/body/alternate-row color rules from the template

### minimax-xlsx

When creating or editing a spreadsheet with MiniMax's XML workflow:

1. Read `tokens.md` + `xlsx-template.md`
2. Apply header row styling (fill color, font, freeze pane) via the unpack→edit→pack pipeline
3. Set column widths, number formats, and print layout per template rules
4. For charts, use the template's chart color palette

### pptx-generator

When creating a presentation with PptxGenJS:

1. Read `tokens.md` + `pptx-template.md`
2. Use the PptxGenJS color mapping from the template
3. Apply slide layout rules (cover, TOC, content, divider) with template-specific sizing

### pdf

When processing or creating PDFs:

1. Read `tokens.md` + `pdf-template.md`
2. Apply page geometry and font embedding rules
3. For PDFs generated from docx, the docx rules already carry through

## Custom Themes

To create a new theme, copy an existing theme directory (e.g. `themes/editorial-dark/`) and fill in all files:

1. **tokens.md** — colors, typography, spacing (same structure for every theme)
2. **docx-template.md** — rules that make sense for the OpenXML SDK pipeline
3. **xlsx-template.md** — rules that work with the XML unpack→edit→pack workflow
4. **pptx-template.md** — rules compatible with PptxGenJS
5. **pdf-template.md** — page geometry and embedding rules

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
