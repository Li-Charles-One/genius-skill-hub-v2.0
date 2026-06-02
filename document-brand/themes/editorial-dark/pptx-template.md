# 编辑级暗夜 — pptx-generator 模板

> 这是本主题的**主战场**——全暗底 PPT，跟参考网页的 UI 语言完全一致。PptxGenJS 引擎。
>
> 使用前先读取 `tokens.md` 获取色彩、字体、间距令牌。

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
│  [TAG LINE]                         │  ← 7pt, accent, letter-spacing 3px
│                                      │     y = 28%, x = 60px
│  [TITLE]                            │  ← 56pt, weight 200, #ffffff
│                                      │     letter-spacing -2px, line-height 1.05
│  ──                                 │  ← accent 分割线, 48px wide, 1px
│                                      │
│  [Subtitle]                         │  ← 11pt, weight 300, #999999
│                                      │     line-height 1.8, max 2 lines
│                                      │
│                                      │
│  [Date]                  [Author]   │  ← 8pt, #555555, bottom 60px
└──────────────────────────────────────┘
```

#### TOC (目录)

```
全屏 #000000
┌──────────────────────────────────────┐
│                                      │
│  目录                               │  ← 7pt, accent, letter-spacing 3px, y = 8%
│                                      │
│  01  [Section]           ······ 03  │  ← Number: 40pt, weight 200, accent
│  02  [Section]           ······ 05  │     Label: 13pt, weight 500, #ffffff
│  03  [Section]           ······ 08  │     Page num: 9pt, #555555, right
│  04  [Section]           ······ 12  │     Dotted leader between
│  05  [Section]           ······ 15  │
│                                      │     y = 20%, items start at y = 38%
└──────────────────────────────────────┘
```

#### Section Divider (章节分隔)

```
全屏 #0a0a0a (bg-secondary)
┌──────────────────────────────────────┐
│                                      │
│                                      │
│              02                      │  ← 80pt, weight 200, accent
│          [Section Title]             │  ← 26pt, weight 200, #ffffff
│              ───                     │  ← accent 分割线, 1px × 64px, 居中
│                                      │
│                                      │
└──────────────────────────────────────┘
```

#### Content (内容)

```
全屏 #000000
┌──────────────────────────────────────┐
│                                      │
│  02  章节标签                        │  ← 7pt, accent, letter-spacing 3px, x = 60px, y = 8%
│                                      │
│  [Slide Title]                      │  ← 28pt, weight 200, #ffffff
│                                      │     letter-spacing -1px
│                                      │
│  [Body text body text body text     │  ← 10pt, weight 300, #999999
│   body text body text body text     │     line-height 2.0
│   body text body text.]             │     max-width: 72% slide width
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
│                                      │
│  03  关键数据                        │  ← 7pt, accent, letter-spacing 3px, x = 60px, y = 8%
│                                      │
│  ┌──────────┐ ┌──────────┐ ┌──────┐ │
│  │ 50×      │ │ 0%       │ │ v8   │ │  ← #111111 背景
│  │ 更多迭代 │ │ 零废料   │ │ 正确 │ │     #222222 边框
│  │          │ │          │ │ 答案 │ │     6px 圆角
│  │ desc...  │ │ desc...  │ │ desc │ │     数字: 32pt weight 200 accent
│  └──────────┘ └──────────┘ └──────┘ │     标题: 11pt weight 600 #ffffff
│                                      │     描述: 8pt #777777
└──────────────────────────────────────┘
```

#### Tables in Slides

| Element | Style |
|---------|-------|
| Background | `bg-card` (`#111111`) with 1px `border` (`#222222`), 8px radius |
| Header row | `border` (`#222222`), white 9pt weight 500 |
| Data rows | `#111111` bg. `#ffffff` text, 8pt weight 300. 底部 1px `#222222` |
| Category row | `accent-dim` bg, `accent` text, 8pt |
| Totals | 顶部 2px `accent`, `accent` text, 9pt bold |
| Cell padding | 12px top/bottom, 16px left/right |

#### Charts

- **Style**: 扁平。无 3D。暗色绘图区（`#0a0a0a`）。
- **Gridlines**: 仅水平，`#1a1a1a`，0.5pt。
- **Palette**: `00a8ff`, `ffffff`, `999999`, `555555`, `222222`
- **Data labels**: 10pt, `#999999`。
- **Legend**: 底部，11pt, `#999999`。

### Design Checklist

- [ ] 所有幻灯背景为 `#000000` 或 `#0a0a0a`
- [ ] 内容页顶部无装饰线——仅标签 + 标题，纯粹干净
- [ ] 章节标签 7pt, accent, letter-spacing 3px
- [ ] 标题 weight 200（极细），非粗体
- [ ] 正文 weight 300，`#999999`，行高 1.8
- [ ] 数字展示用 weight 200 + accent 色
- [ ] 卡片使用 `#111111` 背景 + `#222222` 边框 + 8px 圆角
- [ ] 表格四边有 1px 边框，行与行之间也有边框
- [ ] 无 Comic Sans、无剪贴画、无 3D 效果
- [ ] 页码右下角，10pt `#555555`
