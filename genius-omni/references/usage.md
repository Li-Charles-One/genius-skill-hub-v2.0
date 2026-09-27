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

Verify with `python3 scripts/vision.py --check`. `pdftoppm` (poppler) is only needed for MiMo or page-mode PDF. The script uses only the Python standard library (3.9+).

## Usage

`<skill_dir>` = directory of this SKILL.md (OpenCode: `~/.config/opencode/skills/genius-omni/`). On Windows replace `python3` with `python`. ZCode / Hermes may call their built-in `vision_analyze` with a mode-specific prompt instead.

```bash
python3 "<skill_dir>/scripts/vision.py" <file_path_or_url> <mode> [--output json|text]

# Images
python3 "<skill_dir>/scripts/vision.py" screenshot.png ui-review
python3 "<skill_dir>/scripts/vision.py" document.jpg ocr --output json
python3 "<skill_dir>/scripts/vision.py" before.png compare --compare-with after.png

# Video / YouTube (local ≥15 min is segmented automatically)
python3 "<skill_dir>/scripts/vision.py" meeting.mp4 video-summary
python3 "<skill_dir>/scripts/vision.py" lecture-2h.mp4 video-summary --no-long-video
python3 "<skill_dir>/scripts/vision.py" "https://www.youtube.com/watch?v=..." video-summary

# Audio
python3 "<skill_dir>/scripts/vision.py" interview.wav audio-transcribe
python3 "<skill_dir>/scripts/vision.py" clip.mp3 describe          # → audio-summary

# PDF
python3 "<skill_dir>/scripts/vision.py" report.pdf ocr
VISION_PDF_PAGES=1 python3 "<skill_dir>/scripts/vision.py" scan.pdf ocr   # force page-by-page

# Oversize media: only build the analysis proxy (no API call)
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
# optional overrides:
# CPA_MODEL=gemini-3.8-flash-high
# CPA_BASE_URL=https://cpa-jp.charles-ai.space/v1

# Optional: MiMo
# MIMO_API_KEY=tp-your-token-plan-key
# MIMO_MODEL=mimo-v2.6-flash
```

The first existing file wins: `scripts/.env`, then `~/.hermes/.env`. Process environment variables override both. `--check` and `--list-providers` show the model that requests will actually use.

## Output

Text mode (default) prints `## <Mode> Analysis` followed by the model's markdown. `--output json` prints `{"mode": ..., "file": ..., "result": ...}`. Local audio/video results end with a `⏱ 时长校验` footer comparing the ffprobe duration with the duration the model claims.

Failures go to stderr as `Error [CODE]: message`:

| Code | Exit | Typical cause |
|---|---|---|
| `INPUT_NOT_FOUND` | 3 | local file does not exist |
| `UNSUPPORTED_FORMAT` | 4 | mode does not fit the media (e.g. `audio-transcribe` on an image) |
| `DEPENDENCY_MISSING` | 5 | `ffmpeg` / `ffprobe` / `pdftoppm` not on PATH |
| `PROVIDER_ERROR` | 6 | unknown provider, missing key, HTTP error, network failure |
| `TIMEOUT` | 7 | no API response in time, or an ffmpeg step timed out |

Other errors exit 1; `--check` with missing tools exits 2.

## Providers

| Provider | API style | Default model | Base URL | Key env |
|---|---|---|---|---|
| **`cpa`（默认）** | `gemini` native | `gemini-3.8-flash-high` | `https://cpa-jp.charles-ai.space/v1` | `CPA_API_KEY` |
| `mimo` | `openai` | `mimo-v2.6-flash` | `https://token-plan-cn.xiaomimimo.com/v1` | `MIMO_API_KEY` |

- `gemini` → `POST {root}/v1beta/models/{model}:generateContent`; local media `inline_data`, YouTube / URLs `file_data.file_uri`, PDF `application/pdf`.
- `openai` → `POST {base}/chat/completions`; `image_url` / `video_url` / `input_audio`.
- MiMo thinking is forced on (`"thinking": {"type": "enabled"}`) and cannot be disabled. `mimo-v2.5-pro` cannot see or hear; `mimo-v2.6-pro` is unverified.

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

One-off override without editing `.env`: `--provider <name> --base-url <url> --api-key <key> --model <id>`. Not every OpenAI-compatible gateway handles video/audio; YouTube is only reliable on `gemini` style.

### Common env

