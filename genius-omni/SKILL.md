---
name: genius-omni
description: "Analyze images, analyze video/audio, and OCR (Genius 视听). Use when the user wants to understand a picture, extract text, transcribe speech, or summarize a video/audio/YouTube file. Triggers: 看图, 这张图是什么, 分析图片, 描述图片, 识图, OCR, 识别文字, 提取文字, 截图里的字, 读这个PDF, 对比这两张图, 看看这个界面, 分析视频, 这个视频讲了什么, 视频总结, YouTube, 转写, 听写, 录音转文字, 分析音频, 听这段, 视听. Do not use for generating images or video (genius-cpa-image / dreamina-cli), DESIGN.md, or shotlists."
metadata:
  version: "2.6.0"
---

# Genius Omni（视听）

This skill exists to **analyze images**, **analyze video/audio**, and **OCR**. Nothing else.

Default: CPA `gemini-3.6-flash-high` via native Gemini `generateContent`. Also: official Google Gemini, Xiaomi MiMo, or another multimodal pack via env. Old name `genius-vision` is retired.

Config, examples, providers, proxy, and verification: `references/usage.md`.

## Pick a mode

| User wants | Mode |
|---|---|
| What is in this picture | `describe` |
| Read text in a screenshot / photo / PDF | `ocr` |
| Critique a UI screenshot | `ui-review` |
| Read a chart | `chart-data` |
| List objects in a picture | `object-detect` |
| Diff two pictures | `compare` |
| What happened in this video / YouTube | `video-summary` |
| Text visible in a video | `video-ocr` |
| Critique a recording | `video-review` |
| Shot-by-shot video | `video-frame-analysis` |
| What is in this audio | `audio-summary` |
| Transcribe speech | `audio-transcribe` |
| Critique audio production | `audio-review` |
| Soundscape / events | `audio-scene` |

## Modes

| Kind | Modes |
|---|---|
| Image | `describe` `ocr` `ui-review` `chart-data` `object-detect` `compare` |
| Video | `video-summary` `video-ocr` `video-review` `video-frame-analysis` |
| Audio | `audio-summary` `audio-transcribe` `audio-review` `audio-scene` |
| PDF | `ocr` (default) `describe` `chart-data` `ui-review` — render pages, merge |

Auto remap: audio `describe`→`audio-summary`, `ocr`→`audio-transcribe`. Video `describe`→`video-summary`, `ocr`→`video-ocr`.

Local video ≥ 15 min is segmented (disable `--no-long-video`). `ffprobe` injects real duration.

## Run

Needs `ffmpeg` / `ffprobe`. Then:

```bash
python "<skill_dir>/scripts/vision.py" <file_or_url> <mode> [--output json|text]
python "<skill_dir>/scripts/vision.py" --check
python "<skill_dir>/scripts/vision.py" --list-providers
```

`<skill_dir>` is this skill folder. Keys live in local env, not in the package.

## Gotchas

- This skill analyzes media and extracts text. It does not generate images or video.
- MiMo multimodal is `mimo-v2.5` only. `mimo-v2.5-pro` cannot see or hear.
- YouTube is stable on Gemini-style providers, not every OpenAI-compatible gateway.
- Proxy/index temp files live under system TEMP (`genius-omni-proxy/`, `genius-omni-index/`).

## Resource Map

- `scripts/vision.py`
- `references/usage.md`
