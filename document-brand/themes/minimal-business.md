# 极简商务 (Minimal Business)

> 克制、权威、耐久。黑白为底，单色点缀。没有装饰，只有层次。

---

## Design Tokens

### Colors

| Token | Hex | Preview | Role |
|-------|-----|---------|------|
| `primary` | `#1a1a2e` | ■ | 标题、强调文字 |
| `secondary` | `#16213e` | ■ | 副标题、表头背景 |
| `accent` | `#e94560` | ■ | 关键数据、行动点、图表高亮 |
| `background` | `#ffffff` | ■ | 页面背景 |
| `surface` | `#f5f5f7` | ■ | 表格隔行、侧栏底色 |
| `text-primary` | `#1a1a2e` | ■ | 正文 |
| `text-secondary` | `#6b7280` | ■ | 说明文字、脚注、元信息 |
| `border` | `#e5e7eb` | ■ | 表格线、分割线 |
| `chart-1` | `#1a1a2e` | ■ | 图表系列 1 |
| `chart-2` | `#e94560` | ■ | 图表系列 2 |
| `chart-3` | `#6b7280` | ■ | 图表系列 3 |
| `chart-4` | `#d1d5db` | ■ | 图表系列 4 |
| `chart-5` | `#f5f5f7` | ■ | 图表系列 5 |

### Typography

| Role | Font Stack | Weight | Size | Line Height |
|------|-----------|--------|------|-------------|
| 文档标题 | Noto Sans SC Bold, DM Serif Display, serif | 700 | 28pt | 1.2 |
| 一级标题 | Noto Sans SC Bold, Arial, sans-serif | 700 | 20pt | 1.25 |
| 二级标题 | Noto Sans SC Medium, Arial, sans-serif | 600 | 16pt | 1.3 |
| 三级标题 | Noto Sans SC Medium, Arial, sans-serif | 500 | 14pt | 1.3 |
| 正文 | Noto Sans SC Regular, Inter, sans-serif | 400 | 11pt | 1.35 |
| 说明/脚注 | Noto Sans SC Light, Inter, sans-serif | 300 | 9pt | 1.4 |
| 代码/数据 | JetBrains Mono, Consolas, monospace | 400 | 10pt | 1.4 |

### Spacing

| Token | Value |
|-------|-------|
| 页边距 | 2.54 cm / 1 inch |
| 段落间距（段后） | 6pt |
| 正文行高 | 1.35 |
| 表格单元格内边距 | 上下 4pt，左右 6pt |
| 标题上间距 | 18pt |
| 标题下间距 | 6pt |

---

## minimax-docx

> Target pipeline: OpenXML SDK (.NET) — create from scratch, fill template, or edit existing.

### Page Setup

- **Page size**: A4 (210mm × 297mm). Use US Letter (8.5" × 11") only when user specifies.
- **Margins**: 2.54 cm all sides (1 inch). In the SDK, set via `PageSize` and `PageMargin` classes.
- **Header/Footer distance**: 1.25 cm from edge.

### Title Page (when document has one)

- Title centered vertically at 40% from top of page.
- Title font: 28pt, `primary`, bold.
- Subtitle: 14pt, `text-secondary`, 12pt below title.
- Date: 10pt, `text-secondary`, aligned to bottom-right margin.
- Author/organization: 10pt, `text-secondary`, left-aligned at bottom margin.
- No horizontal rules or decorative elements.

### Heading Styles

Use the SDK's style system. Override `Heading1`, `Heading2`, `Heading3` built-in style IDs:

| Style ID | Font | Size | Color | Spacing | Extra |
|----------|------|------|-------|---------|-------|
| `Heading1` | 文档标题 typography | 20pt | `primary` | 18pt before, 6pt after | Left-aligned. No numbering unless user asks. |
| `Heading2` | 一级标题 typography | 16pt | `primary` | 12pt before, 6pt after | 6pt bottom border in `border`, width 100%. |
| `Heading3` | 二级标题 typography | 14pt | `secondary` | 8pt before, 4pt after | Plain. No underline. |

