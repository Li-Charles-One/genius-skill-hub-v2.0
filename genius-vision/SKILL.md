---
name: genius-vision
description: Universal image & video analysis via doubao (豆包) vision API. Use when user asks to analyze, OCR, review, or describe any image or video file. Supports 6 image modes (describe, ocr, ui-review, chart-data, object-detect, compare) and 4 video modes (video-summary, video-ocr, video-review, video-frame-analysis). Triggers: analyze image, analyze video, OCR, extract text, UI review, screenshot, chart, video summary, 看图, 视频分析.
version: 1.2.0
---

# Genius Vision

Universal image & video analysis skill for AI agents. Analyzes images and videos via doubao (豆包) vision API and returns structured results. Video files are auto-detected by extension (.mp4/.mov/.avi/.mkv/.webm) and sent as native video_url — no ffmpeg frame extraction needed.

## Supported Environments

- Hermes Agent (native)
- Claude Code / Codex / Cursor (via Python script)

## Analysis Modes

### Image Modes

| Mode | Use case | Output |
|------|----------|--------|
| `describe` | General image understanding | Detailed description |
| `ocr` | Text extraction from screenshots/docs | Preserved text structure |
| `ui-review` | UI mockups, wireframes, design critique | Structured design review |
| `chart-data` | Charts, graphs, data visualizations | Extracted data points |
| `object-detect` | Identify objects, people, activities | Listed elements with locations |
| `compare` | Two images side-by-side | Differences and similarities |

### Video Modes (auto-detected by extension)

| Mode | Use case | Output |
|------|----------|--------|
| `video-summary` | Full video understanding | Timeline + key content + tone |
| `video-ocr` | Extract text visible in video | Chronological text with timestamps |
| `video-review` | Video/screen recording production critique | Structured review with suggestions |
| `video-frame-analysis` | Frame-level / scene-by-scene breakdown | Per-scene timestamp + visual + audio detail |

**Duration verification**: For all video modes, `ffprobe` automatically extracts actual duration, injects it as ground truth into the prompt, and appends a comparison footer to the output.

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

For agents without native vision tools, use the bundled script. Auto-detects video by extension:

```bash
python /path/to/scripts/vision.py <file_path_or_url> <mode> [--output json|text]
```

### Image Modes
- `describe` — general description
- `ocr` — text extraction
- `ui-review` — design critique
- `chart-data` — chart data extraction
- `object-detect` — object identification
- `compare` — side-by-side image comparison (requires `--compare-with`)

### Video Modes
- `video-summary` — full video understanding with timeline
- `video-ocr` — extract text visible in video
- `video-review` — video/screen recording production critique

### Examples
```bash
# Images
python vision.py screenshot.png ui-review
python vision.py document.jpg ocr --output json
python vision.py before.png compare --compare-with after.png

# Videos (auto-detected by .mp4/.mov/.avi/.mkv/.webm extension)
python vision.py meeting.mp4 video-summary
python vision.py screencast.mov video-review
python vision.py presentation.mp4 video-ocr --output json
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

1. **All files are base64-encoded**: Both local files and URLs are sent as base64 for maximum reliability. URL files are downloaded first, then encoded.
2. **Image size**: Max 10MB. Resize large images before sending.
3. **Video size**: Max 50MB. Large videos may need compression or trimming before analysis.
4. **SVG files**: Not directly supported. Convert to PNG first.
5. **API key required**: Must have valid `ARK_API_KEY`. No fallback.
6. **Chinese text**: doubao handles CJK natively — no special config needed.
7. **Batch analysis**: Process files sequentially to avoid rate limits.
8. **OCR accuracy**: For complex layouts, use `ocr` mode. `describe` mode summarizes text but doesn't extract verbatim.
9. **Video timeout**: Video analysis can take up to 120s. The script sets a longer timeout for video files automatically.

## Verification

- [ ] `ARK_API_KEY` is set and valid
- [ ] Test with a simple image: `python3 vision.py test.jpg describe`
- [ ] Verify JSON output: `python3 vision.py test.jpg ocr --output json`
- [ ] Check that Chinese text is recognized correctly
