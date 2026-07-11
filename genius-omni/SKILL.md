---
name: genius-omni
description: "Universal image, video & audio analysis (Genius 视听) via Xiaomi MiMo mimo-v2.5. Use when user asks to analyze, OCR, review, describe, or transcribe any image/video/audio file. Supports 6 image modes, 4 video modes, 4 audio modes. Triggers: analyze image, analyze video, analyze audio, OCR, 看图, 视频分析, 听音频, 转写, 视听."
version: 2.0.0
---

# Genius Omni（视听）

Universal multimodal analysis skill for AI agents. Analyzes **images, videos, and audio** via Xiaomi MiMo (`mimo-v2.5`) OpenAI-compatible API. Media kind is auto-detected by extension; local files are sent as base64 data-URIs; public URLs pass through.

> Formerly `genius-vision`. Folder alias `genius-vision` may still point here for compatibility; skill name is **`genius-omni`**.

## Supported Environments

- ZCode / Hermes Agent (native)
- Claude Code / Codex / OpenCode / Cursor (via Python script)

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

### Video Modes

| Mode | Use case | Output |
|------|----------|--------|
| `video-summary` | Full video understanding | Timeline + key content + tone |
| `video-ocr` | Extract text visible in video | Chronological text with timestamps |
| `video-review` | Video/screen recording production critique | Structured review with suggestions |
| `video-frame-analysis` | Frame-level / scene-by-scene breakdown | Per-scene storyboard |

### Audio Modes (MiMo `input_audio`)

| Mode | Use case | Output |
|------|----------|--------|
| `audio-summary` | Full audio understanding | Timeline + speakers + soundscape |
| `audio-transcribe` | Speech-to-text | Verbatim transcript + speakers |
| `audio-review` | Production quality critique | Structured review + fixes |
| `audio-scene` | Acoustic scene analysis | Events, environment, atmosphere |

**Auto mode remap**: on audio, `describe`→`audio-summary`, `ocr`→`audio-transcribe`, `ui-review`/`video-review`→`audio-review`. On video, `describe`→`video-summary`, `ocr`→`video-ocr`.

**Duration verification**: For video/audio local files, `ffprobe` injects actual duration into the prompt and appends a footer.

## Prerequisites

### ffprobe (video / audio duration)

```bash
# macOS
brew install ffmpeg
# Windows
winget install Gyan.FFmpeg
# Ubuntu / Debian
sudo apt install ffmpeg
```

Verify: `ffprobe -version`.

## Usage (ZCode / Hermes Agent)

Call `vision_analyze` with a mode-specific prompt when available; otherwise use the Python script below.

## Usage (Other Agents — Python Script)

**`<skill_dir>`** = the directory containing this SKILL.md (e.g. `~/.config/opencode/skills/genius-omni/`).

```bash
python "<skill_dir>/scripts/vision.py" <file_path_or_url> <mode> [--output json|text]
```

### Examples
```bash
# Images
python "<skill_dir>/scripts/vision.py" screenshot.png ui-review
python "<skill_dir>/scripts/vision.py" document.jpg ocr --output json
python "<skill_dir>/scripts/vision.py" before.png compare --compare-with after.png

# Videos
python "<skill_dir>/scripts/vision.py" meeting.mp4 video-summary
python "<skill_dir>/scripts/vision.py" lecture.mp4 video-frame-analysis

# Audio
python "<skill_dir>/scripts/vision.py" podcast.mp3 audio-summary
python "<skill_dir>/scripts/vision.py" interview.wav audio-transcribe
python "<skill_dir>/scripts/vision.py" mix.flac audio-review
python "<skill_dir>/scripts/vision.py" field.m4a audio-scene
# describe on audio auto-maps to audio-summary
python "<skill_dir>/scripts/vision.py" clip.mp3 describe
```

### Setup
```bash
export MIMO_API_KEY="tp-your-token-plan-key"
export VISION_BASE_URL="https://token-plan-cn.xiaomimimo.com/v1"
export VISION_MODEL="mimo-v2.5"

# Or scripts/.env
echo 'MIMO_API_KEY=tp-your-key' > "<skill_dir>/scripts/.env"
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
  "mode": "audio-transcribe",
  "file": "interview.wav",
  "result": "..."
}
```

## Configuration

### API Provider
Default: **Xiaomi MiMo Token Plan** — `mimo-v2.5`（全模态：图 / 视频 / 音频）

官方文档：
- 图：https://mimo.mi.com/docs/zh-CN/usage-guide/multimodal-understanding/image-understanding
- 视频：https://mimo.mi.com/docs/zh-CN/usage-guide/multimodal-understanding/video-understanding
- 音频：https://mimo.mi.com/docs/zh-CN/usage-guide/multimodal-understanding/audio-understanding
- 深度思考：https://mimo.mi.com/docs/zh-CN/quick-start/usage-guide/text-generation/deep-thinking

| Env Variable | Description | Default |
|---|---|---|
| `MIMO_API_KEY` | MiMo API key（也认 `VISION_API_KEY` / `ARK_API_KEY`） | (required) |
| `VISION_MODEL` | Model name | `mimo-v2.5` |
| `VISION_BASE_URL` | API base URL | `https://token-plan-cn.xiaomimimo.com/v1` |
| `VISION_VIDEO_FPS` | 视频抽帧 fps | `2` |
| `VISION_VIDEO_RESOLUTION` | `default` / `max` | `default` |
| `VISION_SHOW_THINKING` | `1` 时输出 `reasoning_content` | off |
| `VISION_MAX_TOKENS` | 思考+回答总上限 | `32768` |

### Models

| Model ID | 能力 | 说明 |
|---|---|---|
| `mimo-v2.5` | 全模态（图/视频/音频/文本） | **默认，视听必用** |
| `mimo-v2.5-pro` | 文本/Agent 旗舰 | **不支持**多模态，勿用于本 skill |

### Media formats

| Kind | Extensions | API content type |
|------|------------|------------------|
| Image | jpg/png/gif/webp/bmp | `image_url` |
| Video | mp4/mov/avi/mkv/webm/… | `video_url` (+ fps, media_resolution) |
| Audio | mp3/wav/flac/m4a/ogg（官方主推） | `input_audio` |

**Limits (MiMo)**：Base64 单文件编码后 ≤50MB；音频 URL ≤100MB；视频 URL ≤300MB。

### Thinking
对 `mimo-*` **强制** `"thinking": {"type": "enabled"}`，不可关闭。

## Pitfalls

1. 本地文件 → base64 data-URI；公网 URL 直接透传。
2. 仅 `mimo-v2.5` 支持多模态；`pro` 不能看图/听音频。
3. 音频 API 字段是 `input_audio.data`（不是 `audio_url`）。
4. 开思考会变慢、吃 token；`VISION_MAX_TOKENS` 默认 32768。
5. SVG 需先转 PNG；复杂音频格式以实测为准。

## Verification

- [ ] `MIMO_API_KEY` set (or `scripts/.env`)
- [ ] Image: `python scripts/vision.py test.jpg describe`
- [ ] Video: `python scripts/vision.py test.mp4 video-summary`
- [ ] Audio: `python scripts/vision.py test.mp3 audio-summary`
- [ ] Audio ASR-style: `python scripts/vision.py test.wav audio-transcribe`
