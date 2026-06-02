---
name: document-brand
description: Unified brand design system for office documents. Provides 10 pluggable brand themes covering colors, typography, and layout rules for docx, xlsx, pptx, and pdf workflows. Use when creating any document and you want consistent, professional branding without re-deciding design every time.
license: MIT
---

# Document Brand — Unified Design System for Office Documents

## Overview

A single source of truth for document-level brand identity. When you produce a report, spreadsheet, presentation, or PDF, reference this skill to get the brand parameters — colors, fonts, spacing, and format-specific rules — rather than reinventing them each time.

**Keywords**: brand, branding, corporate identity, document design, visual identity, design system, style guide, color palette, typography, document formatting

## Architecture

```
document-brand (this skill)
    │
    ├── 10 brand themes, each defining:
    │   ├── Colors (primary, secondary, accent, background, text)
    │   ├── Typography (headings, body, code, captions)
    │   ├── Spacing & layout tokens
    │   └── Format-specific rules ↓
    │
    ├──→ docx   (page margins, heading hierarchy, table styles, headers/footers)
    ├──→ xlsx   (header rows, data zones, conditional formatting, print layout)
    ├──→ pptx   (slide layouts, chart palettes, text hierarchy, cover/divider styles)
    └──→ pdf    (page geometry, watermark, margin, font embedding)
```

## How to Use

### Step 1: Pick a theme

