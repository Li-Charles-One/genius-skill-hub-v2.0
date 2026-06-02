---
name: genius-vision
description: "Use when user asks to analyze, describe, understand, review, OCR, extract text from, or interpret any image — screenshots, mockups, charts, documents, photos, design files, wireframes, diagrams. Triggers: analyze image, describe image, what's in this image, OCR, extract text, UI review, design review, screenshot, mockup, chart analysis, compare images, 看图, 识别文字, 图片分析, 审查设计, 截图分析."
version: 1.0.0
author: Genius Agent
license: MIT
metadata:
  hermes:
    tags: [vision, image, ocr, analysis, review, doubao, visual]
    related_skills: []
---

# Genius Vision

Universal image analysis skill for AI agents. Analyzes images via doubao (豆包) vision API and returns structured results.

## Supported Environments

- Hermes Agent (native)
- Claude Code / Codex / Cursor (via Python script)

## Analysis Modes

| Mode | Use case | Output |
|------|----------|--------|
| `describe` | General image understanding | Detailed description |
| `ocr` | Text extraction from screenshots/docs | Preserved text structure |
| `ui-review` | UI mockups, wireframes, design critique | Structured design review |
| `chart-data` | Charts, graphs, data visualizations | Extracted data points |
| `object-detect` | Identify objects, people, activities | Listed elements with locations |
| `compare` | Two images side-by-side | Differences and similarities |

## Usage (Hermes Agent)

Call `vision_analyze` with a mode-specific prompt:

```
vision_analyze(image_url="path/to/image.png", question="[mode prompt below]")
```

### Mode Prompts

**describe:**
> Provide a detailed description of this image. Include: main subject, setting/background, colors/style, any text visible, notable objects, and overall composition.

**ocr:**
> Extract all text visible in this image verbatim. Preserve structure and formatting (headers, lists, columns, tables). If no text is found, say so.

**ui-review:**
> You are a senior UI/UX design reviewer. Analyze this interface mockup or design. Return a structured review: (1) Strengths — what works well, (2) Issues — usability or design problems with severity, (3) Specific actionable suggestions. Be constructive and detailed.

**chart-data:**
> Extract all data from this chart or graph. List: chart type, title, axis labels, all data points/series with values, and a brief summary of the trend or key insight.

**object-detect:**
> List all distinct objects, people, animals, and activities in this image. For each, describe what it is, its approximate location (top-left, center, bottom-right, etc.), and any notable attributes.

**compare:**
> Compare these two images. List: (1) What's the same, (2) What's different, (3) Which version is better and why.

## Usage (Other Agents — Python Script)

For agents without native vision tools, use the bundled script:

```bash
python3 /path/to/scripts/vision.py <image_path> <mode> [--output json|text]
```

### Modes
- `describe` — general description
- `ocr` — text extraction
- `ui-review` — design critique
- `chart-data` — chart data extraction
- `object-detect` — object identification

### Examples
```bash
python3 vision.py screenshot.png ui-review
python3 vision.py document.jpg ocr --output json
python3 vision.py design_v2.png describe
```

### Setup (Other Agents)
```bash
# Set environment variable
export ARK_API_KEY="your-volcengine-ark-api-key"

# Or create .env file in skill directory
echo 'ARK_API_KEY=your-key' > /path/to/genius-vision/scripts/.env
```

## Output Format

### Text mode (default)
```
## [Mode] Analysis

[Analysis content in readable markdown]
```

### JSON mode (`--output json`)
```json
{
  "mode": "ui-review",
  "image": "screenshot.png",
  "result": {
    "strengths": ["Clean layout", "Good color contrast"],
    "issues": [
      {"severity": "high", "description": "Missing alt text on images"},
      {"severity": "low", "description": "Button padding inconsistent"}
    ],
    "suggestions": [
      "Add aria-labels to icon buttons",
      "Standardize button padding to 12px"
    ]
  }
}
```

## Configuration

### API Provider
Default: 火山引擎 Ark (doubao-seed-2.0-lite)

**⚠️ Volcengine Ark 端点陷阱**：coding 端点用 `/api/coding/v3`，不要用 `/api/v3`（会 404）。

| Env Variable | Description | Default |
|---|---|---|
| `ARK_API_KEY` | Volcengine Ark API key | (required) |
| `VISION_MODEL` | Model name | `doubao-seed-2.0-lite` |
| `VISION_BASE_URL` | API base URL | `https://ark.cn-beijing.volces.com/api/coding/v3` |

### Quality Levels

| Level | Model | Speed | Cost |
|---|---|---|---|
| fast | doubao-seed-2.0-lite | ~1s | Free tier |
| balanced | doubao-seed-2.0 | ~2s | Low |
| best | doubao-seed-2.0-pro | ~3s | Medium |

Set via `VISION_MODEL` env or pass `--model` flag.

## Pitfalls

1. **All images are base64-encoded**: Both local files and URLs are sent as base64 for maximum reliability. URL images are downloaded first, then encoded.
2. **Image size**: Max 10MB. Resize large images before sending.
3. **SVG files**: Not directly supported. Convert to PNG first.
4. **API key required**: Must have valid `ARK_API_KEY`. No fallback.
5. **Chinese text**: doubao handles CJK natively — no special config needed.
6. **Batch analysis**: Process images sequentially to avoid rate limits.
7. **OCR accuracy**: For complex layouts, use `ocr` mode. `describe` mode summarizes text but doesn't extract verbatim.

## Verification

- [ ] `ARK_API_KEY` is set and valid
- [ ] Test with a simple image: `python3 vision.py test.jpg describe`
- [ ] Verify JSON output: `python3 vision.py test.jpg ocr --output json`
- [ ] Check that Chinese text is recognized correctly
