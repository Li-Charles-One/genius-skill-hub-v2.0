# 编辑级暗夜 — pptx 工程映射

> 本文件只提供 **tokens → PptxGenJS 参数映射**。设计意图见 `tokens.md`。
> 执行流程由 pptx-generator 自行决策（参考其 `references/design-system.md` 和 `references/slide-types.md`）。

## 全局设置

```js
const pptx = new PptxGenJS();
pptx.defineLayout({ name: "CUSTOM_16x9", width: 10, height: 5.625 });
pptx.layout = "CUSTOM_16x9";
```

| 属性 | 值 |
|------|-----|
| Slide size | `{ width: 10, height: 5.625 }`（16:9） |
| 默认背景 | `"000000"`（纯黑） |
| Color format | **6 位 hex，不带 `#`** |
| 默认字体 | `"Noto Sans SC"` |

## 色彩令牌 → PptxGenJS

```js
const C = {
  accent:         "00A8FF",
  textPrimary:    "FFFFFF",
  textSecondary:  "999999",
  textMuted:      "555555",
  border:         "222222",
  bgCard:         "111111",
  surface:        "161616",
  bgSecondary:    "0A0A0A",
  bgPrimary:      "000000",
};
```

## 字体

| tokens.md 角色 | PptxGenJS `fontFace` | `fontSize` | `bold` | `color` | 备注 |
|---------------|---------------------|-----------|--------|---------|------|
| 封面大标题 | `"Noto Sans SC Thin"` | 56 | `false` | `C.textPrimary` | `letterSpacing: -2` |
| 一级标题 | `"Noto Sans SC Thin"` | 28 | `false` | `C.textPrimary` | `letterSpacing: -1` |
| 二级标题 | `"Noto Sans SC Medium"` | 14 | `false` | `C.textPrimary` | |
| 正文 | `"Noto Sans SC Light"` | 10 | `false` | `C.textSecondary` | `lineSpacingMultiple: 2.0` |
| 小号正文 | `"Noto Sans SC"` | 9 | `false` | `C.textSecondary` | |
| 标签 | `"Noto Sans SC Medium"` | 7 | `false` | `C.accent` | `letterSpacing: 3` |
| 数字展示 | `"Noto Sans SC Thin"` | 32 | `false` | `C.accent` | |
| 脚注/页码 | `"Noto Sans SC"` | 8 | `false` | `C.textMuted` | |

> **PptxGenJS 不支持 `letterSpacing` 属性**。变通：在每个字符间插入空格，或使用 `charSpacing`（如有）。
> 若引擎不支持，忽略 letter-spacing 参数。

## 幻灯片布局

所有坐标单位为 **英寸**。原点为左上角。

### 封面（Cover）

| 元素 | x | y | w | h | fontSize | fontFace | color | 备注 |
|------|---|---|---|---|---------|----------|-------|------|
| TAG LINE | 0.6 | 1.5 | 8.8 | 0.3 | 7 | Medium | `C.accent` | — |
| TITLE | 0.6 | 1.8 | 8.8 | 1.5 | 56 | Thin | `C.textPrimary` | `lineSpacingMultiple: 1.05` |
| 分割线 | 0.6 | 3.3 | 0.48 | 0 | — | — | `C.accent` | `line { w: 1, color: C.accent }` |
| SUBTITLE | 0.6 | 3.4 | 8.8 | 0.7 | 11 | Light | `C.textSecondary` | `lineSpacingMultiple: 1.8` |
| 元信息左 | 0.6 | 4.8 | 3.0 | 0.3 | 8 | — | `C.textMuted` | 日期 |
| 元信息右 | 6.6 | 4.8 | 3.0 | 0.3 | 8 | — | `C.textMuted` | 作者/对齐 |

### 目录（TOC）

| 元素 | x | y | w | h | fontSize | color |
|------|---|---|---|---|---------|-------|
| 标签 | 0.6 | 0.4 | 2.0 | 0.2 | 7 | `C.accent` |
| 章节号 | 0.6 | 1.8+ | 0.8 | 0.6 | 40 | `C.accent`（Thin） |
| 章节名 | 1.6 | 1.8+ | 5.0 | 0.6 | 13 | `C.textPrimary`（Medium） |
| 页码 | 8.5 | 1.8+ | 1.0 | 0.6 | 9 | `C.textMuted` |
| 引导线 | 章节名右 → 页码左 | — | — | — | `C.textMuted`（dotted） |

首项 y = 2.0，项间距 0.6。

### 章节分隔（Section Divider）

背景色：`C.bgSecondary`（`"0A0A0A"`）

| 元素 | x | y | w | h | fontSize | fontFace | color |
|------|---|---|---|---|---------|----------|-------|
| 编号 | center | 2.0 | 1.0 | 1.2 | 80 | Thin | `C.accent` |
| 标题 | center | 3.2 | 6.0 | 0.6 | 26 | Thin | `C.textPrimary` |
| 分割线 | center | 3.8 | 0.64 | 0 | — | — | `C.accent` |

编号和标题 `align: "center"`。分割线 `line { w: 1, color: C.accent }`，居中。

### 内容页（Content）

