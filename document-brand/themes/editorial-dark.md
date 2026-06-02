# 编辑级暗夜 (Editorial Dark)

> 克制、锋利、沉浸。纯黑画布上，蓝色光标是唯一的信号。小字号、大留白、细分割线——这不是装饰，是编辑意志。

---

## Design Tokens

### Colors

| Token | Hex | Preview | Role |
|-------|-----|---------|------|
| `bg-primary` | `#000000` | ■ | 封面背景、PPT 暗色底、章节分隔页 |
| `bg-secondary` | `#0a0a0a` | ■ | 次级暗色区域 |
| `bg-card` | `#111111` | ■ | 卡片底色 |
| `surface` | `#161616` | ■ | 表格隔行、侧栏 |
| `border` | `#222222` | ■ | 分割线、表格边框 |
| `accent` | `#00a8ff` | ■ | 唯一强调色：链接、关键数据、图表高亮 |
| `accent-dim` | `rgba(0,168,255,0.15)` | ░ | 淡化强调（hover 态、弱标记） |
| `text-primary` | `#ffffff` | ■ | 正文（暗底上） |
| `text-secondary` | `#999999` | ■ | 说明文字、副标题 |
| `text-muted` | `#555555` | ■ | 元信息、脚注、非活跃态 |
| `chart-1` | `#00a8ff` | ■ | 图表系列 1 |
| `chart-2` | `#ffffff` | ■ | 图表系列 2 |
| `chart-3` | `#999999` | ■ | 图表系列 3 |
| `chart-4` | `#555555` | ■ | 图表系列 4 |
| `chart-5` | `#222222` | ■ | 图表系列 5 |

**明暗双模**：打印文档（docx/xlsx）不能全黑底 → 暗色用于封面和分隔页，正文区切换为白底黑字。PPT 和 PDF 可全暗。

| 模式 | 背景 | 正文色 | 使用场景 |
|------|------|--------|----------|
| 🌑 暗底 | `#000000` / `#0a0a0a` | `#ffffff` | PPT 全部、封面页、章节分隔、标题栏 |
| 🌕 明底 | `#ffffff` | `#000000` | docx 正文、xlsx 数据区、打印输出 |
| 🌓 卡片 | `#111111` | `#ffffff` | 表格、信息块、侧边栏 |

### Typography

字体栈与参考网页完全一致：

| Role | Font Stack | Weight | Size | Line Height | Letter Spacing |
|------|-----------|--------|------|-------------|----------------|
| 封面大标题 | Noto Sans SC, Inter, PingFang SC, sans-serif | 200 | 48–96pt | 1.05 | -2px |
| 一级标题 | Noto Sans SC, Inter, PingFang SC, sans-serif | 200 | 32–48pt | 1.2 | -1px |
| 二级标题 | Noto Sans SC, Inter, PingFang SC, sans-serif | 600 | 16pt | 1.3 | 0 |
| 三级标题 | Noto Sans SC, Inter, PingFang SC, sans-serif | 500 | 14pt | 1.3 | 0 |
| 正文 | Noto Sans SC, Inter, PingFang SC, sans-serif | 300 | 13pt | 1.8 | 0 |
| 小号正文 | Noto Sans SC, Inter, PingFang SC, sans-serif | 400 | 12pt | 1.6 | 0 |
| 说明/脚注 | Noto Sans SC, Inter, PingFang SC, sans-serif | 400 | 11pt | 1.6 | 1px |
| 标签/元信息 | Noto Sans SC, Inter, PingFang SC, sans-serif | 500 | 10pt | 1.4 | 2–4px |
| 数据/代码 | JetBrains Mono, Consolas, monospace | 400 | 12pt | 1.5 | 0 |
| 数字展示 | Noto Sans SC, Inter, PingFang SC, sans-serif | 200 | 36–48pt | 1.0 | -1px |

### Spacing

| Token | Value |
|-------|-------|
| 页边距 | 48px / 1.27cm（比传统 1 inch 窄，更现代） |
| 段落间距 | 无段后间距——用空白行（1 倍行高）分隔段落 |
| 正文行高 | 1.8（松散、可呼吸） |
| 标题上间距 | 120px（docx 封面）/ 32px（正文内） |
| 标题下间距 | 16px |
| 表格单元格内边距 | 上下 12px，左右 16px |
| 卡片内边距 | 24–36px |
| 章节间距 | 120px（PPT 章节间）/ 48px（docx 章节间） |

---

## minimax-docx

> 使用 OpenXML SDK。本主题在 docx 中采用**明底为主 + 暗色封面/分隔页**策略——正文白底黑字保证可打印，封面和章节页用暗底制造冲击。

