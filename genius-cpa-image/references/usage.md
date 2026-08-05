# Genius CPA Image — Multi-provider

## Providers

### JP · Gemini generateContent

```text
POST {CPA_JP_BASE}/v1beta/models/gemini-3.1-flash-image:generateContent
Authorization: Bearer $CPA_JP_API_KEY
```

Body:

```json
{
  "contents": [{
    "role": "user",
    "parts": [
      {"text": "a red apple"},
      {"inlineData": {"mimeType": "image/png", "data": "<base64>"}}
    ]
  }],
  "generationConfig": {
    "responseModalities": ["IMAGE"],
    "imageConfig": {
      "aspectRatio": "16:9",
      "imageSize": "2K"
    }
  },
  "tools": [{"google_search": {}}]
}
```

### US · OpenAI images (gpt-image-2)

```text
POST {CPA_US_BASE}/v1/images/generations
Authorization: Bearer $CPA_US_API_KEY
```

```json
{
  "model": "gpt-image-2",
  "prompt": "minimal blue icon",
  "size": "1024x1024",
  "n": 1,
  "quality": "low",
  "output_format": "png"
}
```

With `--ref` → `POST /v1/images/edits` (multipart `image` / `image[]` + prompt).

## CLI mapping

| CLI | Gemini | gpt-image-2 (CPA-US) |
|---|---|---|
| prompt | `contents.parts.text` | `prompt` |
| `--aspect` | `imageConfig.aspectRatio` | maps to fixed 1K `size` (1:1 3:2 2:3 4:3 3:4 5:4 4:5 16:9 9:16 21:9 9:21 2:1 1:2 auto) |
| `--resolution` | `imageConfig.imageSize` 0.5K–4K | only **1K/auto** real；2K/4K coerce→1K |
| `--size` | n/a | CPA 1K presets only；legacy 2K/4K sizes remap to same-aspect 1K |
| `--quality` | **rejected** | `quality`（画质/耗时，不抬像素） |
| `--output-format` | **rejected** | `output_format` |
| `--ref` | inlineData parts | images/edits |
| `--google-search` | tools.google_search | **rejected** |

gpt-image-2 CPA-US 1K size matrix (observed 2026-08-05):

| aspect | size |
|---|---|
| 1:1 | 1024x1024 |
| 16:9 | 1672x941 |
| 9:16 | 941x1672 |
| 4:3 | 1443x1090 |
| 3:4 | 1090x1443 |
| 3:2 | 1536x1024 |
| 2:3 | 1024x1536 |
| 5:4 | 1408x1120 |
| 4:5 | 1120x1408 |
| 21:9 | 1920x832 |
| 9:21 | 832x1920 |
| 2:1 | 1792x896 |
| 1:2 | 896x1792 |
| auto | auto |

Coerce examples (both print `[note]`):

- `--resolution 4K --aspect 16:9` → size `1672x941`, resolution field becomes `1K`
- `--size 3840x2160` → `1672x941` (legacy OpenAI-style sizes remap to same-aspect 1K)

`quality` low|medium|high only changes fidelity/latency, **not** pixels. For true 2K/4K use Gemini.

After save, skill reports `actual_size` from image bytes.

## Secrets

优先级：进程环境变量 > skill 本地 `.env`。

```bash
cp .env.example .env
# CPA_JP_API_KEY=...
# CPA_US_API_KEY=...
# CPA_JP_BASE=https://cpa-jp.charles-ai.space
# CPA_US_BASE=https://cpa.charles-ai.space
```

## Examples

```bash
# Gemini JP
python3 -u scripts/cpa_image.py "minimal blue icon" \
  --aspect 1:1 --resolution 1K --name demo --out ./genius_output

# gpt-image-2 US (1K only)
python3 -u scripts/cpa_image.py "minimal blue icon" \
  --model gpt-image-2 --aspect 1:1 --quality low --name demo-gpt \
  --out ./genius_output

# 16:9 → 1672x941
python3 -u scripts/cpa_image.py "wide seascape" \
  --model gpt-image-2 --aspect 16:9 --resolution 1K --quality medium \
  --out ./genius_output

# direct CPA 1K preset
python3 -u scripts/cpa_image.py "portrait" \
  --model gpt-image-2 --size 1024x1536 --quality medium \
  --out ./genius_output

# Prefer Gemini for real high-res
python3 -u scripts/cpa_image.py "landscape" \
  --aspect 16:9 --resolution 4K --name landscape-4k \
  --out ./genius_output

# legacy only (will [note] coerce — do not use as default example)
# --model gpt-image-2 --size 3840x2160  → 1672x941
# --model gpt-image-2 --aspect 16:9 --resolution 4K  → 1672x941 + note
```

## Errors: model_cooldown / 429 / auth_unavailable

Skill policy:

- **Do not retry** `HTTP 429` / `model_cooldown` / `auth_unavailable`
- Fail immediately and print `reset_time` / `reset_seconds` when present
- Only retry transient network exceptions

## Local async jobs

Client-side background workers (not a server job API).

```bash
python3 -u scripts/cpa_image.py "neon alley" \
  --model gpt-image-2 --aspect 1:1 --quality low --name neon \
  --async --out ./genius_output

python3 -u scripts/cpa_image.py --status cpa-YYYYMMDD_HHMMSS-xxxxxxxx --out ./genius_output
python3 -u scripts/cpa_image.py --wait cpa-YYYYMMDD_HHMMSS-xxxxxxxx --timeout 600 --out ./genius_output
python3 -u scripts/cpa_image.py --list-jobs --out ./genius_output
```

Artifacts:

| Path | Meaning |
|---|---|
| `genius_output/Jobs/<job_id>.json` | status / result / error |
| `genius_output/Jobs/<job_id>.log` | detached worker stdout/stderr |
| `genius_output/*_N.png` | final image(s) |

## Log rotation

Main log and async job artifacts are rotated/pruned automatically.

| Target | Default |
|---|---|
| `Logs/cpa_image_log.jsonl` | rotate at **10 MB** → `cpa_image_log_YYYYMMDD_HHMMSS.jsonl` |
| Main archives | keep **7 days**, max **20** files |
| `Jobs/<id>.log` | rotate at **5 MB** |
| Job json/log | keep **7 days**, max **100** status files |

Override via env / skill `.env`:

```bash
CPA_IMAGE_LOG_MAX_MB=10
CPA_IMAGE_LOG_KEEP_DAYS=7
CPA_IMAGE_LOG_MAX_ARCHIVES=20
CPA_IMAGE_JOB_LOG_MAX_MB=5
CPA_IMAGE_JOB_KEEP_DAYS=7
CPA_IMAGE_JOB_MAX_FILES=100
```