### Body Text

- Default paragraph style: 11pt, `text-primary`, 1.35 line height, 6pt after.
- First line indent: none. Use paragraph spacing for separation.
- Alignment: justified for CJK documents, left-aligned for English.

### Lists

- **Bullet**: Use `LevelFormat.BULLET` with numbering config. Bullet character "•" in `accent` color, 8pt, indent 0.5" (720 DXA), hanging 0.25" (360 DXA).
- **Numbered**: Use `LevelFormat.DECIMAL`. Number in `primary`, same indent as bullets.
- Never use Unicode bullet characters in text runs.

### Tables

Follow the SDK table creation pattern. Always set both `columnWidths` on the table AND `width` on each cell in DXA units.

| Element | Style |
|---------|-------|
| **Header row** | `secondary` background. White text, bold, 11pt. Cell padding: 4pt top/bottom, 6pt left/right. |
| **Data rows** | White background (`background`). `text-primary`, regular, 11pt. |
| **Alternate rows** | `surface` background on even rows (row 2, 4, 6…). Keep header as row 1, start alternation from row 2. |
| **Borders** | All cells: 0.5pt solid `border`. No outer double-border. |
| **Totals row** | Bold text. Top border: 1.5pt `accent`. |
| **Width** | Full content width (page width minus left+right margins). For A4 with 1" margins: ~9360 DXA. Use `WidthType.DXA`, never `PERCENTAGE`. |

### Headers & Footers

- **Header**: Document title or section name, left-aligned, 9pt, `text-secondary`. 0.5pt `border` rule below, full width.
- **Footer**: Page number right-aligned, 9pt, `text-secondary`. Plain — no "Page X of Y" unless user asks. 0.5pt `border` rule above.

### Track Changes & Comments

When editing with tracked changes:
- Author name: use "Claude" unless user specifies.
- Insertion runs: apply the theme's body font/size.
- Comment text: 9pt, `text-secondary`.

### Validation

After creating the document, run:
```bash
python scripts/office/validate.py output.docx
```
Fix any schema violations before delivering.

---

## minimax-xlsx

> Target pipeline: XML unpack → edit → repack (zero format loss). Also: `xlsx_reader.py` for reading, `style_audit.py` for verification.

### Sheet Setup

- **Default font**: 正文 typography (Noto Sans SC Regular, 11pt).
- **Default column width**: 12 characters for text columns, 10 for numbers, 8 for dates. Adjust to content.
- **Row height**: Auto. Minimum 15pt for readability.
- **Freeze pane**: Freeze below header row (row 2) and after any index column.

### Header Row (Row 1)

| Property | Value |
|----------|-------|
| Fill | `secondary` (`#16213e`) |
| Font | White, bold, 11pt, 正文 typography |
| Alignment | Center for short labels (< 15 chars), left for long labels |
| Borders | Bottom: 1pt `accent`. Other sides: none. |
| Height | 20pt minimum |
| Auto-filter | Enabled on header row range |

### Data Zone

| Property | Value |
|----------|-------|
| Fill | `background` (white) for odd data rows; `surface` (`#f5f5f7`) for even data rows |
| Font | `text-primary`, regular, 11pt |
| Borders | All cells: 0.5pt `border`, inside and outside |
| Alignment | Numbers: right. Text: left. Dates: center. Headers in data: left, bold. |

### Number Formatting

| Data Type | Format String | Example |
|-----------|--------------|---------|
| Integer | `#,##0` | 12,345 |
| Decimal (2 places) | `#,##0.00` | 12,345.67 |
| RMB | `¥#,##0` | ¥12,345 |
| Percentage | `0.0%` | 12.3% |
| Date | `yyyy-mm-dd` | 2026-06-02 |

### Totals / Summary Row

