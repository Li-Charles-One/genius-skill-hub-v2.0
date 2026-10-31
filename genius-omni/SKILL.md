---
name: genius-omni
description: "Genius 多模态视听分析：用于图像理解、UI 界面分析、文档/PDF OCR 文字提取，以及音视频总结与语音转写。"
metadata:
  version: "2.9.1"
---

# Genius Omni（视听）

This skill exists to **analyze images**, **analyze video/audio**, and **OCR**. Nothing else.

Default: CPA via native Gemini `generateContent`. Alternative: any multimodal endpoint configured as a custom provider. `--check` shows the model each provider will actually use.

Config, providers, proxy and verification: `references/usage.md`. Trigger checks: `evals/evals.json`.

## Pick a mode

| User wants | Mode |
|---|---|
| What is in this picture | `describe` |
| Read text in a screenshot / photo / PDF | `ocr` |
| Critique a UI screenshot | `ui-review` |
| Read a chart | `chart-data` |
| List objects in a picture | `object-detect` |
| Diff two pictures | `compare` (`--compare-with <second>`) |
| What happened in this video / YouTube | `video-summary` |
| Text visible in a video | `video-ocr` |
| Critique a recording | `video-review` |
| Shot-by-shot video | `video-frame-analysis` |
| What is in this audio | `audio-summary` |
| Transcribe speech | `audio-transcribe` |
| Critique audio production | `audio-review` |
| Soundscape / events | `audio-scene` |

PDF accepts `ocr` (default), `describe`, `chart-data`, `ui-review`. Generic modes remap automatically: audio `describe`→`audio-summary`, `ocr`→`audio-transcribe`; video `describe`→`video-summary`, `ocr`→`video-ocr`.

## Run

```bash
python3 "<skill_dir>/scripts/vision.py" <file_or_url> <mode> [--output json|text] [--provider cpa|<custom>]
python3 "<skill_dir>/scripts/vision.py" --check
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`, plus `pdftoppm` only for page-mode PDF. No Python packages to install. Keys live in `scripts/.env`, never in the package.

- Note the video length or PDF page count before running. A missing local file fails with `INPUT_NOT_FOUND`; URLs are not pre-checked.
- Local audio/video of any size or codec needs no preparation: the script probes it, prints `plan: …` (as-is, one proxy, or N segments), encodes once and caches the proxy. Do not transcode or split it yourself.
- PDF: CPA reads the whole document in one request; OpenAI-style providers (or `VISION_PDF_PAGES=1`) render pages and analyze them one by one.
- Run one media analysis at a time; parallel runs make the CPA gateway return 502 (retried automatically, but slower).
- `audio-transcribe` first asks the model whether a human voice is audible (one short extra request; `VISION_VOICE_CHECK=0` disables) and answers `NO_SPEECH_DETECTED` without transcribing when there is none.

## Report

- Image: `Summary`, `Observations`, `Extracted Text` (when requested), `Uncertainty`.
- Video: `Summary`, `Timeline`, `Key Moments`, `Uncertainty`.
- Audio: `Summary`, `Transcript or Key Segments`, `Speakers or Sound Events`, `Uncertainty`.
- Compare: `Unchanged`, `Added`, `Removed`, `Uncertain`.

Analysis modes answer in Simplified Chinese; quoted text, speech, names and brands stay verbatim. `ocr`, `video-ocr` and `audio-transcribe` keep the source language. Keep OCR as observed text and mark inferred repairs separately. Unreadable spans stay `[illegible]` (speech: `[inaudible]`); never guess. Report `NO_TEXT_FOUND` when the result says no text was found; pass `NO_SPEECH_DETECTED` through unchanged. If long-media segmentation fails, report the failed segment and do not fabricate a summary.

Failures print `Error [CODE]: …` with a non-zero exit. Report the code and message as-is; the code table is in `references/usage.md`.

## Gotchas

- YouTube works on Gemini-style providers (CPA), not on every OpenAI-compatible gateway.
- Proxy, PDF page and segment index files live under system TEMP (`genius-omni-proxy/`, `genius-omni-index/`) and are purged after 30 days.
