# 编辑级暗夜 — docx 工程映射

> 本文件只提供 **tokens → OpenXML 参数映射**。设计意图见 `tokens.md`。
> 执行流程由 minimax-docx 自行决策。

## 工程基线

| 属性 | 值 |
|------|-----|
| 基准菜谱 | 无。从零构建（内置菜谱均为白底方案，本主题为明暗双模，不宜基于任何现有菜谱） |
| 页面尺寸 | A4: `Width=11906, Height=16838`（DXA） |
| 默认语言 | `Val="en-US", EastAsia="zh-CN"` |

## 设计令牌 → OpenXML 映射

### RunFonts 三段式

本主题 CJK 字体为 Noto Sans SC 系列，Latin 为 Inter：

```csharp
new RunFonts {
    Ascii = "Inter",           // 拉丁字符
    HighAnsi = "Inter",        // 高位 ANSI（西欧符号）
    EastAsia = "{variant}",    // CJK 变体名，见下方映射
    ComplexScript = "Inter"    // 复杂脚本（阿拉伯/泰文等）
}
```

**字重 → EastAsia 变体名**（关键：Word 不识别可变字重，必须用精确变体名）：

| tokens.md 字重 | 变体名 | `Bold` / `BoldComplexScript` |
|---------------|--------|------------------------------|
| 200 (Thin) | `"Noto Sans SC Thin"` | `false` |
| 300 (Light) | `"Noto Sans SC Light"` | `false` |
| 400 (Regular) | `"Noto Sans SC"` | `false` |
| 500-600 (Medium) | `"Noto Sans SC Medium"` | `false` |
| ≥700 (Bold) | `"Noto Sans SC"` | `Bold=true, BoldComplexScript=true` |

### 色彩令牌

| tokens.md | OpenXML `Color.Val` | 用途 |
|-----------|--------------------|------|
| `bg-primary` | `"000000"` | Shading.Fill（封面/分隔页背景） |
| `bg-secondary` | `"0a0a0a"` | Shading.Fill（次级暗色） |
| `bg-card` | `"111111"` | Shading.Fill（卡片/信息块） |
| `border` | `"222222"` | Border.Color（表格边框） |
| `accent` | `"00a8ff"` | Color.Val（强调文字、分割线） |
| `text-primary` | `"ffffff"` | Color.Val（暗底文字） |
| `text-secondary` | `"999999"` | Color.Val（副标题） |
| `text-muted` | `"555555"` | Color.Val（脚注） |

正文区（明底）文字色：`"000000"`（纯黑，打印优化）。

### 间距令牌

| tokens.md | OpenXML | DXA 值 |
|-----------|---------|--------|
| 页边距 | `PageMargin { Top, Bottom, Left, Right }` | `907`（48px ≈ 1.27cm） |
| 段后间距 | `SpacingBetweenLines.After` | `120`（6pt） |
| 正文行高 | `SpacingBetweenLines.Line` + `LineRule.Auto` | `480`（2.0 × 240） |
| 标题上间距（封面） | `SpacingBetweenLines.Before` | `1701`（~120px） |
| 标题上间距（正文内） | `SpacingBetweenLines.Before` | `454`（~32px） |
| 标题下间距 | `SpacingBetweenLines.After` | `227`（~16px） |
| 表格 cell padding（上下） | `TableCellMarginDefault { TopMargin, BottomMargin }` | `60` |
| 表格 cell padding（左右） | `TableCellMarginDefault { StartMargin, EndMargin }` | `120` |
| 卡片内边距 | `TableCellMarginDefault` 或 paragraph margin | `340-510`（24-36px） |

## 文档结构

本主题使用**两节（section）**结构：

```
Section 0: 封面（暗底 #000000）
  ├── sectPr { type="nextPage" }
Section 1: 正文（白底 #ffffff）→ 可以有多页
  ├── sectPr（最后一个 child）
```

**封面 sectPr**：
```csharp
new SectionProperties(
    new PageSize { Width = 11906, Height = 16838 },
    new PageMargin { Top = 907, Bottom = 907, Left = 907, Right = 907,
                     Header = 510, Footer = 510, Gutter = 0 },
    // 封面背景：在第一个 paragraph 的 pPr 里用 Shading Fill="000000"
    new SectionType { Val = SectionMarkValues.NextPage }
)
```

**正文 sectPr**（白底正常打印）：
```csharp
new SectionProperties(
    new PageSize { Width = 11906, Height = 16838 },
    new PageMargin { Top = 907, Bottom = 907, Left = 907, Right = 907,
                     Header = 510, Footer = 510, Gutter = 0 }
)
```

