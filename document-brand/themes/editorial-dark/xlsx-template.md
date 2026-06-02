# 编辑级暗夜 — minimax-xlsx 模板

> 本主题的 xlsx 明底策略：白底黑字数据区 + 黑色表头 + 蓝色强调。表格不是装饰品，是信息本身。
>
> 使用前先读取 `tokens.md` 获取色彩、字体、间距令牌。

### Sheet Setup

- **默认字体**: 小号正文 typography（Noto Sans SC, 12pt, weight 400）。
- **默认列宽**: 14 字符（文本列），11 字符（数字列），8 字符（日期列）。根据内容调整。
- **默认行高**: 24pt。
- **Freeze**: 冻结表头行 + 首列（如有索引列）。
- **Gridlines**: 关闭 Excel 默认灰色网格线——用自定义边框代替。

### Header Row

| Property | Value |
|----------|-------|
| Fill | `border` (`#222222`) |
| Font | `text-primary` (`#ffffff`), 12pt, weight 500 |
| Letter Spacing | 2px（通过字符间距设置） |
| Alignment | 左对齐 |
| Height | 32pt |
| Bottom Border | 2px `accent` (`#00a8ff`)。其余三边 1px `#333`。 |
| Auto-filter | 启用 |

### Data Zone

| Property | Value |
|----------|-------|
| Fill | 白底 (`#ffffff`) |
| Font | `#000000`, 12pt, weight 300 |
| Row Height | 24pt |
| Borders | 四边 1px `#e0e0e0`。每个单元格都有边框——xlsx 必须有清晰的网格线。 |
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
