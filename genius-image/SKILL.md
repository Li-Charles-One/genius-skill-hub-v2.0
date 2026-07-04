---
name: genius-image
description: "Generate images using Crun.ai API with 4 model options (gpt-image-2, gpt-image-2-premium, nano-banana-2, nano-banana-pro). Supports single image, batch concurrent generation, async webhook mode, auto-retry on 501 upstream timeouts, and JSONL logging with 10MB rotation / 7-day cleanup. Use when user wants to generate AI images, run multi-model comparisons, or batch-generate from a list of prompts. Triggers on 'genius image', 'crun image', 'batch image generation', or any request to generate images via Crun API."
---

# Genius Image

## Overview

Generate AI images via Crun.ai (https://crun.ai) using async webhook pattern. The script lives in this skill folder, but every normal run must use the current session workspace as `workdir` so outputs land in that workspace's `genius_output/`. Single command can run one image or batch-concurrent multiple images across different models. All complexity (cloudflared tunnel, webhook server, retry logic, log rotation) is hidden from the user.

## Start Here

Classify the request:

- **Single image**: "generate one image with prompt X" → run directly
- **Multi-model compare**: "compare 4 models on prompt X" → auto-generate batch.json
- **Batch generation**: "generate 5 prompts" → auto-generate batch.json
- **Preflight**: first generation request in a session → run `--preflight --no-gen` once
- **Check balance**: "how many credits left" → run with `--balance`
- **Self-test**: "test the skill" → run `<skill_dir>/scripts/test.py`

Inspect the smallest useful evidence:
- User's prompt(s)
- Desired model(s), aspect ratio, resolution (or use defaults)
- Whether comparison/batch mode is needed

## Non-Negotiables

> ⚠️ **#1 常见错误：把输出目录搞错**
>
> 脚本默认把所有产物写入 `<cwd>/genius_output/`。如果 cwd 不是用户工作区，图片会落在错误位置。
>
> **根本解法：始终传 `--out "<workspace>/genius_output"` 明确指定输出目录**，彻底消除 cwd 歧义。
>
> **不知道工作区路径时，直接问用户**——宁可多问一句。

1. **API key from environment**: `CRUN_API_KEY` must be set; never hardcode, never commit
2. **Always use cloudflared tunnel**: webhook mode is required (avoids polling delays and rate limits)
3. **Always clean up tunnel + webhook server**: use `finally` block
4. **JSONL log rotation**: 10MB → archive, 7 days → delete
5. **501 auto-retry**: retry only when completed task payload has `result.code == 501`, up to 3 times, 5s delay
6. **User does not see batch.json**: AI generates and cleans up the file
7. **Do not run self-test before ordinary generation**: run `scripts/test.py` only when the user asks, after editing this skill, or while debugging setup failures
8. **推荐用 `--out` 明确指定输出目录**：直接传绝对路径，彻底消除 workdir 歧义。例如 `--out "C:/Users/jinhu/Documents/workspace/genius_output"`。不传时脚本写入 `<cwd>/genius_output/`，仍需保证 cwd 是用户工作区。
9. **不知道工作区路径时，问用户或使用 `--out`**：不要猜测，宁可多问一句。
10. **Use absolute script paths**: the script is in the skill folder; the output location is controlled by `--out` or `workdir`, not by where the script file lives
11. **Run preflight once per session before the first generation**: `--preflight --no-gen` checks API key, workspace writability, and cloudflared tunnel without creating a task or consuming generation credits
12. **cloudflared must be available before generating**: check `bin/cloudflared.exe` (relative to `<skill_dir>`) or `cloudflared` on PATH. If neither exists, report the missing binary and exit — do not attempt generation without it. Download from https://github.com/cloudflare/cloudflared/releases/latest and place at `<skill_dir>/bin/cloudflared.exe`.
13. **Webhook port 8765 is hardcoded**: if the port is already in use, the script will fail with `Address already in use`. Fix: kill the process occupying 8765 (`netstat -ano | findstr :8765` on Windows), then retry.
14. **回调超时最长 300 秒（5分钟）**：高分辨率或复杂 prompt 的生成任务可能接近5分钟。在长任务开始前告知用户预计等待时间；若 agent runtime 自身有工具调用超时限制，建议优先使用较轻量的模型（如 `gpt-image-2` 或 `nano-banana-2-lite`）或降低分辨率。

## Path Resolution

**`<skill_dir>`** = the directory containing this SKILL.md file. The agent must resolve it at runtime before running any command. Examples:
- ZCode / Kiro / OpenCode: use the skill's install path (e.g. `~/.zcode/skills/genius-image/`)
- Hermes / Reasonix: the path where this SKILL.md was loaded from
- When unsure: run `find ~/.config ~/.zcode ~/.hermes ~/.reasonix -name "genius-image" -type d 2>/dev/null | head -1`

Use `<skill_dir>` in all script paths below. Never hardcode a user-specific absolute path.

## Workflow

> 下方命令均使用 `<skill_dir>` 指向脚本，用 `<workspace>` 指向用户工作区。**推荐始终传 `--out "<workspace>/genius_output"` 明确指定输出路径，避免 cwd 问题。** `<skill_dir>` 见上方 Path Resolution 说明。

### Single image
```bash
# 推荐：用 --out 明确指定输出目录，彻底消除 workdir 歧义
python "<skill_dir>/scripts/genius.py" "一只可爱的小猫" --model gpt-image-2 --aspect 16:9 --resolution 1K --out "<workspace>/genius_output"
```

### 参考图 / 图生图（--ref）
`--ref` 接受一张或多张参考图，用于保持人物 / 风格一致性（如角色转面、同一个人多角度）。每一项可以是：
- **http(s) URL** —— 原样传给 API
- **本地文件路径** —— 脚本自动读取并编码成 `data:image/...;base64,...`（API 只收 URL 或 base64，本地路径会被自动转换，无需手动处理）

```bash
# 本地图（自动转 base64）
python "...\genius.py" "同一个人的 3x3 九宫格多角度转面图" --model nano-banana-pro --aspect 16:9 --resolution 1K --ref "genius_output\some_photo.png"
# 远程 URL，或多张混用
python "...\genius.py" "..." --ref "https://example.com/a.png" "genius_output\b.png"
```
> 注意：base64 会让请求体增大约 33%，传超大图或多张参考图时 body 可能偏大。需要稳定时优先用 http(s) URL。本地文件找不到会直接报错，不会把无效路径丢给服务端。batch.json 里对应字段是 `ref`（数组）或兼容写法 `img_urls`。

### Preflight (once per session)
```bash
python "<skill_dir>/scripts/genius.py" --preflight --no-gen --out "<workspace>/genius_output"
```

### Batch (auto-generate config)
AI creates `batch_<timestamp>.json` in the **`genius_output/Tmp/` subdirectory** (clearly separated from artifacts), runs, then deletes the file:
```bash
# AI writes: <workspace>/genius_output/Tmp/batch_<timestamp>.json
# AI runs:
python "<skill_dir>/scripts/genius.py" --batch <workspace>/genius_output/Tmp/batch_<timestamp>.json --concurrent 3 --out "<workspace>/genius_output"
# AI deletes the batch file immediately after
```
**Always** put batch.json in `genius_output/Tmp/` — never in the working directory root, and never alongside the generated images.

#### batch.json 格式

顶层是一个**任务数组**（不是带 `concurrent`/`tasks` 包装的对象）。并发数由命令行 `--concurrent` 控制，不写在文件里。每个任务对象至少要有 `prompt`，其余字段（`model`/`aspect`/`resolution` 等）可选，缺省走默认值：

```json
[
  { "prompt": "一只可爱的小猫", "model": "nano-banana-pro", "aspect": "16:9", "resolution": "2K" },
  { "prompt": "赛博朋克城市夜景", "model": "gpt-image-2", "aspect": "1:1", "resolution": "1K" }
]
```

> 也兼容 `{ "tasks": [ ... ] }` 包装写法，但推荐用纯数组。顶层若不是数组也不是含 `tasks` 的对象，脚本会直接报错提示格式。

## Project Directory Structure

所有产物（图片、日志、临时 batch）都落在 `workdir` 指向的用户工作区下，**不是 skill 自己的目录**：

```
<user_workspace>/genius_output/     ← 这里的 <user_workspace> 就是 workdir
├── Tmp/                            ← temporary batch configs (deleted after run)
├── Logs/                           ← JSONL logs (current + auto-archived)
│   ├── genius_log.jsonl
│   └── genius_log_YYYYMMDD_HHMMSS.jsonl
└── *.png                           ← generated images
```

### Check balance
```bash
python "<skill_dir>/scripts/genius.py" --balance
```

### Self-test
```bash
python "<skill_dir>/scripts/test.py"
```

## Models

| Key | Crun ID | Resolutions | Special params |
|---|---|---|---|
| `gpt-image-2` | `openai/gpt-image-2` | 1K/2K/4K | — |
| `gpt-image-2-stable` | `openai/gpt-image-2-stable` | — | `--quality` / `--background` (transparent/**唯一支持透明背景**) / `--moderation` / `--output-format`（default webp） |
| `gpt-image-2-premium` | `openai/gpt-image-2-premium` | 1K/2K/4K | `--quality`（low/medium/high，default medium） |
| `nano-banana-2` | `google/nano-banana-2` | 1K/2K/4K | `--google-search` / `--output-format` |
| `nano-banana-2-lite` | `google/nano-banana-2-lite` | — | 轻量版，max 10张参考图，无 resolution |
| `nano-banana-pro` | `google/nano-banana-pro` | 1K/2K/4K | `--output-format` |

**选型指引：**
- 速度优先 / 省积分 → `gpt-image-2`
- 需要**透明背景**或 webp 输出 → `gpt-image-2-stable`
- 高质量写实，可控质量档位 → `gpt-image-2-premium`
- 超长 prompt（最多20000字符）/ 需要谷歌搜索增强 → `nano-banana-2`
- 轻量快速，无需高分辨率 → `nano-banana-2-lite`
- 参考图贴合度最高（图生图） → `nano-banana-pro`

## Resource Map

- `scripts/genius.py`: main script (single + batch + balance)
- `scripts/test.py`: lightweight health checks (run on request, after edits, or when debugging)
- `bin/cloudflared.exe`: tunnel binary (Windows, ~54MB) — **not in repo**, download from https://github.com/cloudflare/cloudflared/releases/latest and place at `bin/cloudflared.exe` (or have `cloudflared` on PATH)
- `references/usage.md`: detailed usage with examples
- `references/troubleshooting.md`: common errors and fixes
- `evals/evals.json`: test prompts and expected behavior

## Error Reference

| 错误码 | 含义 | 应对策略 |
|:--|:--|:--|
| `401` | API Key 无效或缺失 | 检查 `CRUN_API_KEY` 环境变量是否正确设置 |
| `402` | 积分不足 | 告知用户充值，可先用 `--balance` 查询当前余额 |
| `403` | API Key 已禁用 | 联系 Crun.ai 支持，Key 可能被封禁 |
| `404` | 任务不存在 | `task_id` 有误，用 `--balance` 或重新提交 |
| `422` | 参数校验错误 | 检查 prompt/aspect/resolution 是否符合模型限制 |
| `429` | 触发速率限制 | 等待后重试，批量任务降低 `--concurrent` |
| `455` | 服务维护中 | 等待数分钟后重试，无需修改参数 |
| `500` | 服务器内部错误 | 等待数分钟后重试一次 |
| `501` | 生成失败 | 脚本会自动重试最多3次；持续失败可换模型或简化 prompt |
| `505` | 功能已禁用 | 该模型或功能当前不可用，换其他模型 |

## Output Contract

Always report:
- **Output location confirmation**: 文件必须落在 `<user_workspace>/genius_output/`，不是 skill 目录
- **Models used** and their order
- **Total duration** per model
- **File paths** in `genius_output/`
- **Task IDs and media URLs** from log `genius_output/Logs/genius_log.jsonl`
- **Credits consumed** (from log `genius_output/Logs/genius_log.jsonl`)
- **Cleanup status** (tunnel closed, batch.json deleted)

## Final Response

Report: what was generated, where files live, credits spent, and any failures with retry status.