| 元素 | x | y | w | 备注 |
|------|---|---|---|------|
| 章节标签 | 0.6 | 0.4 | 2.0 | fontSize: 7, fontFace: "Medium", color: `C.accent` |
| 标题 | 0.6 | 0.6 | 8.8 | fontSize: 28, fontFace: "Thin", color: `C.textPrimary`, letterSpacing: -1 |
| 正文 | 0.6 | 1.4 | 6.3 | fontSize: 10, fontFace: "Light", color: `C.textSecondary`, lineSpacingMultiple: 2.0 |
| 要点列表 | 0.6 | 正文后+0.3 | 8.8 | fontSize: 14, fontFace: "Regular", color: `C.textPrimary`, bullet: `{code: "2014"}` accent 色 |

正文最大宽度：slide 宽度的 72%（~7.2 inch）。

### 卡片网格（Card Grid）

| 属性 | 值 |
|------|-----|
| 背景 | `rect { fill: C.bgCard, line: { color: C.border, width: 1 }, rectRadius: 0.06 }` |
| 内边距 | 卡片内文字 x+0.2, y+0.15 |
| 数字 | fontSize: 32, fontFace: "Thin", color: `C.accent` |
| 标题 | fontSize: 11, fontFace: "Medium", color: `C.textPrimary`, bold: false |
| 描述 | fontSize: 8, color: `"777777"` |

3 列布局：卡片宽度 2.6，间距 0.2。起始 x = 0.6。

### 幻灯片内表格

| 元素 | 值 |
|------|-----|
| 整体背景 | `fill: C.bgCard`, `border: { pt: 1, color: C.border }`, `rectRadius: 0.08` |
| 表头行 | `fill: C.border`, `color: C.textPrimary`, fontSize: 9, bold: true |
| 数据行 | `fill: C.bgCard`, `color: C.textPrimary`, fontSize: 8 |
| 分类行 | `fill: rgba(0,168,255, 0.05)`, `color: C.accent`, fontSize: 8, bold: true |
| 合计行 | `border: { pt: 2, color: C.accent }（顶部）`, `color: C.accent`, fontSize: 9, bold: true |
| Cell padding | top/bottom: 12px, left/right: 16px |
| 行间分隔 | `border: { pt: 0.5, color: C.border }`（底部） |

### 图表

| 属性 | 值 |
|------|-----|
| 绘图区 | `fill: C.bgSecondary` |
| 网格线 | 仅水平，`color: "1A1A1A"`, `size: 0.5` |
| 系列颜色 | `[C.accent, C.textPrimary, C.textSecondary, C.textMuted, C.border]` |
| 数据标签 | fontSize: 10, color: `C.textSecondary` |
| 图例 | fontSize: 11, color: `C.textSecondary`, position: `"b"`（底部） |

## 样式配方

主题的 PptxGenJS style recipe（替代 pptx-generator 内置的 Sharp/Soft/Rounded/Pill）：

```js
// 编辑级暗夜 style recipe
const editorialDark = {
  // 卡片默认
  cardFill: C.bgCard,
  cardBorder: { pt: 1, color: C.border },
  cardRadius: 0.06,
  // 分割线
  divider: { w: 1, color: C.accent },
  dividerWide: 0.48,
  // 标题区
  tagSize: 7,
  tagColor: C.accent,
  tagSpacing: 3,
  // 段落
  bodySize: 10,
  bodyColor: C.textSecondary,
  bodyLineSpacing: 36,  // 2.0 × 18pt
  bodyFont: "Noto Sans SC Light",
};
```

## 已知坑位

1. **PptxGenJS color format**：所有颜色为 6 位 hex **不带 `#`**。`"#00a8ff"` → `"00A8FF"`。错误格式会静默失败（渲染为黑色）。

2. **fontFace 不支持变体名**：PptxGenJS 的 `fontFace` 接受任意字符串但 PowerPoint 仅识别已安装字体。如果系统未安装 `"Noto Sans SC Thin"`，PowerPoint 会回退到默认字体。确保目标机器已安装 Noto Sans SC 全套变体。

3. **letter-spacing 无直接 API**：PptxGenJS `textProps` 无 `letterSpacing`。忽略此参数；如果关键（封面大标题），手动在字符间插入空格。

4. **暗色背景 + 导出**：全黑幻灯片在投影仪上效果最佳，但在打印/导出 PDF 时墨水消耗大。如需打印版，将 `bgPrimary` 改为 `"FFFFFF"`，`textPrimary` 改为 `"000000"`。

5. **数字展示的等宽对齐**：PptxGenJS 不支持 tabular-nums。数字列用 `align: "right"` 对齐即可。

## 校验清单

- [ ] slide size 为 16:9（10" × 5.625"）
- [ ] 所有颜色值无 `#` 前缀
- [ ] 封面/内容/章节分隔三套布局分别实现
- [ ] 表格有自定义边框（非默认样式）
- [ ] 图表颜色顺序为 `[accent, textPrimary, textSecondary, textMuted, border]`
- [ ] 页码右下角（x: 9.3, y: 5.1），8pt `C.textMuted`
- [ ] 无 Comic Sans、无剪贴画、无 3D 图表效果
