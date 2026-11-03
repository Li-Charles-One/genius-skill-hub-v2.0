# Genius Omni Usage, Config, Verification

## Prerequisites

```bash
# macOS
brew install ffmpeg poppler
# Windows
winget install Gyan.FFmpeg        # PDF page mode: install poppler and put pdftoppm on PATH
# Ubuntu / Debian
sudo apt install ffmpeg poppler-utils
```

Verify with `python3 scripts/vision.py --check`. `pdftoppm` (poppler) is only needed for page-mode PDF. The script uses only the Python standard library (3.9+).

## Usage

`<skill_dir>` = directory of this SKILL.md (OpenCode: `~/.config/opencode/skills/genius-omni/`). On Windows replace `python3` with `python`. ZCode / Hermes may call their built-in `vision_analyze` with a mode-specific prompt instead.

```bash
python3 "<skill_dir>/scripts/vision.py" <file_path_or_url> <mode> [--output json|text]

# Images
python3 "<skill_dir>/scripts/vision.py" screenshot.png ui-review
python3 "<skill_dir>/scripts/vision.py" document.jpg ocr --output json
python3 "<skill_dir>/scripts/vision.py" before.png compare --compare-with after.png

# Video / YouTube (long local media is split by the computed plan)
python3 "<skill_dir>/scripts/vision.py" meeting.mp4 video-summary
python3 "<skill_dir>/scripts/vision.py" lecture-2h.mp4 video-summary --no-long-video
python3 "<skill_dir>/scripts/vision.py" "https://www.youtube.com/watch?v=..." video-summary

# Exact shot list (frames, timecode, count) + per-shot description from storyboards
python3 "<skill_dir>/scripts/vision.py" footage.mov video-shots --output json
# Measurement only, no model (also what ArtisticCut calls)
python3 "<skill_dir>/scripts/measure.py" footage.mov [--output json]

# Audio
python3 "<skill_dir>/scripts/vision.py" clip.mp3 describe          # → audio-summary

# PDF
python3 "<skill_dir>/scripts/vision.py" report.pdf ocr
VISION_PDF_PAGES=1 python3 "<skill_dir>/scripts/vision.py" scan.pdf ocr   # force page-by-page

# Show the plan and build proxies / segments only (no API call)
python3 "<skill_dir>/scripts/vision.py" big.mp4 --proxy-only
python3 "<skill_dir>/scripts/vision.py" report.pdf --proxy-only           # render pages

# Self-test / providers
python3 "<skill_dir>/scripts/vision.py" --check
python3 "<skill_dir>/scripts/vision.py" --list-providers
```

## Setup (`scripts/.env`)

```bash
VISION_PROVIDER=cpa
CPA_API_KEY=sk-your-cpa-key
# optional overrides (CPA_MODEL replaces both defaults, for every media kind):
# CPA_MODEL=gemini-4-argon-high
# CPA_BASE_URL=https://cpa-jp.charles-ai.space/v1

```

The first existing file wins: `scripts/.env`, then `~/.hermes/.env`. Process environment variables override both. `--check` and `--list-providers` show the model that requests will actually use.

## Output

Text mode (default) prints `## <Mode> Analysis` followed by the model's markdown. Analysis modes answer in Simplified Chinese (quotes, names and brands stay in the original language, also in long-media synthesis); `ocr` and `video-ocr` keep the source language. `--output json` prints `{"mode": ..., "file": ..., "result": ...}`. Local audio/video results end with a `⏱ 时长校验` footer comparing the ffprobe duration with the duration the model claims. `video-shots` prints a shot table instead; with `--output json`, `result` is the measurement (`fps`, `fps_rational`, `frames`, `duration`, `timecode_start`, `shots[]` with `first`/`last`/`tc_in`/`tc_out`/`via`/`transition`/`desc`, `suspects[]` with `check`/`reason`, `storyboards`, `warnings`).

Failures go to stderr as `Error [CODE]: message`:

| Code | Exit | Typical cause |
|---|---|---|
| `INPUT_NOT_FOUND` | 3 | local file does not exist |
| `UNSUPPORTED_FORMAT` | 4 | mode does not fit the media (e.g. `audio-summary` on an image, `ocr` on audio) |
| `DEPENDENCY_MISSING` | 5 | `ffmpeg` / `ffprobe` / `pdftoppm` not on PATH |
| `PROVIDER_ERROR` | 6 | unknown provider, missing key, HTTP error, network failure |
| `TIMEOUT` | 7 | no API response in time, or an ffmpeg step timed out |

Other errors exit 1; `--check` with missing tools exits 2.

## Providers

