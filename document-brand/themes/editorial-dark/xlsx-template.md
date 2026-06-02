# 编辑级暗夜 — xlsx 工程映射

> 本文件只提供 **tokens → xlsx 参数映射**。设计意图见 `tokens.md`。
> 执行流程由 minimax-xlsx 自行决策。

## 工作表默认值

| 属性 | 值 |
|------|-----|
| 默认列宽（文本列） | `width="14"` |
| 默认列宽（数字列） | `width="11"` |
| 默认列宽（日期列） | `width="8"` |
| 默认行高 | `ht="24"` |
| Freeze pane | 表头行 + 首列（如有） |
| Gridlines | 关闭 Excel 默认网格线（`sheetView showGridLines="0"`），用自定义边框替代 |

## 令牌 → xlsx XML 映射

### 字体

xlsx 的字体通过 `styles.xml` 中的 `<font>` 元素定义，单元格通过 `s` 属性引用字体索引。

**默认字体**（字体索引 0）：

```xml
<font>
  <name val="Noto Sans SC"/>
  <sz val="12"/>          <!-- 12pt -->
  <color rgb="FF000000"/>  <!-- 黑色 -->
</font>
```

| tokens.md 角色 | `<name>` | `<sz>` | `<color>` | `<b/>` | 用途 |
|---------------|----------|--------|-----------|--------|------|
| 正文 (Light 300) | `Noto Sans SC` | `12` | `FF000000` | no | 数据单元格 |
| 小号正文 (400) | `Noto Sans SC` | `9` | `FF000000` | no | 脚注 |
| Medium (500-600) | `Noto Sans SC` | `12` | `FFFFFFFF` | no | 表头行文字 |

> **注意**：xlsx 的 `<font>` 不支持字重属性（无 `weight` 属性）。Noto Sans SC 变体通过字体名指定：
> - Light → `<name val="Noto Sans SC Light"/>`
> - Medium → `<name val="Noto Sans SC Medium"/>`

### 填充色

| tokens.md | `<fgColor>` | 用途 |
|-----------|-------------|------|
| `border` | `FF222222` | 表头行底色 |
| `accent-dim` | `FFF5F9FF` | 分类行底色 |
| 白底 | `FFFFFFFF` | 数据区底色 |
| 淡灰 | `FFFAFAFA` | 合计行底色 |

### 边框

| 位置 | `style` | `<color>` |
|------|---------|-----------|
| 表头底部 | `medium` | `FF00A8FF` |
| 表头其余三边 | `thin` | `FF333333` |
| 数据单元格四边 | `thin` | `FFE0E0E0` |
| 分类行底部 | `thin` | `FFE0E0E0` |
| 合计行顶部 | `medium` | `FF00A8FF` |

### 数字格式

| 类型 | `numFmt formatCode` | `numFmtId` |
|------|--------------------|------------|
| 整数 | `#,##0` | 自定义，≥ 164 |
| 小数 | `#,##0.00` | 同上 |
| 人民币 | `¥#,##0` | 同上 |
| 百分比 | `0.0%` | 同上 |

## 表头行

```xml
<row r="1" ht="32" customHeight="1">
```

每个单元格（`c`）：
- `s="N"` 引用 styles.xml 表头字体索引 + 填充索引
- 对齐：文本左对齐（`horizontal="left"`）
- 启用 auto-filter：`<autoFilter ref="A1:X1"/>`

## 数据区

```xml
<row r="2-n" ht="24">
```

每个单元格（`c`）：
- `s="N"` 引用数据区字体 + 白底填充 + 四边细线边框
- 对齐：文本左对齐，数字右对齐，日期居中
- 数字列使用 tabular-nums（等宽数字）

## 分类行

```xml
<row r="n" ht="28" customHeight="1">
```

合并整行：第一个 `<c>` 设置 `s="N"`（`F5F9FF` 底 + `00A8FF` 字 + Medium），后续单元格为空或合并。

## 合计行

```xml
<row r="n" ht="32" customHeight="1">
```

- `s="N"` 引用合计行字体（13pt Medium `000000`）+ `FAFAFA` 填充 + 顶部 medium `00A8FF` 边框

## 图表

| 属性 | 值 |
|------|-----|
| 绘图区底色 | `FFFFFFFF`（白色） |
| 网格线 | 仅水平主网格线，`style="hair"`，颜色 `F0F0F0` |
| 系列颜色顺序 | `00A8FF` → `000000` → `999999` → `555555` → `222222` |
| 数据标签 | 10pt，`555555` 色，数据点 ≤ 6 时显示 |
| 图例 | 底部，11pt |
| 3D / 渐变 | 禁止 |

## 打印布局

| 属性 | 值 |
|------|-----|
| 纸张 | A4 纵向（默认）。> 10 列切横向（`orientation="landscape"`） |
| 页边距 | 1.27cm 四边（在 `pageMargins` 中，单位为英寸：`top="0.5" bottom="0.5" left="0.5" right="0.5"`） |
| 页眉 | 文件名，左对齐，8pt，`555555` 色 |
| 页脚 | `"第 &P 页，共 &N 页"`，居中，8pt，`555555` 色 |
| 重复表头 | `printTitles rows="1:1"` |
| 自定义边框打印 | 关闭 `printGridLines="0"`，依赖自定义边框 |

## 已知坑位

1. **xlsx 无字重属性**：xlsx fonts 不支持 `weight`。Medium 字体需新建一个 `<font>` 条目，`name="Noto Sans SC Medium"`，不能在同一个 font 上同时用于不同字重的单元格。

2. **边框覆盖**：自定义边框必须在每个 `<c>` 的 `s` 引用的 `cellXf` 中设置。设置 `printGridLines="0"` 后若忘记自定义边框，单元格将完全无边线。

3. **字体变体名**：和 docx 一样，xlsx 也需用完整变体名（`Noto Sans SC Light` / `Noto Sans SC Medium`），不能只写 `Noto Sans SC`。

4. **分类行合并**：分类行的合并单元格用 `mergeCells` 或在 `<c>` 中省略后续列。不要写入空 `<c>` 元素——它们会创建可见的空单元格打破视觉统一。

## 校验清单

- [ ] 关闭 Excel 默认网格线（`showGridLines="0"`）
- [ ] 每个单元格有 4 边自定义边框
- [ ] 字体名使用完整变体名
- [ ] 表头行启用 auto-filter
- [ ] 冻结窗格在正确位置
- [ ] 数字列使用右对齐 + tabular-nums 格式
