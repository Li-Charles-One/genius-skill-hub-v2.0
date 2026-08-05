---
name: genius-cpa-image
description: "Generate images via multi-provider CPA: JP Gemini generateContent (gemini-3.1-flash-image) and US OpenAI images (gpt-image-2). Supports aspect/resolution, --ref, --quality/--output-format (gpt-image), --google-search (Gemini), batch, preflight, GENIUS_RESULT. Triggers: genius cpa image, CPA image, gpt-image-2, gemini-3.1-flash-image, Genius_Cpa_image, generateContent image, Codex image. Not for Crun nano or Seedream/即梦."
---

# Genius CPA Image

## Overview

Multi-provider CPA 生图 skill。按 **model** 自动选供应商与接口：

| Model | Provider | Endpoint |
|---|---|---|
| `gemini-3.1-flash-image` (default) | `cpa-jp` | `POST {CPA_JP_BASE}/v1beta/models/{model}:generateContent` |
| `gpt-image-2` | `cpa-us` | `POST {CPA_US_BASE}/v1/images/generations`（`--ref` → `/v1/images/edits`） |

- JP base 默认：`https://cpa-jp.charles-ai.space`
- US base 默认：`https://cpa.charles-ai.space`
- 密钥：环境变量 **或** skill 本地 `.env`
- 输出目录：工作区 `genius_output/`（**始终传 `--out`**）
- 详细尺寸矩阵 / API body / 错误与 async → `references/usage.md`

## Start Here

- 密钥 → 复制 `.env.example` 为 `.env`，填 `CPA_JP_API_KEY` 和/或 `CPA_US_API_KEY`
- Gemini → `scripts/cpa_image.py "prompt" --aspect 16:9 --resolution 1K`
- **gpt-image-2** → `scripts/cpa_image.py "prompt" --model gpt-image-2 --aspect 16:9 --quality medium`
- 真 2K/4K → **只用 Gemini** `--resolution 2K|4K`（gpt-image 渠道只有 1K）
- 图生图 → `--ref`；批量 → `--batch`；异步 → `--async` / `--status` / `--wait`
- 首次 → `--preflight --no-gen`（可加 `--model gpt-image-2`）

## Non-Negotiables

1. 密钥只来自环境变量或 skill 本地 `.env`，**禁止硬编码**；真实 `.env` 永不提交远端。
2. 始终 `--out "<workspace>/genius_output"`。
3. Agent 用 `python3 -u`。
4. 模型决定供应商：不要把 Gemini 参数硬套到 gpt-image，反之亦然。
5. Gemini：**不支持** `quality` / `output_format`；用 `--aspect` + `--resolution`（0.5K–4K 真实生效）。
6. gpt-image-2（CPA-US）：**仅 1K 像素档**。支持 `--quality` / `--output-format` / 固定 `--size` 预设；**不支持** `--google-search`。`--resolution 2K/4K` 与 legacy 大尺寸会 **coerce 到同比例 1K** 并打印 `[note]`；`quality` 不抬像素。完整矩阵见 `references/usage.md`。
7. 解析 `GENIUS_RESULT` 行；始终报告 `actual_size`。
8. batch.json 放 `genius_output/Tmp/`，跑完删除。
9. 遇到 `HTTP 429` / `model_cooldown` / `auth_unavailable` **立刻失败**，禁止重试空转。

## Workflow

### Preflight
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" --preflight --no-gen --out "<workspace>/genius_output"
python3 -u "<skill_dir>/scripts/cpa_image.py" --model gpt-image-2 \
  --preflight --no-gen --out "<workspace>/genius_output"
```

### Gemini (JP)
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "窗边橘猫，柔和自然光" \
  --aspect 1:1 --resolution 1K --name "cpa-cat" \
  --out "<workspace>/genius_output"

# 真 4K 用 Gemini
python3 -u "<skill_dir>/scripts/cpa_image.py" "wide seascape" \
  --aspect 16:9 --resolution 4K --name "sea-4k" \
  --out "<workspace>/genius_output"
```

