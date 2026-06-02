# 编辑级暗夜 — pdf 工程映射

> 本文件只提供 **tokens → PDF 参数映射**。设计意图见 `tokens.md`。

## 页面几何

| 属性 | 值 |
|------|-----|
| 页面尺寸 | A4（210mm × 297mm） |
| 页边距 | 48px（1.27cm / ~0.5 inch）四边 |

## 字体嵌入

| 操作 | 说明 |
|------|------|
| 嵌入字体 | Noto Sans SC 子集（Thin / Light / Regular / Medium 四个变体） |
| Latin fallback | Inter Regular |

嵌入命令（通过 LibreOffice / Ghostscript）：

```bash
# 确保字体已安装到系统
# 然后导出 PDF 时自动嵌入
soffice --headless --convert-to pdf document.docx
```

## 元数据

| 字段 | 值 |
|------|-----|
| Title | 文档标题（由用户提供） |
| Author | 用户指定 |
| Subject | 用户指定 |
| Creator | `"MiniMax Document Pipeline"` |

## 暗色页面

封面和章节分隔页的 `#000000` 背景**保留**在 PDF 中。这是设计意图——暗底冲击力是视觉语言的一部分。

若用户要求打印优化版：
- 封面背景 → `#ffffff`
- 封面标题色 → `#000000`
- 分割线保留 `#00a8ff`
- 正文不变（本就是白底黑字）

## 已知坑位

1. **字体缺失回退**：若目标系统未安装 Noto Sans SC，PDF 渲染器会用默认衬线/无衬线回退。确保生成 PDF 前系统已安装 Noro Sans SC。

2. **暗底打印成本**：黑色满版打印耗墨。生成 PDF 时提醒用户——如需大量纸质分发，建议同时生成一份打印版（白底）。

3. **从 docx 生成时 sectPr 一致性**：封面和正文分属两个 section。导出 PDF 时确保 soffice 正确处理 section 边界——封面 sectPr type="nextPage" 后正文页码应从 1 开始。
