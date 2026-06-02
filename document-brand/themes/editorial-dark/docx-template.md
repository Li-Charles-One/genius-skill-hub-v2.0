# 编辑级暗夜 — minimax-docx 模板

> 使用 OpenXML SDK。本主题在 docx 中采用**明底为主 + 暗色封面/分隔页**策略——正文白底黑字保证可打印，封面和章节页用暗底制造冲击。
>
> 使用前先读取 `tokens.md` 获取色彩、字体、间距令牌。

### Page Setup

- **Page size**: A4 (210mm × 297mm)。
- **Margins**: 48px（约 1.27cm / 0.5 inch）四边。比传统 1 inch 窄，留白靠内容呼吸而非页边。
- **Header/Footer**: 不设页眉页脚横线。页码右下角，10pt，`text-muted`。

### Title Page

```
┌──────────────────────────────────────┐
│                                      │
│  [Tag line]                          │  ← 7pt, accent, letter-spacing 3px
│                                      │
│  [TITLE]                             │  ← 36pt, Noto Sans SC Thin, black
│  ──                                  │  ← accent 分割线（bottom-border 段落，右缩进）
│                                      │
│  [Subtitle]                          │  ← 10pt, Noto Sans SC Light, text-secondary
│                                      │
└──────────────────────────────────────┘
```

- 标签行：y ≈ 30%，7pt，`accent`，letter-spacing 3px。
- 标题：y 紧随标签，36pt，Noto Sans SC Thin。不超过两行。行高 1.05。
- 分割线：标题下方，`accent` 色。实现方式：空段落 + bottom-border + 右缩进（不做成全宽线）。
- 副标题：分割线下方，10pt，Noto Sans SC Light，`text-secondary`，最多三行，行高 1.8。
- 封面不需要日期和署名——保持干净。如需元信息，放到正文页的页脚或副标题中。

### Heading Styles (正文页)

正文页为白底（`#ffffff`），黑字（`#000000`）。

| Style ID | Font | Size | Color | Weight | Spacing | Extra |
|----------|------|------|-------|--------|---------|-------|
| `Heading1` | 一级标题 typography | 32pt | `#000000` | 200 | 120px before, 16px after | Letter-spacing 1px。左对齐。 |
| `Heading2` | 二级标题 typography | 16pt | `#000000` | 600 | 48px before, 8px after | Letter-spacing 0.5px。左对齐。 |
| `Heading3` | 三级标题 typography | 14pt | `#000000` | 500 | 32px before, 8px after | Letter-spacing 0.5px。左对齐。 |

每章节入口：
```
┌─ 48px accent 分割线
│  01 章节标签         ← 10pt, accent, letter-spacing 4px
│  章节标题             ← 32pt, weight 200
│  章节导语             ← 14pt, text-secondary, 最多 2 行
```

### Body Text

- 默认段落：10pt，Noto Sans SC Light，`#000000`，行高 2.0。无首行缩进。
- **段落间距**：段后 6pt，不用整行空行。段落之间靠段后间距区分，保持紧凑的编辑节奏。
- 行内强调用 `accent` 色（`#00a8ff`），不用加粗。

### Tables

| Element | Style |
|---------|-------|
| **整体** | 全宽（页面宽度）。所有单元格四边有 1px 边框。 |
| **表头行** | `#222222` 背景。`#ffffff` 文字，9pt，Noto Sans SC Medium。padding 上下 60 DXA，左右 120 DXA。 |
| **数据行** | 白底。`#000000` 文字，9pt，Noto Sans SC Light。padding 上下 60 DXA，左右 120 DXA。 |
| **行分隔** | 每个单元格四边 1px `#e8e8e8`。表头边框用 `#333`，底部 2px `accent`。 |
| **分类行** | `#f4f9ff` 背景。`accent` 文字，9pt，Noto Sans SC Medium。合并整行为一列。 |
| **合计行** | 顶部 2px `accent`。`accent` 文字，10pt，Noto Sans SC Medium。 |
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
