# Troubleshooting

## `ERROR: set $env:CRUN_API_KEY first`

API key not in environment. Set it:
```powershell
[System.Environment]::SetEnvironmentVariable("CRUN_API_KEY", "your_key", "User")
```
Restart PowerShell.

## `ERROR: cloudflared not found at ...`

The `bin/cloudflared.exe` file is missing. Re-download:
```powershell
Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile "bin/cloudflared.exe"
```

## `cloudflared 60 秒内未拿到公网 URL`

Network issue. Check:
- Is your proxy (TUN mode) on? Cloudflared needs outbound access
- Try: `bin\cloudflared.exe tunnel --url http://localhost:8765 --no-autoupdate` manually to see logs

## `submit fail [401]: API Key 无效`

Key invalid or revoked. Get a new one at https://crun.ai/user-api-key

## `submit fail [402]: 积分不足`

Out of credits. Top up at https://crun.ai

## `submit fail [422]: 参数错误`

Model doesn't support this parameter. Check:
- Defaults: fast → `nano-banana-2-lite`; complex/design → `gpt-image-2`
- Also available: `gpt-image-2-premium`, `nano-banana-2`
- Resolutions: `1K`/`2K`/`4K` where supported (`nano-banana-2-lite` has no resolution)
- `--quality` only works with `gpt-image-2-premium`
- `--google-search` / `--output-format` only work with `nano-banana-2`

## `任务失败: 501 generation failed`

Upstream API timeout (OpenAI/Google). The script auto-retries up to 3 times only when the completed task payload has `result.code == 501`. If still failing:
- Wait 10-30 minutes (upstream load)
- Try a different model
- Simplify the prompt

## Webhook never received

Check:
- cloudflared tunnel is running (look for "公网 URL" line)
- callback_url is correctly passed to Crun
- Try `bin\cloudflared.exe tunnel --url http://localhost:8765` in another terminal to see real-time logs

Script also polls TaskInfo every 30s while waiting. If webhook is flaky, look for `[poll]` lines. After timeout, use:
```bash
python -u scripts/genius.py --fetch-task "<task_id>" --out "<workspace>/genius_output"
```

## Agent looks hung / no output for minutes

Causes:
- stdout fully buffered (agent shell) — always run with `python -u`
- long cloud generation (up to 300s callback window)
- tunnel/proxy issues — prefer `--poll-only`

Expected healthy wait logs every ~15s:
```
[wait/poll-only] abcd1234... still waiting  elapsed=15s  remaining≈285s
[poll] abcd1234... TaskInfo status=running
```

If the agent aborts mid-wait: cloud task may still succeed. Find `task_id` from:
- stdout line `task_id: ...`
- `GENIUS_RESULT` line
- `genius_output/Logs/genius_log.jsonl` entry with `"status":"submitted"`

Then recover with `--fetch-task`.

## Port already in use / tunnel fails

Use:
```bash
python -u scripts/genius.py "..." --poll-only --out "<workspace>/genius_output"
```
Or set `--port 8770` (auto-tries next free ports if busy).

## File naming shows weird characters

Prompt is non-English. The script keeps alphanumeric (which includes Chinese) and replaces punctuation with `_`. If you see garbled text, check the prompt encoding.

## Batch used to wait for the slowest task before any download

Fixed: batch now downloads each image as soon as its TaskInfo is `success` (stream settle). You still see one process until the deadline for stragglers, but finished files appear in `genius_output/` immediately and emit `GENIUS_RESULT` one-by-one. Timed-out tasks: `--fetch-task <id>`.

## Concurrent batch fails partially

The 501 auto-retry handles generation failures. If a task fails after 3 retries, check the log:
```bash
cat genius_output/genius_log.jsonl | grep failed
```