### Page Setup

- **Page size**: A4 (210mm × 297mm)。
- **Margins**: 48px（约 1.27cm / 0.5 inch）四边。比传统 1 inch 窄，留白靠内容呼吸而非页边。
- **Header/Footer**: 不设页眉页脚横线。页码右下角，10pt，`text-muted`。

### Title Page

```
┌──────────────────────────────────────┐
│                                      │
│  [Tag line]                          │  ← 10pt, accent, letter-spacing 4px
│                                      │
│  [TITLE]                             │  ← 48pt, weight 200, text-primary
│  ──                                  │  ← 48px accent 分割线
│                                      │
│  [Subtitle]                          │  ← 16pt, weight 300, text-secondary
│                                      │
│                                      │
│                         [Date]       │  ← 11pt, text-muted
│  [Author / Org]                      │  ← 11pt, text-muted
└──────────────────────────────────────┘
```

- 整页 `bg-primary`（`#000000`）背景——在 docx 中通过 Insert > Shapes 全页黑色矩形实现。
- 标签行：y = page height × 30%，10pt，`accent`，letter-spacing 4px，全大写或中文标签。
- 标题：y 紧随标签，48pt（可缩放到 96pt），weight 200（极细），letter-spacing -2px。不超过两行。行高 1.05。
- 分割线：标题下方 24px。`accent` 色，48px 宽，1px 高。
- 副标题：分割线下方 16px。16pt，weight 300，`text-secondary`，最多三行，行高 1.8。
- 底部信息：页面底边距 48px 处。左侧作者，右侧日期。11pt，`text-muted`。

### Heading Styles (正文页)

正文页为白底（`#ffffff`），黑字（`#000000`）。

| Style ID | Font | Size | Color | Weight | Spacing | Extra |
|----------|------|------|-------|--------|---------|-------|
| `Heading1` | 一级标题 typography | 32pt | `#000000` | 200 | 120px before, 16px after | Letter-spacing -1px。左对齐。 |
| `Heading2` | 二级标题 typography | 16pt | `#000000` | 600 | 48px before, 8px after | 无下划线。左对齐。 |
| `Heading3` | 三级标题 typography | 14pt | `#000000` | 500 | 32px before, 8px after | 左对齐。 |

每章节入口：
```
┌─ 48px accent 分割线
│  01 章节标签         ← 10pt, accent, letter-spacing 4px
│  章节标题             ← 32pt, weight 200
│  章节导语             ← 14pt, text-secondary, 最多 2 行
```

### Body Text

- 默认段落：13pt，weight 300，`#000000`，行高 1.8。无首行缩进。
- **段落间不用段后间距**——用一整行空行（¶）分隔。这是编辑级排版的标志：段落是一个个呼吸单元。
- 行内强调用 `accent` 色（`#00a8ff`），不用加粗。

### Tables

| Element | Style |
|---------|-------|
| **整体** | 全宽（页面宽度）。无外边框。 |
| **表头行** | `bg-primary`（`#000000`）背景。`text-primary`（`#ffffff`）文字，12pt，weight 500。上下 padding 12px，左右 16px。 |
| **数据行** | 白底。`#000000` 文字，12pt，weight 300。上下 padding 10px，左右 16px。 |
| **行分隔** | 仅底部 1px `border`（`#222222`）。无竖线。 |
| **分类行** | `accent-dim`（`rgba(0,168,255,0.08)`）背景。`accent` 文字，12pt，weight 600。 |
| **合计行** | 顶部 2px `accent`。`accent` 文字，13pt，weight 600。 |
| **数字列** | 右对齐。tabular-nums。 |
| **文本列** | 左对齐。 |

### Section Dividers (暗色过渡页)

类似封面——全页 `bg-primary` 背景。用于大章节之间的分隔：
- 章节编号：居中，72pt，weight 200，`accent`，y = 40%。
- 章节标题：编号下方 16px，居中，36pt，weight 200，`text-primary`。
- 1px `accent` 分割线，居中，2 inch 宽。

### Lists

- 不用标准 bullet。用 `accent` 短线 "—" 或 "·" 作为标记，缩进 24px。
- 列表项间距：8px。
- 嵌套列表缩进再加 24px，标记改用 `text-muted` "·"。

---

## minimax-xlsx

> 本主题的 xlsx 明底策略：白底黑字数据区 + 黑色表头 + 蓝色强调。表格不是装饰品，是信息本身。

### Sheet Setup

- **默认字体**: 小号正文 typography（Noto Sans SC, 12pt, weight 400）。
- **默认列宽**: 14 字符（文本列），11 字符（数字列），8 字符（日期列）。根据内容调整。
- **默认行高**: 24pt。
- **Freeze**: 冻结表头行 + 首列（如有索引列）。
- **Gridlines**: 关闭 Excel 默认灰色网格线——用自定义边框代替。