| Env | Default | Meaning |
|---|---|---|
| `VISION_PROVIDER` | `cpa` | active provider |
| `VISION_MODEL` / `VISION_BASE_URL` / `VISION_API_STYLE` | — | override the **active** provider only |
| `VISION_MAX_TOKENS` | `32768` | output limit |
| `VISION_SHOW_THINKING` | off | `1` prints thinking before the answer |
| `VISION_VIDEO_FPS` / `VISION_VIDEO_RESOLUTION` | `2` / `default` | MiMo video sampling |
| `HTTPS_PROXY` / `HTTP_PROXY` / `ALL_PROXY` | — | HTTP proxy for API calls (first one set wins) |

## Media, proxies, PDF, long video

| Kind | Extensions |
|---|---|
| Image | jpg / png / gif / webp / bmp (SVG: convert to PNG first) |
| Video | mp4 / mov / avi / mkv / webm / flv / wmv / m4v / YouTube |
| Audio | mp3 / wav / flac / m4a / ogg / aac / wma / opus |
| PDF | pdf |

Local media is sent as base64 (raw ≤35MB, leaving headroom under MiMo's ~50MB encoded limit). A public URL is passed through and skips base64 and proxies (MiMo: video ≤300MB, audio ≤100MB).

Local media over `VISION_PROXY_TRIGGER_MB` is compressed into an analysis proxy (not a master):

| Kind | Strategy |
|---|---|
| Video | `hevc_qsv/nvenc/amf` → `h264_qsv/nvenc/amf` → `libx264`, width 1280, then 720p / 480p. Gemini style prefers H.264; an API codec rejection retries once with H.264. No AV1 (MiMo base64 often rejects it). |
| Audio | AAC `m4a` at `VISION_PROXY_AUDIO_K`; still too large → 32k mono |
| Image | JPEG, long edge ≤2048; still too large → 1280 |

PDF: Gemini style sends the whole file in one request when it is ≤ the proxy trigger size. Otherwise (MiMo, larger files, or `VISION_PDF_PAGES=1`) `pdftoppm` renders up to `VISION_PDF_MAX_PAGES` pages and each page is analyzed separately. Rendered pages are cached per file.

Long video: local video ≥ `VISION_LONG_VIDEO_SEC` is cut into `VISION_LONG_SEGMENT_SEC` segments (one API call each plus one synthesis call). Notes are indexed per file and mode, so a rerun only synthesizes.

| Env | Default | Meaning |
|---|---|---|
| `VISION_PROXY_TRIGGER_MB` | `20` | compress above this size |
| `VISION_MAX_RAW_MB` | `35` | base64 raw upload limit |
| `VISION_PROXY_SCALE` | `1280` | video proxy width |
| `VISION_PROXY_AUDIO_K` | `64k` | audio proxy bitrate |
| `VISION_PROXY_IMAGE_MAX_EDGE` | `2048` | image proxy long edge |
| `VISION_PDF_PAGES` | off | `1` forces page-by-page PDF |
| `VISION_PDF_MAX_PAGES` | `30` | page mode page limit |
| `VISION_PDF_DPI` | `180` | page mode render DPI |
| `VISION_LONG_VIDEO` | `1` | `0` disables segmentation (same as `--no-long-video`) |
| `VISION_LONG_VIDEO_SEC` | `900` | segmentation threshold |
| `VISION_LONG_SEGMENT_SEC` | `300` | segment length (min 60) |
| `VISION_CACHE_MAX_AGE_DAYS` | `30` | purge proxies/indexes older than N days; `0` disables |

Cache files live under system TEMP (`genius-omni-proxy/`, `genius-omni-index/`). Old files are purged at most once per run; `--cleanup-cache` purges immediately.

## Verification

- [ ] `python3 scripts/vision.py --check` → `ok`, active provider and model as expected
- [ ] Image: `python3 scripts/vision.py test.png describe`
- [ ] Video: `python3 scripts/vision.py test.mp4 video-summary`
- [ ] Audio: `python3 scripts/vision.py test.wav audio-transcribe`
- [ ] PDF: `python3 scripts/vision.py test.pdf ocr` (whole document) and `VISION_PDF_PAGES=1 …` (pages)
- [ ] MiMo: `python3 scripts/vision.py test.png describe --provider mimo`
- [ ] Proxies: `--proxy-only` on a large video / wav / png (expect `h264_*`/`hevc_*`/`libx264`, `.m4a`, `.jpg`)
- [ ] Errors: a missing file exits 3 with `INPUT_NOT_FOUND`