### gpt-image-2 (US · CPA 1K only)
```bash
# 默认按 aspect → 1K 预设（16:9 → 1672x941）
python3 -u "<skill_dir>/scripts/cpa_image.py" "minimal red square app icon" \
  --model gpt-image-2 --aspect 1:1 --quality low --name "gpt-icon" \
  --out "<workspace>/genius_output"

python3 -u "<skill_dir>/scripts/cpa_image.py" "wide seascape" \
  --model gpt-image-2 --aspect 16:9 --resolution 1K --quality medium --name "sea" \
  --out "<workspace>/genius_output"

# 直接指定 CPA 1K 预设（见 usage.md 全表）
python3 -u "<skill_dir>/scripts/cpa_image.py" "portrait" \
  --model gpt-image-2 --size 1024x1536 --quality low \
  --out "<workspace>/genius_output"
```

### Image-to-image / grounding / batch / async
```bash
# Gemini ref
python3 -u "<skill_dir>/scripts/cpa_image.py" "同一只猫侧身站立" \
  --aspect 1:1 --resolution 1K \
  --ref "<workspace>/genius_output/cpa-cat_1.jpg" \
  --name "cpa-cat-side" --out "<workspace>/genius_output"

# gpt-image edits
python3 -u "<skill_dir>/scripts/cpa_image.py" "same subject, side view" \
  --model gpt-image-2 --aspect 1:1 --quality low \
  --ref "<workspace>/genius_output/gpt-icon_1.png" \
  --name "gpt-side" --out "<workspace>/genius_output"

# Gemini google search
python3 -u "<skill_dir>/scripts/cpa_image.py" "Generate an infographic of today's weather in Tokyo" \
  --aspect 16:9 --resolution 1K --google-search \
  --out "<workspace>/genius_output"

# async
python3 -u "<skill_dir>/scripts/cpa_image.py" "neon alley" \
  --model gpt-image-2 --aspect 1:1 --quality low --name "neon" --async \
  --out "<workspace>/genius_output"
python3 -u "<skill_dir>/scripts/cpa_image.py" --status <job_id> --out "<workspace>/genius_output"
```

Batch JSON 可混用 model（详见 `references/usage.md`）。

## Models / Params

| Model | Provider | aspect | resolution / size | extra |
|---|---|---|---|---|
| `gemini-3.1-flash-image` | cpa-jp | 1:1 … 21:9, 1:4… | **0.5K 1K 2K 4K 真实** | `--ref` `--google-search` |
| `gpt-image-2` | cpa-us | 1:1 3:2 2:3 4:3 3:4 5:4 4:5 16:9 9:16 21:9 9:21 2:1 1:2 auto | **仅 1K**（2K/4K→1K + note） | `--size` 预设 / `--quality` / `--output-format` / `--ref` |

gpt-image 常用 1K：`1:1=1024x1024`，`16:9=1672x941`，`9:16=941x1672`，`3:2=1536x1024`。全表与 legacy coerce 见 `references/usage.md`。

## Env / Secrets

优先级：**进程环境变量 > skill 本地 `.env`**。

| Var | Provider | Required | Default |
|---|---|---|---|
| `CPA_JP_API_KEY` | cpa-jp | for Gemini | — |
| `CPA_API_KEY` | cpa-jp alias | optional | — |
| `CPA_JP_BASE` | cpa-jp | no | `https://cpa-jp.charles-ai.space` |
| `CPA_US_API_KEY` | cpa-us | for gpt-image-2 | — |
| `CPA_GPT_API_KEY` | cpa-us alias | optional | — |
| `CPA_US_BASE` | cpa-us | no | `https://cpa.charles-ai.space` |

Log/job rotation 可选 env 见 `.env.example`。

## Resource Map

- `scripts/cpa_image.py`
- `scripts/test.py`
- `.env.example`
- `references/usage.md` — 尺寸矩阵、API body、async、错误策略
- `evals/evals.json`
- `agents/openai.yaml`

## Final Response

Report path, model, provider, aspect/resolution/size, actual_size, quality, duration, task_id, failures. If gpt-image requested 2K/4K, state that CPA-US coerced to 1K.