### Header Row

| Property | Value |
|----------|-------|
| Fill | `bg-primary` (`#000000`) |
| Font | `text-primary` (`#ffffff`), 12pt, weight 500 |
| Letter Spacing | 2px（通过字符间距设置） |
| Alignment | 左对齐 |
| Height | 32pt |
| Bottom Border | 2px `accent` (`#00a8ff`) |
| Auto-filter | 启用 |

### Data Zone

| Property | Value |
|----------|-------|
| Fill | 白底 (`#ffffff`) |
| Font | `#000000`, 12pt, weight 300 |
| Row Height | 24pt |
| Borders | 仅底部：1px `#eeeeee`（极浅灰，比 `border` 更淡）。无竖线。 |
| Alignment | 文本左对齐，数字右对齐，日期居中 |

### Category Rows (分类行)

用于数据分组（如按部门、按季度）：

| Property | Value |
|----------|-------|
| Fill | `#f5f9ff`（极浅蓝，对应 `accent-dim`） |
| Font | `accent` (`#00a8ff`), 12pt, weight 600 |
| Height | 28pt |
| Bottom Border | 1px `#e0e0e0` |

### Totals Row

| Property | Value |
|----------|-------|
| Top Border | 2px `accent` |
| Fill | `#fafafa` |
| Font | `#000000`, 13pt, weight 600 |
| Height | 32pt |

### Number Formatting

与 极简商务 一致：
- 整数：`#,##0`
- 小数：`#,##0.00`
- 人民币：`¥#,##0`
- 百分比：`0.0%`

### Charts

- **Style**: 扁平。无 3D。无渐变。白色绘图区。
- **Gridlines**: 仅水平主网格线，`#f0f0f0`，0.5pt。
- **Color order**: `chart-1` 到 `chart-5`。
- **Data labels**: 10pt，`text-muted`。数据点 ≤ 6 时显示。
- **Legend**: 底部，11pt。

### Print Layout

- **Paper**: A4 纵向（默认）。> 10 列用横向。
- **Margins**: 1.27cm 四边。
- **Header**: 文件名，左对齐，8pt，`text-muted`。
- **Footer**: 页码 "1 / N"，居中，8pt，`text-muted`。
- **Repeat header row**: 每页重复。
- **Gridlines**: 打印时使用自定义边框（Excel 默认网格线关闭）。

---

## pptx-generator

> 这是本主题的**主战场**——全暗底 PPT，跟参考网页的 UI 语言完全一致。PptxGenJS 引擎。

### Global Settings

| Property | Value |
|----------|-------|
| Slide size | 16:9（LAYOUT_16x9, 10" × 5.625"） |
| Default background | `bg-primary` (`#000000`) |
| Default font | Noto Sans SC, Inter, PingFang SC |
| Color format | 6-char hex WITHOUT `#` |

### Color Mapping (PptxGenJS)

| Token | Value |
|-------|-------|
| `accent` | `00a8ff` |
| `text-primary` | `ffffff` |
| `text-secondary` | `999999` |
| `text-muted` | `555555` |
| `border` | `222222` |
| `bg-card` | `111111` |
| `surface` | `161616` |

### Slide Layouts

#### Cover (封面)

```
全屏 #000000
┌──────────────────────────────────────┐
│                                      │
│  [TAG LINE]                         │  ← 10pt, accent, letter-spacing 4px
│                                      │     y = 24%, x = 48px
│  [TITLE]                            │  ← 72pt, weight 200, #ffffff
│                                      │     letter-spacing -2px, line-height 1.05
│  ──                                 │  ← accent 分割线, 64px wide, 1px
│                                      │
│  [Subtitle]                         │  ← 18pt, weight 300, #999999
│                                      │     line-height 1.8, max 2 lines
│                                      │
│                                      │
│  [Date]                  [Author]   │  ← 11pt, #555555, bottom 48px
└──────────────────────────────────────┘
```

#### TOC (目录)

```
全屏 #000000
┌──────────────────────────────────────┐
│  ──                                 │  ← accent 分割线, 48px
│  目录                               │  ← 10pt, accent, letter-spacing 4px
│                                      │
│  01  [Section]           ······ 03  │  ← Number: 48pt, weight 200, accent
│  02  [Section]           ······ 05  │     Label: 16pt, weight 500, #ffffff
│  03  [Section]           ······ 08  │     Page num: 13pt, #555555, right
│  04  [Section]           ······ 12  │     Dotted leader between
│  05  [Section]           ······ 15  │
│                                      │     y = 20%, items start at y = 35%
└──────────────────────────────────────┘
```

