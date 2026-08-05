---
name: genius-cpa-image
description: "Generate images via JP CPA using official Gemini generateContent for gemini-3.1-flash-image. Supports imageConfig aspectRatio + imageSize (0.5K/1K/2K/4K), --ref image-to-image, --google-search, batch, preflight, GENIUS_RESULT. Endpoint: /v1beta/models/{model}:generateContent. Triggers: genius cpa image, CPA image, gemini-3.1-flash-image, Genius_Cpa_image, generateContent image. Not for Crun nano/gpt-image or Seedream/即梦."
---

# Genius CPA Image

## Overview

JP CPA 专用生图 skill，走 **官方 Gemini 原生接口**（不是 OpenAI chat 凑合）：

```text
POST {CPA_JP_BASE}/v1beta/models/gemini-3.1-flash-image:generateContent
```

- Base 默认：`https://cpa-jp.charles-ai.space`
- Auth：`CPA_JP_API_KEY`（兼容 `CPA_API_KEY`）
- 密钥来源：进程环境变量 **或** skill 本地 `.env`（见下）
- 控制：`generationConfig.imageConfig.aspectRatio` + `imageSize`
- 输出目录：工作区 `genius_output/`（**始终传 `--out`**）

## Start Here

- 密钥 → 复制 `.env.example` 为 `.env` 填入 `CPA_JP_API_KEY`（或 `export`）
- 单张 → `scripts/cpa_image.py "prompt" --aspect 16:9 --resolution 1K`
- 高清 → `--resolution 2K` 或 `4K`
- 图生图 → `--ref`
- 搜索 grounding → `--google-search`
- 批量 → `--batch`
- 本地异步 → `--async`（秒回 `job_id`）/ `--status` / `--wait` / `--list-jobs`
- 首次会话 → `--preflight --no-gen`

## Non-Negotiables

1. 密钥只来自环境变量或 skill 本地 `.env`，**禁止硬编码**；真实 `.env` 永不提交远端。
2. 始终 `--out "<workspace>/genius_output"`。
3. Agent 用 `python3 -u`。
4. 用官方字段：`--aspect` → `aspectRatio`，`--resolution` → `imageSize`。
5. **不支持** `quality` / `output_format`（不是 Gemini imageConfig）。
6. 解析 `GENIUS_RESULT` 行。
7. batch.json 放 `genius_output/Tmp/`，跑完删除。
8. 遇到 `HTTP 429` / `model_cooldown` **立刻失败**，打印 `reset_time` / `reset_seconds`，**禁止重试空转**。

## Workflow

### Preflight
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" --preflight --no-gen --out "<workspace>/genius_output"
```

### Single
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "窗边橘猫，柔和自然光" \
  --aspect 1:1 --resolution 1K --name "cpa-cat" \
  --out "<workspace>/genius_output"
```

### 2K / 16:9
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "赛博朋克夜市" \
  --aspect 16:9 --resolution 2K --name "cyber" \
  --out "<workspace>/genius_output"
```

### Image-to-image
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "同一只猫侧身站立" \
  --aspect 1:1 --resolution 1K \
  --ref "<workspace>/genius_output/cpa-cat_1.jpg" \
  --name "cpa-cat-side" --out "<workspace>/genius_output"
```

### Google Search grounding
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "Generate an infographic of today's weather in Tokyo" \
  --aspect 16:9 --resolution 1K --google-search \
  --out "<workspace>/genius_output"
```

### Batch
```json
[
  {"prompt": "红苹果", "aspect": "1:1", "resolution": "1K", "name": "apple"},
  {"prompt": "海边日落", "aspect": "16:9", "resolution": "2K", "name": "sunset"}
]
```

### Local async (client-side)
不是 CPA 服务端 job API；是本地后台 worker。状态在 `genius_output/Jobs/`。

```bash
# 提交后立刻返回 job_id
python3 -u "<skill_dir>/scripts/cpa_image.py" "赛博朋克夜市" \
  --aspect 16:9 --resolution 1K --name "cyber" --async \
  --out "<workspace>/genius_output"

# 查询 / 等待 / 列表
python3 -u "<skill_dir>/scripts/cpa_image.py" --status <job_id> --out "<workspace>/genius_output"
python3 -u "<skill_dir>/scripts/cpa_image.py" --wait <job_id> --timeout 600 --out "<workspace>/genius_output"
python3 -u "<skill_dir>/scripts/cpa_image.py" --list-jobs --out "<workspace>/genius_output"

# batch 也可异步
python3 -u "<skill_dir>/scripts/cpa_image.py" --batch "<workspace>/genius_output/Tmp/batch.json" \
  --async --concurrent 3 --out "<workspace>/genius_output"
```

- 状态文件：`genius_output/Jobs/<job_id>.json`
- worker 日志：`genius_output/Jobs/<job_id>.log`
- 成图仍写 `genius_output/`
- 状态：`queued` → `running` → `success` / `failed` / `partial`

## Models / Params

| Key | Endpoint model id |
|---|---|
| `gemini-3.1-flash-image` | `gemini-3.1-flash-image` |

| CLI | Official field | Values |
|---|---|---|
| `--aspect` | `imageConfig.aspectRatio` | `1:1` `2:3` `3:2` `3:4` `4:3` `4:5` `5:4` `9:16` `16:9` `21:9` `1:4` `4:1` `1:8` `8:1` |
| `--resolution` | `imageConfig.imageSize` | `0.5K` `1K`(default) `2K` `4K` |
| `--ref` | multimodal `inlineData` | max 14 |
| `--google-search` | `tools: [{google_search:{}}]` | bool |

## Env / Secrets

优先级：**进程环境变量 > skill 本地 `.env`**。

| Var | Required | Default |
|---|---|---|
| `CPA_JP_API_KEY` | yes* | — |
| `CPA_API_KEY` | alias | — |
| `CPA_JP_BASE` | no | `https://cpa-jp.charles-ai.space` |

本地文件搜索顺序（取第一个存在且非空的）：

1. `<skill_dir>/.env`
2. `<skill_dir>/scripts/.env`
3. `<skill_dir>/Genius_cpa_image.env`

```bash
cp .env.example .env
# 编辑 .env 填入 CPA_JP_API_KEY=...
```

- 仓库根 `.gitignore` 已有 `*.env`，真实密钥文件不会进 git。
- 只提交 `.env.example`（无密钥）。

## Resource Map

- `scripts/cpa_image.py`
- `scripts/test.py`
- `.env.example`
- `references/usage.md`
- `evals/evals.json`
- `agents/openai.yaml`

## Final Response

Report path, aspect, resolution, duration, task_id, failures.
