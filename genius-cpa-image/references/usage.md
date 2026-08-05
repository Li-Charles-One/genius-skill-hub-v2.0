# Genius CPA Image — Official generateContent

## Endpoint

```text
POST {CPA_JP_BASE}/v1beta/models/gemini-3.1-flash-image:generateContent
Authorization: Bearer $CPA_JP_API_KEY
```

## Body shape

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

## CLI mapping

| CLI | Body |
|---|---|
| prompt | `contents[0].parts[0].text` |
| `--aspect` | `generationConfig.imageConfig.aspectRatio` |
| `--resolution` | `generationConfig.imageConfig.imageSize` |
| `--ref` | extra `inlineData` parts |
| `--google-search` | `tools: [{google_search:{}}]` |

## Secrets

优先级：进程环境变量 > skill 本地 `.env`。

本地文件（任选其一，gitignored）：

- `.env`
- `scripts/.env`
- `Genius_cpa_image.env`

```bash
cp .env.example .env
# CPA_JP_API_KEY=sk-...
# CPA_JP_BASE=https://cpa-jp.charles-ai.space   # optional
```

## Examples

```bash
# Option A: skill-local .env (recommended)
# Option B: export CPA_JP_API_KEY=sk-...

python3 -u scripts/cpa_image.py "minimal blue icon" \
  --aspect 1:1 --resolution 1K --name demo --out ./genius_output

python3 -u scripts/cpa_image.py "wide landscape" \
  --aspect 16:9 --resolution 2K --out ./genius_output
```

## Errors: model_cooldown / 429

CPA may return:

```json
{
  "error": {
    "code": "model_cooldown",
    "message": "All credentials for model ... are cooling down ...",
    "reset_time": "3h39m42s",
    "reset_seconds": 13183
  }
}
```

Skill policy:

- **Do not retry** `HTTP 429` / `model_cooldown`
- Fail immediately and print `reset_time` / `reset_seconds`
- Only retry transient network exceptions

Example surface error:

```text
HTTP 429 code=model_cooldown model=gemini-3.1-flash-image provider=antigravity reset_time=3h39m42s reset_seconds=13183 message=...
```

## Local async jobs

Client-side background workers (not a server job API).

```bash
# submit and return immediately
python3 -u scripts/cpa_image.py "neon alley" \
  --aspect 16:9 --resolution 1K --name neon --async --out ./genius_output
# GENIUS_RESULT status=queued job_id=... mode=async-local

python3 -u scripts/cpa_image.py --status cpa-YYYYMMDD_HHMMSS-xxxxxxxx --out ./genius_output
python3 -u scripts/cpa_image.py --wait cpa-YYYYMMDD_HHMMSS-xxxxxxxx --timeout 600 --out ./genius_output
python3 -u scripts/cpa_image.py --list-jobs --out ./genius_output

# async batch
python3 -u scripts/cpa_image.py --batch ./genius_output/Tmp/batch.json \
  --async --concurrent 3 --out ./genius_output
```

Artifacts:

| Path | Meaning |
|---|---|
| `genius_output/Jobs/<job_id>.json` | status / result / error |
| `genius_output/Jobs/<job_id>.log` | detached worker stdout/stderr |
| `genius_output/*_N.jpg` | final image(s) |