- Separated from data by one empty row.
- Top border: 1.5pt `accent`.
- Font: Bold, `primary`, 11pt. White fill on `secondary` background.
- Label cell: right-aligned, "合计" or "Total".
- Apply SUM/SUBTOTAL formulas, not hardcoded values.

### Charts

- **Color palette**: `chart-1` through `chart-5` in order.
- **Style**: Flat. No 3D effects. No gradients. White plot background.
- **Gridlines**: Horizontal major only, `border` color, 0.5pt.
- **Legend**: Bottom, unless pie chart (right).
- **Title**: Above chart, 14pt, `primary`, bold.

### Print Layout

- **Paper**: A4 portrait (default). Landscape for tables wider than 10 columns.
- **Margins**: 2 cm all sides (narrower than docx to maximize data area).
- **Header**: Sheet name, left-aligned, 8pt, `text-secondary`.
- **Footer**: Page number, center, 8pt, `text-secondary`. Format: "1 / N".
- **Repeat rows**: Header row on every printed page.
- **Gridlines**: Print, `border` color, thin.

### Validation

After editing, run:
```bash
python scripts/style_audit.py output.xlsx
```
Check: header row fill color, alternate row pattern, number formats, no formula errors.

---

## pptx-generator

> Target engine: PptxGenJS. Reference `references/design-system.md` for mechanics, override colors and fonts from this theme.

### Global Settings

| Property | Value |
|----------|-------|
| Slide size | 16:9 (LAYOUT_16x9, 10" × 5.625") |
| Default font | 正文 typography (Noto Sans SC Regular, 14pt for body) |
| Color format | 6-char hex WITHOUT `#` (PptxGenJS convention) |

### Color Mapping

When PptxGenJS expects hex without `#`:

| Token | PptxGenJS Value |
|-------|-----------------|
| `primary` | `1a1a2e` |
| `secondary` | `16213e` |
| `accent` | `e94560` |
| `background` | `ffffff` |
| `text-secondary` | `6b7280` |

### Slide Layouts

#### Cover Slide (封面)

```
Layout:
┌──────────────────────────────────────┐
│                                      │
│  [Title]                             │  ← 44pt, bold, primary, left-aligned
│  ───────                             │  ← 4pt accent bar, 40% slide width
│                                      │
│  [Subtitle]                          │  ← 18pt, text-secondary, left-aligned
│                                      │
│                                      │
│                        [Date]        │  ← 12pt, text-secondary, bottom-right
│  [Organization]                      │  ← 12pt, text-secondary, bottom-left
└──────────────────────────────────────┘
```

- Title: y = 1.2", x = 0.8". Font: 44pt, bold, `primary`. Max 2 lines.
- Accent bar: 4pt thick, `accent`, 3.5" wide, 0.15" below title baseline.
- Subtitle: 0.15" below accent bar. 18pt, `text-secondary`. Max 1 line.
- Date: bottom-right corner, 0.5" margin.
- Organization: bottom-left corner, 0.5" margin.

#### TOC Slide (目录)

```
Layout:
┌──────────────────────────────────────┐
│  目录                                │  ← 30pt, bold, primary
│  ───────                             │  ← 2pt accent bar
│                                      │
│  01  [Section Name]       ────       │  ← Number: 24pt accent, bold
│  02  [Section Name]       ────       │     Text: 18pt primary
│  03  [Section Name]       ────       │     Leader: dotted to page number
│  04  [Section Name]       ────       │
│                                      │
└──────────────────────────────────────┘
```

- Title: "目录", 30pt, bold, `primary`, y = 0.6", x = 0.8".
- Items: start at y = 1.5". Number in `accent` 24pt bold. Item text in `primary` 18pt.
- Page numbers: right-aligned, 14pt, `text-secondary`.

#### Content Slide (内容)

