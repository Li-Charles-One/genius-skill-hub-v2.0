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

字体栈与参考网页完全一致。**重要**：Noto Sans SC 是可变字体，必须按字重选择具体变体名，否则 Word 只会渲染 Regular。

| Role | Font (CJK) | Weight | Size | Line Height | Letter Spacing |
|------|-----------|--------|------|-------------|----------------|
| 封面大标题 | Noto Sans SC Thin | 200 | 36–56pt | 1.05 | -2px |
| 一级标题 | Noto Sans SC Thin | 200 | 22–32pt | 1.2 | 1px |
| 二级标题 | Noto Sans SC Medium | 600 | 14pt | 1.3 | 0.5px |
| 三级标题 | Noto Sans SC Medium | 500 | 12pt | 1.3 | 0.5px |
| 正文 | Noto Sans SC Light | 300 | 10pt | 2.0 | 0 |
| 小号正文 | Noto Sans SC | 400 | 9pt | 1.7 | 0 |
| 说明/脚注 | Noto Sans SC | 400 | 8pt | 1.6 | 0.5px |
| 标签/元信息 | Noto Sans SC Medium | 500 | 7pt | 1.4 | 3px |
| 数据/代码 | JetBrains Mono | 400 | 9pt | 1.5 | 0 |
| 数字展示 | Noto Sans SC Thin | 200 | 28–40pt | 1.0 | -1px |

> **字重映射**（OpenXML / PptxGenJS 中指定字体名时用）：
> - weight ≤200 → `Noto Sans SC Thin`
> - weight 300 → `Noto Sans SC Light`
> - weight 400 → `Noto Sans SC`（Regular）
> - weight 500-600 → `Noto Sans SC Medium`
> - weight ≥700 → `Noto Sans SC` + Bold

### Spacing

| Token | Value |
|-------|-------|
| 页边距 | 48px / 1.27cm（比传统 1 inch 窄，更现代） |
| 段落间距 | 段后 6pt，不用整行空行。段落之间靠段后间距区分 |
| 正文行高 | 2.0（松散、可呼吸） |
| 标题上间距 | 120px（docx 封面）/ 32px（正文内） |
| 标题下间距 | 16px |
| 表格单元格内边距 | 上下 12px，左右 16px |
| 卡片内边距 | 24–36px |
| 章节间距 | 120px（PPT 章节间）/ 48px（docx 章节间） |
