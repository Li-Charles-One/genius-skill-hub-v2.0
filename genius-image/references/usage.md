# Genius Image Usage

## Setup

### 1. Set API key (one time, permanent)

PowerShell (admin or user level):
```powershell
[System.Environment]::SetEnvironmentVariable("CRUN_API_KEY", "your_key_here", "User")
```

Restart PowerShell after this.

Verify:
```powershell
echo $env:CRUN_API_KEY
```

### 2. Test the skill only when needed

```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\test.py"
```

Expected: all lightweight checks pass. Do not run this before every generation; run it after editing the skill or when debugging setup.

## Usage

### Preflight once per session
Checks API key, workspace writability, and cloudflared tunnel without creating a generation task:
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" --preflight --no-gen
```

### Single image
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" "a cute cat" --model gpt-image-2 --aspect 16:9
```

### Single image with reference
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" "same cat in winter" --ref https://example.com/cat.jpg
```

### 4-model comparison (batch)
Create `genius_output/Tmp/batch_<timestamp>.json` in the current workspace:
```json
[
  {"prompt": "a cute cat", "model": "gpt-image-2"},
  {"prompt": "a cute cat", "model": "gpt-image-2-premium", "resolution": "2K", "quality": "high"},
  {"prompt": "a cute cat", "model": "nano-banana-2"},
  {"prompt": "a cute cat", "model": "nano-banana-2-lite"}
]
```
Run:
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" --batch genius_output/Tmp/batch_20260622_120000.json --concurrent 4
```

### Check credit balance
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" --balance
```

## Output

All images go to `./genius_output/` in the **current working directory** (`workdir` in the tool call). The script path can be absolute and still write outputs to the current workspace. Use `--out DIR` to change:
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" "a cute cat" --out D:\my_images
```
```
genius_output/
├── gpt-image-2_a_cute_cat_1.png
├── gpt-image-2-premium_a_cute_cat_1.png
├── nano-banana-2_a_cute_cat_1.png
└── nano-banana-2-lite_a_cute_cat_1.png
```

Naming: `{model}_{prompt前30字}_{序号}.{ext}`
- Same model+prompt → auto-incrementing suffix (_1, _2, _3...)
- Different model or prompt → independent counter

## Logs

`genius_output/Logs/genius_log.jsonl` (current)
`genius_output/Logs/genius_log_YYYYMMDD_HHMMSS.jsonl` (archived when >10MB)

Each line is one JSON object. Success rows include `task_id` and `media_urls` so you can locate the Crun task later even though hosted media URLs usually expire:
```json
{"timestamp": "2026-06-22T12:40:17", "task_id": "abc...", "model": "gpt-image-2", "prompt": "...", "duration_s": 52.3, "credits": 4, "file_path": "...", "media_urls": ["https://..."], "status": "success"}
```

Archives older than 7 days are auto-deleted on next run.

## Parameters

| Param | Default | Description |
|---|---|---|
| `prompt` | (required) | Image description |
| `--model` | `gpt-image-2` | Model key (see SKILL.md table) |
| `--aspect` | `1:1` | Aspect ratio (15 options) |
| `--resolution` | `1K` | 1K/2K/4K (depends on model; lite has none) |
| `--quality` | `medium` | Only `gpt-image-2-premium`: low/medium/high |
| `--ref` | - | Reference image URLs (1-16, model-dependent) |
| `--google-search` | false | Only `nano-banana-2`: enable Google Search |
| `--output-format` | `png` | Only `nano-banana-2`: png/jpg/webp |
| `--batch` | - | Batch JSON file path |
| `--concurrent` | 5 | Max concurrent submissions |
| `--balance` | - | Just check credit balance |