```
Layout:
┌──────────────────────────────────────┐
│  [Section Title]                     │  ← 30pt, bold, primary
│  ────────────────────────────────    │  ← 0.5pt border rule, full width
│                                      │
│  [Body text goes here. Keep          │  ← 16pt, text-primary
│   generous whitespace around         │     Line spacing: 1.4
│   all content blocks.]               │
│                                      │
│  • Bullet point                      │  ← Bullet: accent 8pt
│  • Bullet point                      │     Text: 16pt primary
│                                      │
└──────────────────────────────────────┘
```

- Title area: 30pt bold `primary`, y = 0.4", x = 0.8". Rule below: 0.5pt `border`, full slide width minus 0.8" margins.
- Body area: start at y = 1.4". 16pt `text-primary`. Max content height: 3.8" from top of body area. If content exceeds, split to next slide.
- Bullets: `accent` "•", indent 0.3", hanging 0.2".

#### Section Divider (章节分隔)

```
Layout:
┌──────────────────────────────────────┐
│                                      │
│                                      │
│           [Section Number]           │  ← 72pt, accent, bold
│           [Section Title]            │  ← 36pt, white, bold
│           ───────────                │  ← 2pt, accent, 2" wide
│                                      │
│                                      │
└──────────────────────────────────────┘
```
Background: full slide `secondary`.

- Section number: 72pt, `accent`, bold, centered vertically at 35%.
- Section title: 36pt, white, bold, 0.2" below number.
- Accent underline: 2pt `accent`, 2" wide, centered, 0.15" below title.

### Tables in Slides

Same color rules as minimax-xlsx, adapted for slide width:

| Element | Style |
|---------|-------|
| Header row | `secondary` fill, white bold 12pt |
| Data rows | White fill, `text-primary` 11pt |
| Alternate rows | `surface` fill |
| Borders | All sides 0.5pt `border` |
| Cell padding | 4pt all sides |

### Charts in Slides

- **Color order**: `chart-1`, `chart-2`, `chart-3`, `chart-4`, `chart-5`.
- **Style**: Flat. No 3D, no gradients, no shadows. White plot background.
- **Gridlines**: Horizontal only, `border` color, 0.5pt.
- **Data labels**: 9pt, `text-secondary`. Show only when there are ≤ 6 data points.
- **Legend**: Bottom, 10pt. Or right if chart is narrow.

### Design Checklist

Before delivering:
- [ ] All hex colors used WITHOUT `#` prefix
- [ ] Cover slide has accent bar, not just text
- [ ] Section dividers between major sections
- [ ] Tables have alternate row shading
- [ ] Chart colors match theme palette
- [ ] No Comic Sans, no clip art, no 3D effects
- [ ] Slide numbers on all non-cover slides (bottom-right, 8pt, `text-secondary`)

---

## pdf

> Used both standalone and as the output format when exporting from docx.

### Page Geometry

- **Size**: A4 (210mm × 297mm) — default. US Letter (215.9mm × 279.4mm) if user specifies.
- **Margins**: Same as docx — 2.54 cm / 1 inch all sides.
- **Orientation**: Portrait default. Landscape for wide tables or appendix.

### From docx Export

When converting docx → pdf via LibreOffice:

```bash
python scripts/office/soffice.py --headless --convert-to pdf document.docx
```

- The docx formatting (colors, fonts, spacing) carries through automatically.
- Verify: page breaks at intended positions, header/footer present, table borders intact.

### Standalone PDF

When generating PDF directly (reportlab or similar):

- Use the theme's `## minimax-docx` rules for heading styles and body text.
- Embed font subsets for Noto Sans SC to ensure CJK rendering on any system.
- Set document metadata:
  - `/Title` — document title
  - `/Author` — from user or "Genius Agent"
  - `/Subject` — document type (report, proposal, etc.)
  - `/Creator` — "MiniMax Document Pipeline"
- No watermarks unless user requests.

### Print Notes

- Color profile: sRGB. Colors will print slightly darker than screen.
- `accent` (`#e94560`) translates well to both digital and print.
- Background colors (`surface`, `secondary`) may not print on grayscale printers — ensure all critical information is in `text-primary`, not color-coded alone.
