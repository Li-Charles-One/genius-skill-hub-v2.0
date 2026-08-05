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

## Examples

```bash
export CPA_JP_API_KEY=sk-...

python3 -u scripts/cpa_image.py "minimal blue icon" \
  --aspect 1:1 --resolution 1K --name demo --out ./genius_output

python3 -u scripts/cpa_image.py "wide landscape" \
  --aspect 16:9 --resolution 2K --out ./genius_output
```