## 段落样式参数

### DocDefaults

```csharp
new DocDefaults(
    new RunPropertiesDefault(new RunPropertiesBaseStyle(
        new RunFonts { Ascii = "Inter", HighAnsi = "Inter",
                       EastAsia = "Noto Sans SC Light", ComplexScript = "Inter" },
        new FontSize { Val = "20" },           // 10pt body
        new FontSizeComplexScript { Val = "20" },
        new Color { Val = "000000" },
        new Languages { Val = "en-US", EastAsia = "zh-CN" }
    )),
    new ParagraphPropertiesDefault(new ParagraphPropertiesBaseStyle(
        new SpacingBetweenLines {
            Line = "480",                      // 2.0 line spacing
            LineRule = LineSpacingRuleValues.Auto,
            After = "120"                      // 6pt after
        }
    ))
)
```

### Heading 样式

| StyleId | `w:sz` (half-pts) | 字号 | Color | 字体变体 | Bold | Before (DXA) | After (DXA) | LetterSpacing | OutlineLevel |
|---------|-------------------|------|-------|---------|------|-------------|-------------|---------------|--------------|
| `Heading1` | `"64"` | 32pt | `"000000"` | Thin | false | `"454"` | `"227"` | `20` | `0` |
| `Heading2` | `"32"` | 16pt | `"000000"` | Medium | false | `"240"` | `"113"` | `10` | `1` |
| `Heading3` | `"28"` | 14pt | `"000000"` | Medium | false | `"200"` | `"113"` | `10` | `2` |

> **LetterSpacing 实现**: 在 `StyleParagraphProperties` 中不直接支持。替代方案：每个 Heading paragraph 的 `RunProperties` 中设置 `Spacing = 20`（单位：twips）。

### 封面段落

| 角色 | sz | 变体 | Color | Spacing | 位置 |
|------|-----|------|-------|---------|------|
| 标签行 | `"14"` (7pt) | Medium | `"00a8ff"` | After=`"60"` | y ≈ 30%（用段前 spacing 控制） |
| 标题 | `"72"` (36pt) | Thin | `"ffffff"` | Line=`"252"` (1.05), After=`"60"` | 紧随标签 |
| 分割线 | — | — | — | BottomBorder: Single, Size=8, Color=`"00a8ff"`, 右缩进 `"7200"` | 空段落 + border |
| 副标题 | `"20"` (10pt) | Light | `"999999"` | Line=`"432"` (1.8) | 分割线后 |

### 章节入口段落

每个大章节开头：

| 元素 | sz | 变体 | Color | Before | After |
|------|-----|------|-------|--------|-------|
| 分割线 | — | — | — | Before=`"240"` | — |
| 章节标签 | `"20"` (10pt) | Medium | `"00a8ff"` | — | `"40"` |
| 章节标题 | `"56"` (28pt) | Thin | `"000000"` | — | `"113"` |
| 章节导语 | `"24"` (12pt) | Regular | `"999999"` | — | `"200"` |

分割线实现：段落 `pPr` → `ParagraphBorders { BottomBorder { Val=Single, Size=8, Color="00a8ff", Space=0 } }`，段落只含一个 `w:r` 带一个 space 字符或空 `w:t`。右缩进 `"7200"`（~5 inch）。

### Body Text

| 属性 | 值 |
|------|-----|
| StyleId | `"Normal"` |
| `w:sz` | `"20"` (10pt) |
| EastAsia | `"Noto Sans SC Light"` |
| Line | `"480"` (2.0) |
| After | `"120"` (6pt) |
| 首行缩进 | 无 |
| 行内强调 | 不用 Bold。在 RunProperties 中设 `Color Val="00a8ff"` |

### 列表

| 属性 | 值 |
|------|-----|
| 标记 | 不用标准 bullet。段落开头插入 `w:r` → `w:t Text="— "` 或 `"· "`，设 `Color="00a8ff"` |
| 左缩进 | `Indentation { Left = "480" }`（~24px） |
| 段间间距 | After=`"160"` (8pt) |
| 嵌套缩进 | 再加 `"480"`，标记色改为 `"555555"` |

## 表格参数

### 表格属性

