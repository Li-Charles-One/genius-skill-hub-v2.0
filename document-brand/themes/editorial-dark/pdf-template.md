# 编辑级暗夜 — pdf 模板

> 使用前先读取 `tokens.md` 获取色彩、字体、间距令牌。

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
