---
name: genius-omni
description: "Universal image, video & audio analysis (Genius 视听). Default CPA gemini-3.6-flash-high (native generateContent); also google official Gemini, MiMo, or any custom multimodal provider via env. Supports 6 image / 4 video / 4 audio modes + YouTube. Triggers: analyze image, analyze video, analyze audio, OCR, 看图, 视频分析, 听音频, 转写, 视听, YouTube."
version: 2.5.0
---

# Genius Omni（视听）

Universal multimodal analysis for AI agents — **images, videos, audio, YouTube**.

**Default:** CPA `gemini-3.6-flash-high` via **native** Gemini `generateContent`.  
Also built-in: **Google official Gemini**, **Xiaomi MiMo**.  
**Any other multimodal model** can be plugged in via env (see [Add any multimodal model](#add-any-multimodal-model)).

> Skill name: **`genius-omni`** only（旧名 `genius-vision` 已废弃，勿再联接）。

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

### ffmpeg / ffprobe

```bash
# macOS
brew install ffmpeg
# Windows
winget install Gyan.FFmpeg
# Ubuntu / Debian
sudo apt install ffmpeg
```

Verify: `ffmpeg -version` and `ffprobe -version`.

## Usage (ZCode / Hermes Agent)

Call `vision_analyze` with a mode-specific prompt when available; otherwise use the Python script below.

## Usage (Other Agents — Python Script)

**`<skill_dir>`** = directory of this SKILL.md  
（OpenCode: `~/.config/opencode/skills/genius-omni/`）

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
python "<skill_dir>/scripts/vision.py" clip.mp3 describe

# Oversize media: only build proxy (no API)
python "<skill_dir>/scripts/vision.py" big.mp4 --proxy-only
python "<skill_dir>/scripts/vision.py" huge.wav --proxy-only
python "<skill_dir>/scripts/vision.py" giant.png --proxy-only
```

### Setup（推荐写 `scripts/.env`）

```bash
# Default provider pack
VISION_PROVIDER=cpa
CPA_API_KEY=sk-your-cpa-key
# optional overrides:
# CPA_MODEL=gemini-3.6-flash-high
# CPA_BASE_URL=https://cpa-jp.charles-ai.space/v1

# Optional: official Google Gemini
# GOOGLE_API_KEY=AIza...
# GOOGLE_MODEL=gemini-3.6-flash

# Optional: MiMo
# MIMO_API_KEY=tp-your-token-plan-key
```

Switch / inspect:
```bash
python scripts/vision.py --list-providers
python scripts/vision.py shot.png describe --provider cpa      # default
python scripts/vision.py shot.png describe --provider google
python scripts/vision.py shot.png describe --provider mimo
python scripts/vision.py "https://www.youtube.com/watch?v=..." video-summary
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

### Built-in providers

| Provider | API style | Default model | Base URL | Key env |
|---|---|---|---|---|
| **`cpa`（默认）** | `gemini` native | `gemini-3.6-flash-high` | `https://cpa-jp.charles-ai.space/v1` | `CPA_API_KEY` |
| `google` | `gemini` native | `gemini-3.6-flash` | `https://generativelanguage.googleapis.com/v1` | `GOOGLE_API_KEY` / `GEMINI_API_KEY` |
| `mimo` | `openai` | `mimo-v2.5` | `https://token-plan-cn.xiaomimimo.com/v1` | `MIMO_API_KEY` |

**API style 含义：**
- `gemini` → `POST {root}/v1beta/models/{model}:generateContent`  
  本地媒体：`inline_data`；YouTube：`file_data.file_uri`
- `openai` → `POST {base}/chat/completions`  
  `image_url` / `video_url` / `input_audio`

### Add any multimodal model

本 skill **不只绑死 CPA/MiMo**。任意兼容下面两种协议之一的多模态接口，都能配进来。

#### 方式 A：用内置 pack，只改模型/密钥

```bash
# 官方 Google
VISION_PROVIDER=google
GOOGLE_API_KEY=AIzaSy...
# optional:
# GOOGLE_MODEL=gemini-2.5-flash
# GOOGLE_BASE_URL=https://generativelanguage.googleapis.com/v1

# 同一 CPA 换模型
VISION_PROVIDER=cpa
CPA_API_KEY=sk-...
CPA_MODEL=gemini-3.5-flash-low
```

#### 方式 B：自定义 provider（任意名字）

在 `scripts/.env` 写（名字随便，例如 `openrouter` / `relay` / `qwen`）：

```bash
VISION_PROVIDER=openrouter

OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=google/gemini-2.5-flash
OPENROUTER_API_STYLE=openai    # gemini | openai（可省略，会按 host/model 猜）
```

规则（`{NAME}` = provider 名大写）：

| 变量 | 必填 | 说明 |
|---|---|---|
| `VISION_PROVIDER={name}` | 是 | 激活哪个 pack |
| `{NAME}_BASE_URL` | 是 | API base（OpenAI 风格带 `/v1`；Gemini 官方可 `/v1`） |
| `{NAME}_API_KEY` | 是 | 密钥（也认 `VISION_API_KEY`） |
| `{NAME}_MODEL` | 是 | 模型 id |
| `{NAME}_API_STYLE` | 否 | `gemini` 或 `openai`；不写则自动推断 |

CLI 一次性覆盖（不改 .env）：

```bash
python scripts/vision.py shot.png describe \
  --provider openrouter \
  --base-url https://openrouter.ai/api/v1 \
  --api-key sk-or-... \
  --model google/gemini-2.5-flash
```

查看当前配置：

```bash
python scripts/vision.py --list-providers
```

#### 选 `gemini` 还是 `openai`？

| 你的接口 | 设 |
|---|---|
| Google / CPA Gemini 原生（`generateContent`、支持 YouTube file_uri） | `gemini` |
| OpenAI 兼容网关（`/chat/completions`，图 `image_url`） | `openai` |
| 不确定 | 先 `--list-providers` 看推断；不行再显式设 `{NAME}_API_STYLE` |

> 注意：不是每个 OpenAI 兼容网关都真支持视频/音频。YouTube 目前只有 **`gemini` style** 稳定。

### Common env

| Env Variable | Description | Default |
|---|---|---|
| `VISION_PROVIDER` | active provider id | `cpa` |
| `VISION_MODEL` / `VISION_BASE_URL` | 仅覆盖**当前 active** provider | pack default |
| `{NAME}_MODEL` / `{NAME}_BASE_URL` / `{NAME}_API_KEY` / `{NAME}_API_STYLE` | per-provider | — |
| `VISION_API_STYLE` | 全局 style 覆盖（少用） | — |
| `VISION_VIDEO_FPS` | 视频抽帧 fps（MiMo openai） | `2` |
| `VISION_VIDEO_RESOLUTION` | `default` / `max`（MiMo） | `default` |
| `VISION_SHOW_THINKING` | `1` 输出 thinking | off |
| `VISION_MAX_TOKENS` | 输出上限 | `32768` |

### Models (examples)

| Model ID | Provider | 说明 |
|---|---|---|
| `gemini-3.6-flash-high` | cpa | **默认** |
| `gemini-3.6-flash` | google | 官方 Gemini |
| `mimo-v2.5` | mimo | 全模态（图/视频/音频） |
| `mimo-v2.5-pro` | mimo | **不支持**多模态，勿用 |

### Media formats

| Kind | Extensions | API content type |
|------|------------|------------------|
| Image | jpg/png/gif/webp/bmp | **CPA**: `inline_data`; **MiMo**: `image_url` |
| Video | mp4/mov/avi/mkv/webm/… / YouTube | **CPA native** `/v1beta/...:generateContent`：本地 `inline_data`，YouTube `file_data.file_uri`；**MiMo**: `video_url` |
| Audio | mp3/wav/flac/m4a/ogg（官方主推） | **CPA**: `inline_data`；**MiMo**: `input_audio` |

**Limits (MiMo)**：Base64 编码后约 ≤50MB（脚本按 **raw ≤35MB** 留余量）；音频 URL ≤100MB；视频 URL ≤300MB。

### 过大媒体自动代理（>20MB raw 默认触发）

本地 **视频 / 音频 / 图片** 超过 `VISION_PROXY_TRIGGER_MB`（默认 **20**）或超过 raw 上限时，`vision.py` **自动**压分析代理再上传。

| 类型 | 策略 |
|------|------|
| **Video** | HEVC 硬编 → H.264 硬编 → `libx264`；`scale=1280`；失败再 720p；API 拒 codec 则 H.264 重试 |
| **Audio** | 转 AAC `m4a`（默认 64k）；仍过大则 32k mono |
| **Image** | 长边 ≤2048 的 JPEG；仍过大则长边 1280 |

视频编码器顺序：`hevc_qsv/nvenc/amf` → `h264_qsv/nvenc/amf` → `libx264`。（**不用 AV1**：MiMo base64 常拒）

```bash
python scripts/vision.py big.mp4 --proxy-only
python scripts/vision.py clip.mp4 video-summary --force-proxy
```

| Env | Default | 含义 |
|-----|---------|------|
| `VISION_PROXY_TRIGGER_MB` | `20` | 超过则自动代理 |
| `VISION_MAX_RAW_MB` | `35` | base64 上传 raw 上限 |
| `VISION_PROXY_SCALE` | `1280` | 视频代理宽度 |
| `VISION_PROXY_AUDIO_K` | `64k` | 音轨/音频代理码率 |
| `VISION_PROXY_IMAGE_MAX_EDGE` | `2048` | 图片代理长边 px |

有公网 URL 时优先 URL（视频 ≤300MB），可跳过 base64 与代理。

### Thinking
对 `mimo-*` **强制** `"thinking": {"type": "enabled"}`，不可关闭。

## Pitfalls

1. 本地文件 → base64 data-URI；公网 URL 直接透传。
2. MiMo 仅 `mimo-v2.5` 支持多模态；`pro` 不能看图/听音频。切换 `--provider mimo` 时用 MiMo key。
3. 音频 API 字段是 `input_audio.data`（不是 `audio_url`）。
4. 开思考会变慢、吃 token；`VISION_MAX_TOKENS` 默认 32768。
5. SVG 需先转 PNG；复杂音频格式以实测为准。
6. 分析代理需要本机 `ffmpeg`；无硬件编码器时视频回退 `libx264`。
7. 代理是分析用，非成片；临时文件在系统 TEMP 的 `genius-omni-proxy/`。
8. OpenCode 技能名固定为 `genius-omni`。

## Verification

- [ ] `MIMO_API_KEY` set (or `scripts/.env`)
- [ ] Image: `python scripts/vision.py test.jpg describe`
- [ ] Video: `python scripts/vision.py test.mp4 video-summary`
- [ ] Large video proxy: `python scripts/vision.py big.mp4 --proxy-only`（应见 `hevc_*` 或 `h264_*`）
- [ ] Large audio proxy: `python scripts/vision.py big.wav --proxy-only`（应见 `.m4a`）
- [ ] Large image proxy: `python scripts/vision.py big.png --proxy-only`（应见 `.jpg`）
- [ ] Audio: `python scripts/vision.py test.mp3 audio-summary`
- [ ] Audio ASR-style: `python scripts/vision.py test.wav audio-transcribe`