#### Section Divider (章节分隔)

```
全屏 #0a0a0a (bg-secondary)
┌──────────────────────────────────────┐
│                                      │
│                                      │
│              02                      │  ← 96pt, weight 200, accent
│          [Section Title]             │  ← 36pt, weight 200, #ffffff
│              ───                     │  ← accent 分割线, 2px × 80px, 居中
│                                      │
│                                      │
└──────────────────────────────────────┘
```

#### Content (内容)

```
全屏 #000000
┌──────────────────────────────────────┐
│  ──                                 │  ← accent 分割线, 48px, x = 48px
│  02  章节标签                        │  ← 10pt, accent, letter-spacing 4px
│                                      │
│  [Slide Title]                      │  ← 40pt, weight 200, #ffffff
│                                      │     letter-spacing -1px
│                                      │
│  [Body text body text body text     │  ← 16pt, weight 300, #999999
│   body text body text body text     │     line-height 1.8
│   body text body text.]             │     max-width: 80% slide width
│                                      │
│  — Point one                        │  ← 14pt, weight 400, #ffffff
│  — Point two                        │     短线标记, accent 色
│  — Point three                      │
│                                      │
└──────────────────────────────────────┘
```

#### Card Grid (卡片网格)

用于展示多个并列信息块（参考网页的 position-grid）：

```
全屏 #000000
┌──────────────────────────────────────┐
│  ──  03  关键数据                    │
│                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────┐ │
│  │ 50×      │ │ 0%       │ │ v8   │ │  ← #111111 背景
│  │ 更多迭代 │ │ 零废料   │ │ 正确 │ │     #222222 边框
│  │          │ │          │ │ 答案 │ │     8px 圆角
│  │ desc...  │ │ desc...  │ │ desc │ │     数字: 48pt weight 200 accent
│  └──────────┘ └──────────┘ └──────┘ │     标题: 16pt weight 600 #ffffff
│                                      │     描述: 13pt #999999
└──────────────────────────────────────┘
```

#### Tables in Slides

| Element | Style |
|---------|-------|
| Background | `bg-card` (`#111111`) with 1px `border` (`#222222`), 8px radius |
| Header row | `bg-primary` (`#000000`), white 12pt weight 500 |
| Data rows | `#111111` bg. `#ffffff` text, 11pt weight 300. 底部 1px `#222222` |
| Category row | `accent-dim` bg, `accent` text |
| Totals | 顶部 2px `accent`, `accent` text, bold |
| Cell padding | 10px top/bottom, 14px left/right |

#### Charts

- **Style**: 扁平。无 3D。暗色绘图区（`#0a0a0a`）。
- **Gridlines**: 仅水平，`#1a1a1a`，0.5pt。
- **Palette**: `00a8ff`, `ffffff`, `999999`, `555555`, `222222`
- **Data labels**: 10pt, `#999999`。
- **Legend**: 底部，11pt, `#999999`。

### Design Checklist

- [ ] 所有幻灯背景为 `#000000` 或 `#0a0a0a`
- [ ] 每页顶部有 48px accent 分割线（封面和分隔页除外）
- [ ] 章节标签 10pt accent letter-spacing 4px
- [ ] 标题 weight 200（极细），非粗体
- [ ] 正文 weight 300，`#999999`，行高 1.8
- [ ] 数字展示用 weight 200 + accent 色
- [ ] 卡片使用 `#111111` 背景 + `#222222` 边框 + 8px 圆角
- [ ] 表格无竖线，仅底部横线
- [ ] 无 Comic Sans、无剪贴画、无 3D 效果
- [ ] 页码右下角，10pt `#555555`

---

## pdf

### From docx Export

docx 导出 PDF 时，暗色封面和分隔页直接转为 PDF 暗色页面——这在本主题中是**有意为之**的设计选择，不是 bug。

```bash
python scripts/office/soffice.py --headless --convert-to pdf document.docx
```

### Standalone PDF

- **Page size**: A4。US Letter 如需。
- **Margins**: 48px（1.27cm）四边。
- **Font embedding**: 嵌入 Noto Sans SC 子集。
- **Metadata**: Title / Author / Subject / Creator = "MiniMax Document Pipeline"。
- **暗色页面**: 封面和章节分隔页使用 `#000000` 背景——接受打印时的墨水消耗作为设计代价。

### Print Notes

- 暗色页面在屏幕上效果最佳。如需大量打印，考虑提供"打印版"——封面转为白底 + 黑色标题 + accent 分割线，去掉全页黑底。
- 正文页白底黑字，正常打印无额外墨水消耗。
