---
name: genius-cpa-image
description: "Generate images via CPA-US OpenAI images (gpt-image-2). Supports aspect/size, --ref edits, --quality/--output-format, batch, preflight, GENIUS_RESULT. Triggers: genius cpa image, CPA image, gpt-image-2, Genius_Cpa_image, Codex image. Do not use for Gemini generateContent, Crun nano, or Seedream/即梦."
---

# Genius CPA Image

## Overview

CPA-US 生图。只走 **gpt-image-2**：

| Model | Provider | Endpoint |
|---|---|---|
| `gpt-image-2` (only) | `cpa-us` | `POST {CPA_US_BASE}/v1/images/generations`（`--ref` → `/v1/images/edits`） |

- US base 默认：`https://cpa.artistic-genius.vip`
- 密钥：环境变量 **或** skill 本地 `.env`
- 输出目录：工作区 `genius_output/`（**始终传 `--out`**）
- 尺寸矩阵 / API body / 错误与 async → `references/usage.md`

## Start Here

- 密钥 → 复制 `.env.example` 为 `.env`，填 `CPA_US_API_KEY`
- `scripts/cpa_image.py "prompt" --aspect 16:9 --quality medium`
- 图生图 → `--ref`；批量 → `--batch`；异步 → `--async` / `--status` / `--wait`
- 首次 → `--preflight --no-gen`
- 本渠道 **只有 1K**。`--resolution 2K/4K` 会 coerce 到同比例 1K 并打印 `[note]`

## Non-Negotiables

1. 密钥只来自环境变量或 skill 本地 `.env`，**禁止硬编码**；真实 `.env` 永不提交远端。
2. 始终 `--out "<workspace>/genius_output"`。
3. Agent 用 `python3 -u`。
4. 只使用 `gpt-image-2`。不要走 Gemini / `generateContent` / JP CPA。
5. **仅 1K 像素档**。支持 `--quality` / `--output-format` / 固定 `--size` 预设。不支持 `--google-search`。`quality` 不抬像素。
6. 解析 `GENIUS_RESULT` 行；始终报告 `actual_size`。
7. batch.json 放 `genius_output/Tmp/`，跑完删除。
8. 遇到 `HTTP 429` / `model_cooldown` / `auth_unavailable` **立刻失败**，禁止重试空转。

## Workflow

### Preflight
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" --preflight --no-gen --out "<workspace>/genius_output"
```

### gpt-image-2 (US · CPA 1K only)
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "minimal red square app icon" \
  --aspect 1:1 --quality low --name "gpt-icon" \
  --out "<workspace>/genius_output"

python3 -u "<skill_dir>/scripts/cpa_image.py" "wide seascape" \
  --aspect 16:9 --resolution 1K --quality medium --name "sea" \
  --out "<workspace>/genius_output"

python3 -u "<skill_dir>/scripts/cpa_image.py" "portrait" \
  --size 1024x1536 --quality low \
  --out "<workspace>/genius_output"
```

### Image-to-image / batch / async
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "same subject, side view" \
  --aspect 1:1 --quality low \
  --ref "<workspace>/genius_output/gpt-icon_1.png" \
  --name "gpt-side" --out "<workspace>/genius_output"

python3 -u "<skill_dir>/scripts/cpa_image.py" "neon alley" \
  --aspect 1:1 --quality low --name "neon" --async \
  --out "<workspace>/genius_output"
python3 -u "<skill_dir>/scripts/cpa_image.py" --status <job_id> --out "<workspace>/genius_output"
```

## Models / Params

| Model | Provider | aspect | resolution / size | extra |
|---|---|---|---|---|
| `gpt-image-2` | cpa-us | 1:1 3:2 2:3 4:3 3:4 5:4 4:5 16:9 9:16 21:9 9:21 2:1 1:2 auto | **仅 1K**（2K/4K→1K + note） | `--size` 预设 / `--quality` / `--output-format` / `--ref` |

常用 1K：`1:1=1024x1024`，`16:9=1672x941`，`9:16=941x1672`，`3:2=1536x1024`。全表见 `references/usage.md`。

## Env / Secrets

优先级：**进程环境变量 > skill 本地 `.env`**。

| Var | Required | Default |
|---|---|---|
| `CPA_US_API_KEY` | yes | — |
| `CPA_GPT_API_KEY` | optional alias | — |
| `CPA_US_BASE` | no | `https://cpa.artistic-genius.vip` |

Log/job rotation 可选 env 见 `.env.example`。

## Resource Map

- `scripts/cpa_image.py`
- `scripts/test.py`
- `.env.example`
- `references/usage.md`
- `evals/evals.json`
- `agents/openai.yaml`

## Final Response

Report path, model, provider, aspect/resolution/size, actual_size, quality, duration, task_id, failures. If the user asked for 2K/4K, state that CPA-US coerced to 1K.
