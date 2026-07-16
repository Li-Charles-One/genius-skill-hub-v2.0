---
name: genius-image
description: "Generate images using Crun.ai API. Default models: nano-banana-2-lite (fast) and gpt-image-2 (complex/high design). Also supports gpt-image-2-premium and nano-banana-2. Single/batch, webhook or --poll-only, TaskInfo recovery, --name, GENIUS_RESULT. Triggers: genius image, crun image, batch image. Prefer dreamina-cli for Seedream/Seedance 即梦."
---

# Genius Image

## Overview

Generate AI images via Crun.ai (https://crun.ai) using async webhook pattern. The script lives in this skill folder, but every normal run must use the current session workspace as `workdir` so outputs land in that workspace's `genius_output/`. Single command can run one image or batch-concurrent multiple images across different models. All complexity (cloudflared tunnel, webhook server, retry logic, log rotation) is hidden from the user.

## Start Here

**先选模型（双默认）：**
- **快速出图 / 草稿 / 省时间** → `nano-banana-2-lite`（CLI 未指定时的默认）
- **画面内容复杂、构图/设计要求高** → `gpt-image-2`
- 用户点名其他模型再换；不要默认上 premium

Classify the request:

- **Single image**: pick lite or gpt-image-2 by the rule above → run directly
- **Dual default compare**: "对比两个默认模型" → batch with lite + gpt-image-2
- **Multi-model compare**: "compare all models" → batch all 4
- **Batch generation**: "generate 5 prompts" → auto-generate batch.json
- **Preflight**: first generation request in a session → run `--preflight --no-gen` once
- **Check balance**: "how many credits left" → run with `--balance`
- **Recover / re-download**: have `task_id` but missing local file → run `--fetch-task <task_id>`
- **Agent / unstable tunnel**: prefer `--poll-only` (no cloudflared)
- **Self-test**: "test the skill" → run `<skill_dir>/scripts/test.py`

**When NOT this skill:** Seedream / Seedance / 即梦 native → use `dreamina-cli`, not genius-image.

Inspect the smallest useful evidence:
- User's prompt(s) and whether they need **speed** or **design quality**
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
2. **Delivery mode**: default is webhook + cloudflared；Agent 环境或隧道不稳时用 **`--poll-only`**（只轮询 TaskInfo，不启 tunnel）。不要默认强依赖 tunnel。
3. **Always clean up tunnel + webhook server** when used: `finally` block
4. **JSONL log rotation**: 10MB → archive, 7 days → delete
5. **501 auto-retry**: retry only when completed task payload has `result.code == 501`, up to 3 times, 5s delay
6. **User does not see batch.json**: AI generates and cleans up the file
7. **Do not run self-test before ordinary generation**: run `scripts/test.py` only when the user asks, after editing this skill, or while debugging setup failures
8. **Use absolute script paths**: the script is in the skill folder; the output location is controlled by `--out` or `workdir`, not by where the script file lives
9. **Run preflight once per session before the first generation**: `--preflight --no-gen` checks API key, workspace writability, and cloudflared tunnel without creating a task or consuming generation credits
10. **cloudflared must be available before generating**: check `bin/cloudflared.exe` (relative to `<skill_dir>`) or `cloudflared` on PATH. If neither exists, report the missing binary and exit — do not attempt generation without it. Download from https://github.com/cloudflare/cloudflared/releases/latest and place at `<skill_dir>/bin/cloudflared.exe`.
11. **Webhook 端口默认 8765，可用 `--port`；占用时自动顺延**。仍冲突则改用 `--poll-only`。
12. **回调/轮询超时最长 300 秒（5分钟）**：hybrid 每 15s 心跳、30s 轮询；`--poll-only` 每 5s 轮询。超时后保留 `task_id`，用 `--fetch-task` 补下。
13. **Agent 必须用 `python -u`**，推荐默认加 **`--poll-only`**。已提交后不要 abort；中断则 `--fetch-task`。
14. **提交即落盘** + 结束打印 **`GENIUS_RESULT ...`** 一行（`status`/`path`/`task_id`/`media_url`），Agent 优先解析该行。
15. **文件名**：优先 `--name "短名"`；否则 `model_安全截断prompt`。batch 任务对象可写 `"name": "..."`。

## Path Resolution

**`<skill_dir>`** = the directory containing this SKILL.md file. The agent must resolve it at runtime before running any command. Examples:
- ZCode / Kiro / OpenCode: use the skill's install path (e.g. `~/.zcode/skills/genius-image/`)
- Hermes / Reasonix: the path where this SKILL.md was loaded from
- When unsure: run `find ~/.config ~/.zcode ~/.hermes ~/.reasonix -name "genius-image" -type d 2>/dev/null | head -1`

Use `<skill_dir>` in all script paths below. Never hardcode a user-specific absolute path.

## Workflow

> 下方命令均使用 `<skill_dir>` 指向脚本，用 `<workspace>` 指向用户工作区。**推荐始终传 `--out "<workspace>/genius_output"` 明确指定输出路径，避免 cwd 问题。** `<skill_dir>` 见上方 Path Resolution 说明。

### Single image — 快速（默认 lite）
```bash
# 草稿 / 快出图：nano-banana-2-lite（可不写 --model，CLI 默认即是它）
python -u "<skill_dir>/scripts/genius.py" "一只可爱的小猫" --model nano-banana-2-lite --aspect 16:9 --poll-only --name "cute-cat" --out "<workspace>/genius_output"
```

### Single image — 复杂画面 / 设计感（gpt-image-2）
```bash
# 内容复杂、构图与设计要求高：gpt-image-2
python -u "<skill_dir>/scripts/genius.py" "赛博朋克夜市，多层景深，霓虹招牌与雨后反光，电影级构图" --model gpt-image-2 --aspect 16:9 --resolution 1K --poll-only --name "cyberpunk-market" --out "<workspace>/genius_output"

# 需要 webhook 回调时（默认 hybrid）：
python -u "<skill_dir>/scripts/genius.py" "品牌主视觉海报，极简留白与强层级" --model gpt-image-2 --aspect 3:4 --resolution 2K --out "<workspace>/genius_output"
```

### 参考图 / 图生图（--ref）
`--ref` 接受一张或多张参考图，用于保持人物 / 风格一致性（如角色转面、同一个人多角度）。每一项可以是：
- **http(s) URL** —— 原样传给 API
- **本地文件路径** —— 脚本自动读取并编码成 `data:image/...;base64,...`（API 只收 URL 或 base64，本地路径会被自动转换，无需手动处理）

```bash
# 快速参考图迭代 → lite
python -u "<skill_dir>/scripts/genius.py" "同一角色侧身站立" --model nano-banana-2-lite --aspect 1:1 --ref "genius_output\character.png" --poll-only --out "<workspace>/genius_output"
# 复杂转面 / 高设计感图生图 → gpt-image-2
python -u "<skill_dir>/scripts/genius.py" "同一个人的 3x3 九宫格多角度转面图" --model gpt-image-2 --aspect 16:9 --resolution 1K --ref "genius_output\some_photo.png" --poll-only --out "<workspace>/genius_output"
# 远程 URL，或多张混用
python -u "<skill_dir>/scripts/genius.py" "..." --model nano-banana-2-lite --ref "https://example.com/a.png" "genius_output\b.png" --poll-only --out "<workspace>/genius_output"
```
> 注意：base64 会让请求体增大约 33%，传超大图或多张参考图时 body 可能偏大。需要稳定时优先用 http(s) URL。本地文件找不到会直接报错，不会把无效路径丢给服务端。batch.json 里对应字段是 `ref`（数组）或兼容写法 `img_urls`。

### Preflight (once per session)
```bash
# Agent 推荐 poll-only preflight（不测 tunnel）
python -u "<skill_dir>/scripts/genius.py" --preflight --no-gen --poll-only --out "<workspace>/genius_output"
# 完整 tunnel 检查：
python -u "<skill_dir>/scripts/genius.py" --preflight --no-gen --out "<workspace>/genius_output"
```

### Recover by task_id（agent 中断 / 超时后补下）
```bash
python -u "<skill_dir>/scripts/genius.py" --fetch-task "<task_id>" --out "<workspace>/genius_output"
```
不需要 tunnel/webhook。仅当云端任务 `status=success` 时可下载。

### Batch (auto-generate config)
AI creates `batch_<timestamp>.json` in the **`genius_output/Tmp/` subdirectory** (clearly separated from artifacts), runs, then deletes the file:
```bash
# AI writes: <workspace>/genius_output/Tmp/batch_<timestamp>.json
# AI runs:
python -u "<skill_dir>/scripts/genius.py" --batch <workspace>/genius_output/Tmp/batch_<timestamp>.json --concurrent 3 --poll-only --out "<workspace>/genius_output"
# AI deletes the batch file immediately after
```
**Always** put batch.json in `genius_output/Tmp/` — never in the working directory root, and never alongside the generated images.

#### batch.json 格式

顶层是一个**任务数组**（不是带 `concurrent`/`tasks` 包装的对象）。并发数由命令行 `--concurrent` 控制，不写在文件里。每个任务对象至少要有 `prompt`，其余字段（`model`/`aspect`/`resolution` 等）可选，缺省走默认值：

```json
[
  { "prompt": "一只可爱的小猫", "model": "nano-banana-2-lite", "aspect": "16:9", "name": "cat-lite" },
  { "prompt": "赛博朋克城市夜景，多层景深与电影级构图", "model": "gpt-image-2", "aspect": "16:9", "resolution": "1K", "name": "cyber-gpt" }
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
python -u "<skill_dir>/scripts/genius.py" --balance
```

### Self-test
```bash
python -u "<skill_dir>/scripts/test.py"
```

## Models

| Key | Role | Crun ID | Resolutions | Special params |
|---|---|---|---|---|
| `nano-banana-2-lite` | **默认·快** | `google/nano-banana-2-lite` | — | 极速草稿，约4秒，max 10 张参考图，无 resolution |
| `gpt-image-2` | **默认·设计** | `openai/gpt-image-2` | 1K/2K/4K | 复杂画面、高设计感首选 |
| `gpt-image-2-premium` | 备选 | `openai/gpt-image-2-premium` | 1K/2K/4K | `--quality` low/medium/high（default medium） |
| `nano-banana-2` | 备选 | `google/nano-banana-2` | 1K/2K/4K | `--google-search` / `--output-format` |

**选型指引（必须遵守）：**
- **快速出图 / 草稿 / 迭代** → `nano-banana-2-lite`（CLI / batch 未写 model 时的默认）
- **画面内容复杂、构图与设计要好** → `gpt-image-2`
- 用户明确要求更高档位写实可控 → `gpt-image-2-premium`
- 需要谷歌搜索增强 / 超长 prompt → `nano-banana-2`

## Resource Map

- `scripts/genius.py`: main script (single + batch + balance + `--fetch-task`)
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
- **Parse `GENIUS_RESULT` line first** (status / path / task_id / media_url)
- **Models used** and their order
- **Total duration** per model
- **File paths** in `genius_output/`
- **Task IDs and media URLs** from log `genius_output/Logs/genius_log.jsonl`
- **Credits consumed** (from log `genius_output/Logs/genius_log.jsonl`)
- **Cleanup status** (tunnel closed if used, batch.json deleted)

## Final Response

Report: what was generated, where files live, credits spent, and any failures with retry status.
