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

## Model defaults

| Need | Model |
|---|---|
| 快速出图 / 草稿 | `nano-banana-2-lite`（CLI 默认） |
| 复杂画面 / 高设计感 | `gpt-image-2` |

## Usage

### Preflight once per session
Checks API key, workspace writability, and cloudflared tunnel without creating a generation task:
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" --preflight --no-gen --poll-only
```

### Single image — fast (lite)
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" "a cute cat" --model nano-banana-2-lite --aspect 16:9 --poll-only --name "cute-cat"
```

### Single image — complex / design (gpt-image-2)
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" "cyberpunk night market, multi-layer depth, cinematic composition" --model gpt-image-2 --aspect 16:9 --resolution 1K --poll-only --name "cyberpunk-market"
```

### Single image with reference
```bash
# fast iteration
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" "same cat in winter" --model nano-banana-2-lite --ref https://example.com/cat.jpg --poll-only
# high-design img2img
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" "same subject, poster layout" --model gpt-image-2 --resolution 1K --ref https://example.com/cat.jpg --poll-only
```

### Dual-default comparison (batch)
Create `genius_output/Tmp/batch_<timestamp>.json` in the current workspace:
```json
[
  {"prompt": "a cute cat", "model": "nano-banana-2-lite", "name": "cat-lite"},
  {"prompt": "a cute cat", "model": "gpt-image-2", "resolution": "1K", "name": "cat-gpt"}
]
```
Run:
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" --batch genius_output/Tmp/batch_20260622_120000.json --concurrent 2 --poll-only
```

### Check credit balance
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" --balance
```

## Output

All images go to `./genius_output/` in the **current working directory** (`workdir` in the tool call). The script path can be absolute and still write outputs to the current workspace. Use `--out DIR` to change:
```bash
python "C:\Users\jinhu\.config\opencode\skills\genius-image\scripts\genius.py" "a cute cat" --model nano-banana-2-lite --out D:\my_images
```
```
genius_output/
├── cute-cat.png
└── cyberpunk-market.png
```

Naming: prefer `--name "短名"`；否则 `{model}_{prompt前30字}_{序号}.{ext}`
- Same model+prompt → auto-incrementing suffix (_1, _2, _3...)
- Different model or prompt → independent counter

## Logs

`genius_output/Logs/genius_log.jsonl` (current)
`genius_output/Logs/genius_log_YYYYMMDD_HHMMSS.jsonl` (archived when >10MB)

Each line is one JSON object. Success rows include `task_id` and `media_urls` so you can locate the Crun task later even though hosted media URLs usually expire:
```json
{"timestamp": "2026-06-22T12:40:17", "task_id": "abc...", "model": "nano-banana-2-lite", "prompt": "...", "duration_s": 8.2, "credits": 1, "file_path": "...", "media_urls": ["https://..."], "status": "success"}
```

Archives older than 7 days are auto-deleted on next run.

## Parameters

| Param | Default | Description |
|---|---|---|
| `prompt` | (required) | Image description |
| `--model` | `nano-banana-2-lite` | 快用 lite；复杂/设计用 `gpt-image-2`（见 SKILL.md） |
| `--aspect` | model default | Aspect ratio |
| `--resolution` | model default | 1K/2K/4K（lite 不支持） |
| `--quality` | `medium` | Only `gpt-image-2-premium`: low/medium/high |
| `--ref` | - | Reference image URLs or local paths |
| `--google-search` | false | Only `nano-banana-2` |
| `--output-format` | `png` | Only `nano-banana-2`: png/jpg/webp |
| `--name` | - | Output basename without extension |
| `--poll-only` | false | Agent-recommended: poll TaskInfo only |
| `--batch` | - | Batch JSON file path |
| `--concurrent` | 5 | Max concurrent submissions |
| `--balance` | - | Just check credit balance |