```csharp
new TableProperties(
    new TableWidth { Width = "5000", Type = TableWidthUnitValues.Pct },
    new TableBorders(
        new TopBorder { Val = BorderValues.Single, Size = 4, Space = 0, Color = "e8e8e8" },
        new BottomBorder { Val = BorderValues.Single, Size = 4, Space = 0, Color = "e8e8e8" },
        new LeftBorder { Val = BorderValues.Single, Size = 4, Space = 0, Color = "e8e8e8" },
        new RightBorder { Val = BorderValues.Single, Size = 4, Space = 0, Color = "e8e8e8" },
        new InsideHorizontalBorder { Val = BorderValues.Single, Size = 4, Space = 0, Color = "e8e8e8" },
        new InsideVerticalBorder { Val = BorderValues.Single, Size = 4, Space = 0, Color = "e8e8e8" }
    ),
    new TableCellMarginDefault(
        new TopMargin { Width = "60", Type = TableWidthUnitValues.Dxa },
        new BottomMargin { Width = "60", Type = TableWidthUnitValues.Dxa },
        new StartMargin { Width = "120", Type = TableWidthUnitValues.Dxa },
        new EndMargin { Width = "120", Type = TableWidthUnitValues.Dxa }
    )
)
```

### 表头行

| 属性 | 值 |
|------|-----|
| Shading.Fill | `"222222"` |
| Color | `"ffffff"` |
| w:sz | `"18"` (9pt) |
| EastAsia | `"Noto Sans SC Medium"` |
| 底部边框 | BorderValues.Single, Size=12, Color=`"00a8ff"` |
| 其余三边 | BorderValues.Single, Size=4, Color=`"333333"` |

### 数据行

| 属性 | 值 |
|------|-----|
| Shading.Fill | `"ffffff"` |
| Color | `"000000"` |
| w:sz | `"18"` (9pt) |
| EastAsia | `"Noto Sans SC Light"` |
| 四边边框 | BorderValues.Single, Size=4, Color=`"e8e8e8"` |
| 数字列对齐 | JustificationValues.Right |
| 文本列对齐 | JustificationValues.Left |

### 分类行

| 属性 | 值 |
|------|-----|
| Shading.Fill | `"f4f9ff"` |
| Color | `"00a8ff"` |
| w:sz | `"18"` (9pt) |
| EastAsia | `"Noto Sans SC Medium"` |
| 合并 | `HorizontalMerge` + `GridSpan` 覆盖整行 |

### 合计行

| 属性 | 值 |
|------|-----|
| 顶部边框 | BorderValues.Single, Size=12, Color=`"00a8ff"` |
| Color | `"00a8ff"` |
| w:sz | `"20"` (10pt) |
| EastAsia | `"Noto Sans SC Medium"` |

## 页码

```csharp
// 封面 section：无页码
// 正文 section：右下角页码
new Footer(
    new Paragraph(
        new ParagraphProperties { Justification = JustificationValues.Right },
        new Run(
            new RunProperties {
                new RunFonts { Ascii = "Inter", EastAsia = "Noto Sans SC", HighAnsi = "Inter" },
                new FontSize { Val = "20" },       // 10pt
                new Color { Val = "555555" }
            },
            // PageNumber field — use SimpleField or FieldCode + FieldChar pattern
        )
    )
)
```

## 已知坑位

1. **Noto Sans SC 变体名**：Word 不解析可变字重。`RunFonts.EastAsia` 必须写完整变体名（`"Noto Sans SC Thin"`），不能用 `"Noto Sans SC"` + `Bold=false` 替代。名称不带空格/连字符则 Word 退化为 Regular。

2. **暗色封面 sectPr 独立**：封面和正文必须在不同 section。如果封面和正文共用一个 section，正文也会继承暗底。

3. **element order**：`w:p` 内 `pPr` 必须在 runs 之前；`w:r` 内 `rPr` 必须在 `w:t` 之前；`w:body` 内 `sectPr` 必须是最后一个 child。不遵守会导致 Word 报"文件已损坏"。

4. **分割线用 bottom-border，不用 shape**：封面和章节入口的分割线用段落 bottom-border 实现（`pPr → ParagraphBorders → BottomBorder`），不要用 `w:drawing` 插入线条 shape。后者在某些 Word 版本中不显示。

5. **直接格式污染**：从其他文档复制内容时，剥离所有 inline `rPr`（字体、颜色）和 `pPr`（边框、底纹、间距），只保留 `pStyle` 引用和 `w:t` 文本。表格内也要清理。

## 校验清单

生成文档后检查：
- [ ] `Heading1/2/3` 样式包含 `OutlineLevel`
- [ ] 字体无直接格式污染（所有 run 仅引用 styleId，无 inline font/color）
- [ ] 封面和正文分属两个 section
- [ ] 表格边框为自定义（非 Word 默认网格线）
- [ ] `sectPr` 是 `w:body` 的最后一个 child
- [ ] 页面尺寸 A4（11906×16838 DXA）