Choose from the [Brand Theme Catalog](#brand-theme-catalog) below. Each theme has a name and a one-line description.

### Step 2: Tell the downstream skill

When using `docx`, `xlsx`, `pptx`, or `pdf`, include the directive:

> Apply the **{Theme Name}** brand from `document-brand`. Use its colors, fonts, and layout rules.

### Step 3: The downstream skill reads this file

Each theme section below is self-contained — the downstream skill extracts colors, fonts, and format-specific rules for its output.

---

## Brand Theme Catalog

| # | Theme | Style | Best For |
|---|-------|-------|----------|
| 1 | [极简商务](#1-极简商务-minimal-business) | Black/white + single accent | Reports, contracts, whitepapers |
| 2 | [科技蓝调](#2-科技蓝调-tech-blue) | Deep blue gradients + cyan | Tech proposals, API docs, SaaS |
| 3 | [学术经典](#3-学术经典-academic-classic) | Burgundy + ivory + navy | Papers, research, courseware |
| 4 | [金融专业](#4-金融专业-finance-pro) | Deep green + gold + gray | Financial reports, investment decks |
| 5 | [创意时尚](#5-创意时尚-creative-fashion) | Morandi muted tones | Brand books, creative proposals |
| 6 | [温暖人文](#6-温暖人文-warm-humanist) | Earth tones + cream | Newsletters, training, culture |
| 7 | [政务公函](#7-政务公函-government-official) | National red + dark gray | Official notices, government docs |
| 8 | [互联网快消](#8-互联网快消-internet-pop) | High-saturation contrast | Marketing plans, event decks |
| 9 | [医疗健康](#9-医疗健康-healthcare) | Teal + white + soft green | Medical reports, SOPs, health content |
| 10 | [暗夜奢华](#10-暗夜奢华-dark-luxury) | Pure black + gold/white | Premium proposals, CEO letters |

---

## 1. 极简商务 (Minimal Business)

> Clean, authoritative, timeless. Black and white with a single controlled accent. No decoration, only hierarchy.

### Colors

| Token | Hex | Role |
|-------|-----|------|
| `primary` | `#1a1a2e` | Headings, strong emphasis |
| `secondary` | `#16213e` | Subheadings, table headers |
| `accent` | `#e94560` | Key data highlights, call-to-action |
| `background` | `#ffffff` | Page background |
| `surface` | `#f5f5f7` | Table alternate rows, sidebar |
| `text-primary` | `#1a1a2e` | Body text |
| `text-secondary` | `#6b7280` | Captions, footnotes, metadata |
| `border` | `#e5e7eb` | Table borders, dividers |

### Typography

| Role | Font | Weight | Size |
|------|------|--------|------|
| Document Title | Noto Sans SC Bold / DM Serif Display | 700 | 28pt |
| Heading 1 | Noto Sans SC Bold | 700 | 20pt |
| Heading 2 | Noto Sans SC Medium | 600 | 16pt |
| Heading 3 | Noto Sans SC Medium | 500 | 14pt |
| Body | Noto Sans SC Regular / Inter | 400 | 11pt |
| Caption / Footnote | Noto Sans SC Light | 300 | 9pt |
| Code / Data | JetBrains Mono | 400 | 10pt |

### Spacing

| Token | Value |
|-------|-------|
| Page Margin | 1 inch / 2.54 cm |
| Paragraph Spacing (After) | 6pt |
| Line Height (Body) | 1.35 |
| Table Cell Padding | 4pt top/bottom, 6pt left/right |

### docx Rules

- **Title page**: Title centered 3" from top, subtitle below in `text-secondary`, date at bottom
- **Headings**: H1 left-aligned, H2 with 6pt rule below in `border` color, H3 plain
- **Tables**: Header row `secondary` background with white text; odd rows `surface` background
- **Header/Footer**: Running title left-aligned, page number right-aligned, 0.5pt `border` rule
- **List bullets**: `accent` color, size 8pt, indented 0.5"

### xlsx Rules

- **Header row**: `secondary` fill, white bold text, frozen pane, auto-filter enabled
- **Data zone**: White background, `border` gridlines, `text-primary` text
- **Alternate rows**: `surface` fill every other row for readability
- **Totals row**: Bold, `accent` top border (medium weight)
- **Number formatting**: #,##0 for integers, #,##0.00 for decimals, ¥#,##0 for RMB
- **Print**: A4 portrait, repeat header row, page number footer, `accent` thin gridlines

### pptx Rules

- **Slide size**: 16:9 (13.33" × 7.5")
- **Cover slide**: Title bold left-aligned 44pt, accent bar 4pt thick below title, subtitle 24pt `text-secondary`, date bottom-right
- **TOC slide**: Numbered list with `accent` numbers, hanging indent
- **Content slide**: Title 30pt top-left, body 18pt, generous whitespace
- **Section divider**: Solid `secondary` background, white title centered, `accent` underline 2pt
- **Charts**: Palette: `primary`, `secondary`, `accent`, `#6b7280`, `#d1d5db`; no 3D, no gradients
- **Tables in slides**: Same rules as xlsx, scaled to slide width

### pdf Rules

- Inherits all **docx Rules** above
- **Page size**: A4 (210mm × 297mm) or US Letter (8.5" × 11")
- **Font embedding**: Embed subset for Noto Sans SC
- **Metadata**: Include author, title, subject from document properties

---

## 2. 科技蓝调 (Tech Blue)

> Deep, luminous, futuristic. Dark navy backgrounds with electric cyan accents. Inspired by terminal aesthetics and AI interfaces.

### Colors

| Token | Hex | Role |
|-------|-----|------|
| `primary` | `#03045e` | Deep navy — headings |
| `secondary` | `#0077b6` | Medium blue — subheadings, table headers |
| `accent` | `#00b4d8` | Electric cyan — highlights, CTAs |
| `background` | `#ffffff` | Page background (light mode) |
| `surface` | `#f0f8ff` | Alternate rows, side panels |
| `text-primary` | `#0a0a1a` | Body text |
| `text-secondary` | `#5e6e8c` | Captions, metadata |
| `border` | `#c8d6e5` | Dividers, table borders |
| `dark-bg` | `#03045e` | Dark mode backgrounds (pptx, section dividers) |
| `dark-text` | `#caf0f8` | Text on dark backgrounds |

### Typography

| Role | Font | Weight | Size |
|------|------|--------|------|
| Document Title | Space Grotesk Bold | 700 | 28pt |
| Heading 1 | Space Grotesk Bold | 700 | 20pt |
| Heading 2 | Space Grotesk Medium | 600 | 16pt |
| Heading 3 | Space Grotesk Regular | 500 | 14pt |
| Body | Inter / Noto Sans SC | 400 | 11pt |
| Caption | Inter Light | 300 | 9pt |
| Code | JetBrains Mono | 400 | 10pt |

### Spacing

| Token | Value |
|-------|-------|
| Page Margin | 1 inch / 2.54 cm |
| Paragraph Spacing | 8pt after |
| Line Height | 1.4 |
| Table Cell Padding | 4pt top/bottom, 8pt left/right |

### docx Rules

- **Title page**: Solid `primary` rectangle top-third, white title overlay, subtitle below
- **Headings**: H1 with `accent` left border 4pt thick; H2 plain; H3 with `accent` bullet
- **Tables**: Header row `secondary` background white text; odd rows `surface`; `border` grid
- **Header/Footer**: Dark `primary` strip with white text
- **Code blocks**: `surface` background, `JetBrains Mono`, `primary` left border

### xlsx Rules

- **Header row**: `secondary` fill, white bold text, frozen pane
- **Data zone**: White, `border` gridlines; alternate rows `surface`
- **Totals**: Bold white on `secondary` background
- **Charts**: Blue gradient palette, flat (no 3D), clean gridlines
- **Print**: A4 landscape recommended for wide data

### pptx Rules

- **Slide size**: 16:9
- **Cover**: Dark `primary` background, white title 48pt, `accent` underline, subtitle in `dark-text`
- **Content**: Light background, `primary` title bar 4pt top, generous whitespace
- **Section divider**: Full `primary` slide, centered white text, `accent` geometric accent line
- **Code slides**: `dark-bg` background, `accent` monospace code, terminal aesthetic
- **Charts**: Deep-to-light blue gradient; avoid red/green alone for accessibility

### pdf Rules

- Inherits **docx Rules**
- Prefer US Letter for technical documents
- Include metadata with version number

---

## 3. 学术经典 (Academic Classic)

> *Reserved for detailed definition. See theme #1 for the parameter structure to follow.*

---

## 4. 金融专业 (Finance Pro)

> *Reserved for detailed definition. See theme #1 for the parameter structure to follow.*

---

## 5. 创意时尚 (Creative Fashion)

> *Reserved for detailed definition. See theme #1 for the parameter structure to follow.*

---

## 6. 温暖人文 (Warm Humanist)

> *Reserved for detailed definition. See theme #1 for the parameter structure to follow.*

---

## 7. 政务公函 (Government Official)

> *Reserved for detailed definition. See theme #1 for the parameter structure to follow.*

---

## 8. 互联网快消 (Internet Pop)

> *Reserved for detailed definition. See theme #1 for the parameter structure to follow.*

---

## 9. 医疗健康 (Healthcare)

> *Reserved for detailed definition. See theme #1 for the parameter structure to follow.*

---

## 10. 暗夜奢华 (Dark Luxury)

> *Reserved for detailed definition. See theme #1 for the parameter structure to follow.*

---

## Integration

### For Skill Authors

When writing a skill that produces documents, reference this design system:

```markdown
## Brand & Style

Before producing any output, check if the user specified a brand theme.
If not, default to **极简商务** from the `document-brand` skill.

Read the theme's Colors, Typography, and format-specific rules for your output format.
Apply them consistently throughout the document.
```

### For Users

Just tell the agent:

> 用 **科技蓝调** 品牌风格，生成一份项目方案。

Or set a default in your project:

> 这个项目默认用 **极简商务** 风格。

### Cross-Format Consistency

When producing multiple documents in the same project, use the same brand theme across all formats. A pitch deck and its accompanying financial model should feel like they belong together.

---

## Design Principles

1. **System over decoration** — Brand identity comes from consistent parameters, not clip art
2. **Accessibility first** — All color combinations must pass WCAG AA contrast (4.5:1 for body text)
3. **Format-aware** — A table in xlsx has different needs than a table in pptx; the rules adapt
4. **Zero decisions** — The user picks a theme once; the agent never asks "what color should this be?"
5. **CJK native** — All themes designed with Chinese typography in mind; Latin fallbacks provided

## References

- Inspired by Anthropic's `brand-guidelines` skill architecture
- Complementary to `design-md` (frontend brand systems) and `frontend-design` (web UI execution)
- Consumed by `docx`, `xlsx`, `pptx`, `pdf` skills in the official skill hub