| Provider | API style | Default model | Base URL | Key env |
|---|---|---|---|---|
| **`cpa`（默认）** | `gemini` native | images / PDF `gemini-3.8-flash-high`; video / audio `gemini-4-argon-high` | `https://cpa-jp.charles-ai.space/v1` | `CPA_API_KEY` |

- CPA picks the model by media kind: `gemini-4-argon-high` filled every timeline gap and did not invent a soundtrack where 3.8 did, at 40–60% more time per request; for images and PDF 3.8 is as good and faster. `--model`, `CPA_MODEL` or `VISION_MODEL` override both.
- `gemini` → `POST {root}/v1beta/models/{model}:generateContent`; local media `inline_data`, YouTube / URLs `file_data.file_uri`, PDF `application/pdf`.
- `openai` → `POST {base}/chat/completions`; `image_url` / `video_url` / `input_audio`.

### Custom provider

Any endpoint speaking one of the two styles works. In `scripts/.env` (name is free, e.g. `openrouter`):

```bash
VISION_PROVIDER=openrouter
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=google/gemini-2.5-flash
OPENROUTER_API_STYLE=openai    # gemini | openai (optional; inferred from host/model)
```

| Variable | Required | Notes |
|---|---|---|
| `VISION_PROVIDER={name}` | yes | active provider |
| `{NAME}_BASE_URL` | yes | OpenAI style includes `/v1` |
| `{NAME}_API_KEY` | yes | `VISION_API_KEY` also accepted |
| `{NAME}_MODEL` | yes | model id |
| `{NAME}_API_STYLE` | no | `gemini` or `openai` |

One-off override without editing `.env`: `--provider <name> --base-url <url> --api-key <key> --model <id>`. `--api-key` leaves the key in shell history and `ps`; prefer `scripts/.env`. Not every OpenAI-compatible gateway handles video/audio; YouTube is only reliable on `gemini` style.

### Common env

| Env | Default | Meaning |
|---|---|---|
| `VISION_PROVIDER` | `cpa` | active provider |
| `VISION_MODEL` / `VISION_BASE_URL` / `VISION_API_STYLE` | — | override the **active** provider only |
| `VISION_MAX_TOKENS` | `32768` | output limit |
| `VISION_SHOW_THINKING` | off | `1` prints thinking before the answer |
| `HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY` | — | HTTP proxy for API calls (first one set wins) |

## Media, proxies, PDF, long video

| Kind | Extensions |
|---|---|
| Image | jpg / png / gif / webp / bmp (SVG: convert to PNG first) |
| Video | mp4 / mov / avi / mkv / webm / flv / wmv / m4v / YouTube |
| Audio | mp3 / wav / flac / m4a / ogg / aac / wma / opus / aiff (wma / aiff are converted to AAC first) |
| PDF | pdf |

Local media is sent as base64. A public URL is passed through and skips base64 and proxies.

**Audio / video are planned, not retried.** One `ffprobe` call reads duration, codec and size; the plan is computed from the per-request budget and printed as `[genius-omni] plan: …`:

| Case | Action |
|---|---|
| H.264 `.mp4/.mov/.m4v` (OpenAI style: also HEVC) or common audio, ≤ budget, ≤ `VISION_MAX_SINGLE_SEC` | upload as-is |
| fits one request at ≥ `VISION_VIDEO_MIN_KBPS` | one proxy, bitrate = budget ÷ duration |
| otherwise | N equal segments, N = ⌈duration ÷ max segment⌉; each segment is encoded straight from the source |

- Video proxy: H.264 (OpenAI style: HEVC first), long edge ≤ `VISION_PROXY_SCALE` (never upscaled), `VISION_PROXY_FPS` fps, mono AAC. Encoder: VideoToolbox on macOS → NVENC/QSV/AMF → `libx264`; a failing encoder is skipped for the rest of the run. Gemini samples video at ~1 fps, so 2 fps keeps text sharp at a low bitrate. An API codec rejection of an as-is upload retries once with a proxy.
- Audio proxy: mono AAC `m4a` at `VISION_PROXY_AUDIO_KBPS`; 64k fits 30 min (`VISION_MAX_SINGLE_SEC`) in ~15MB.
- Image: over `VISION_PROXY_TRIGGER_MB` → JPEG, long edge ≤2048; still too large → 1280.
- Proxies are cached per source file + spec, so a rerun does not re-encode.
- Segments: one API call each, then one synthesis call; `video-frame-analysis` joins segment outputs instead. The index is saved after every segment, so a failed run resumes from the next segment.
- Gateway errors (HTTP 429/5xx, network) retry after 5s / 15s / 30s. A canned refusal (e.g. "content policy") is `PROVIDER_ERROR`, not a result.

PDF: Gemini style sends the whole file in one request when it is ≤ `VISION_PROXY_TRIGGER_MB`. Otherwise (OpenAI-style providers, larger files, or `VISION_PDF_PAGES=1`) `pdftoppm` renders up to `VISION_PDF_MAX_PAGES` pages and each page is analyzed separately. Rendered pages are cached per file.

| Env | Default | Meaning |
|---|---|---|
| `VISION_BUDGET_MB` | `30` | media bytes per request (29.8MB verified on CPA) |
| `VISION_MAX_RAW_MB` | `35` | hard base64 raw limit |
| `VISION_PROXY_FPS` | `2` | video proxy frame rate |
| `VISION_PROXY_SCALE` | `1280` | video proxy long edge |
| `VISION_PROXY_AUDIO_KBPS` | `64` | proxy audio bitrate (mono) |
| `VISION_VIDEO_MIN_KBPS` | `200` | below this, split instead of squeezing |
| `VISION_VIDEO_MAX_KBPS` | `1500` | proxy video bitrate cap |
| `VISION_MAX_SINGLE_SEC` | `1800` | max media seconds per request |
| `VISION_LONG_VIDEO` | `1` | `0` never splits (same as `--no-long-video`) |
| `VISION_PROXY_TRIGGER_MB` | `20` | image downscale / whole-PDF threshold |
| `VISION_PROXY_IMAGE_MAX_EDGE` | `2048` | image proxy long edge |
| `VISION_PDF_PAGES` | off | `1` forces page-by-page PDF |
| `VISION_PDF_MAX_PAGES` | `30` | page mode page limit |
| `VISION_PDF_DPI` | `180` | page mode render DPI |
| `VISION_CACHE_MAX_AGE_DAYS` | `30` | purge proxies/indexes older than N days; `0` disables |

Cache files live under system TEMP (`genius-omni-proxy/`, `genius-omni-index/`). Old files are purged at most once per run; `--cleanup-cache` purges immediately.

## Shot measurement (`measure.py`, `video-shots`)

Every frame is decoded at 32×18 and compared with the previous frame and with the frame half a second back; brightness tracks black. Frame numbers are decode order, times come from each frame's pts (variable frame rate is handled and warned), and timecode starts from the camera tag (drop-frame aware) or 00:00:00:00.

| Boundary | Rule | Result |
|---|---|---|
| `cut` | change ≥6 and ≥3× the local motion level (repeated frames ignored), and ≥60% of pixels changed | confirmed |
| `black` | frames at mean RGB ≤3 inside the clip; the fade in and out (≤1s each side) is one transition, the next shot starts after the black | confirmed |
| `weak-cut` | a spike that misses the cut rule (part of the picture, dark or blended frames) | suspect |
| `gradual` | ≥3 frames of sustained change adding up to a different picture within 2s | suspect |
| `storyboard` | a suspect the model judged a new shot from its before / middle / after frames (the a→b time is given) | confirmed |

Measured: on a built test clip (hard cut, punch-in, 2-frame flash, dissolve, fade through black, jump cut, a hand crossing) all boundaries landed on the exact frame after the storyboard check. On real edits, 19/19, 40/40 sampled and 72/73 confirmed cuts were real (the miss: 7.5 fps webcam footage upconverted to 30 fps). Storyboard frames are grabbed by pts relative to the container start and matched decode order pixel for pixel on five clips, including B-frame and non-zero start files. Labels are drawn with a built-in 5×7 font, so no ffmpeg `drawtext` or fonts are needed. Sheets are cached under `genius-omni-proxy/storyboards/`.

## Verification

- [ ] `python3 scripts/vision.py --check` → `ok`, active provider and model as expected
- [ ] Image: `python3 scripts/vision.py test.png describe`
- [ ] Video: `python3 scripts/vision.py test.mp4 video-summary`
- [ ] Shots: `python3 scripts/measure.py test.mp4` lists shots; `python3 scripts/vision.py test.mp4 video-shots` fills every shot's description and resolves every suspect
- [ ] Audio: `python3 scripts/vision.py test.wav audio-summary`
- [ ] PDF: `python3 scripts/vision.py test.pdf ocr` (whole document) and `VISION_PDF_PAGES=1 …` (pages)
- [ ] Proxies: `--proxy-only` on a large video / long audio / png (expect a `plan=` line, `h264_videotoolbox` on macOS, `.m4a` segments, `.jpg`)
- [ ] Errors: a missing file exits 3 with `INPUT_NOT_FOUND`
