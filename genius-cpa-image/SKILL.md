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

## Start Here

- 密钥 → 复制 `.env.example` 为 `.env`，填 `CPA_JP_API_KEY` 和/或 `CPA_US_API_KEY`
- Gemini → `scripts/cpa_image.py "prompt" --aspect 16:9 --resolution 1K`
- **gpt-image-2** → `scripts/cpa_image.py "prompt" --model gpt-image-2 --aspect 1:1 --quality low`
- 图生图 → `--ref`（Gemini=inlineData；gpt-image=edits）
- 批量 → `--batch`（可混用 model）
- 本地异步 → `--async` / `--status` / `--wait` / `--list-jobs`
- 首次 → `--preflight --no-gen`（可加 `--model gpt-image-2`）

## Non-Negotiables

1. 密钥只来自环境变量或 skill 本地 `.env`，**禁止硬编码**；真实 `.env` 永不提交远端。
2. 始终 `--out "<workspace>/genius_output"`。
3. Agent 用 `python3 -u`。
4. 模型决定供应商：不要把 Gemini 参数硬套到 gpt-image，反之亦然。
5. Gemini：**不支持** `quality` / `output_format`；用 `--aspect` + `--resolution`。
6. gpt-image-2（CPA-US）：支持 `--quality` / `--output-format` / `--size`；**不支持** `--google-search`。aspect 含 `1:1` `3:2` `2:3` `4:3` `3:4` `5:4` `4:5` `16:9` `9:16` `21:9` `9:21` `2:1` `1:2` `auto`。**仅 1K 像素档**；`2K`/`4K` 会 coerce 到同比例 1K。`--size` 仅限 CPA 1K 预设（或 legacy 尺寸自动映射）。始终报告 `actual_size`。
7. 解析 `GENIUS_RESULT` 行。
8. batch.json 放 `genius_output/Tmp/`，跑完删除。
9. 遇到 `HTTP 429` / `model_cooldown` / `auth_unavailable` **立刻失败**，禁止重试空转。

## Workflow

### Preflight
```bash
# default gemini / JP
python3 -u "<skill_dir>/scripts/cpa_image.py" --preflight --no-gen --out "<workspace>/genius_output"

# gpt-image-2 / US
python3 -u "<skill_dir>/scripts/cpa_image.py" --model gpt-image-2 \
  --preflight --no-gen --out "<workspace>/genius_output"
```

### Gemini (JP)
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "窗边橘猫，柔和自然光" \
  --aspect 1:1 --resolution 1K --name "cpa-cat" \
  --out "<workspace>/genius_output"
```

### gpt-image-2 (US · CPA 1K only)
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "minimal red square app icon" \
  --model gpt-image-2 --aspect 1:1 --quality low --name "gpt-icon" \
  --out "<workspace>/genius_output"

# 16:9 1K → 1672x941；quality 只影响画质/耗时，不抬像素
python3 -u "<skill_dir>/scripts/cpa_image.py" "wide seascape" \
  --model gpt-image-2 --aspect 16:9 --resolution 1K --quality medium --name "sea" \
  --out "<workspace>/genius_output"

# 9:16 竖图；--resolution 4K 会被 coerce 成 1K (941x1672)
python3 -u "<skill_dir>/scripts/cpa_image.py" "phone wallpaper" \
  --model gpt-image-2 --aspect 9:16 --quality high --name "wall" \
  --out "<workspace>/genius_output"

# 直接指定 CPA 1K 预设
python3 -u "<skill_dir>/scripts/cpa_image.py" "portrait" \
  --model gpt-image-2 --size 1024x1536 --quality low \
  --out "<workspace>/genius_output"

# legacy 4K size 会自动映射到同比例 1K（1672x941），不会出真 4K
python3 -u "<skill_dir>/scripts/cpa_image.py" "landscape" \
  --model gpt-image-2 --size 3840x2160 --quality medium \
  --out "<workspace>/genius_output"
```

### Image-to-image
```bash
# Gemini
python3 -u "<skill_dir>/scripts/cpa_image.py" "同一只猫侧身站立" \
  --aspect 1:1 --resolution 1K \
  --ref "<workspace>/genius_output/cpa-cat_1.jpg" \
  --name "cpa-cat-side" --out "<workspace>/genius_output"

# gpt-image-2 edits
python3 -u "<skill_dir>/scripts/cpa_image.py" "same subject, side view" \
  --model gpt-image-2 --aspect 1:1 --quality low \
  --ref "<workspace>/genius_output/gpt-icon_1.png" \
  --name "gpt-side" --out "<workspace>/genius_output"
```

### Google Search grounding (Gemini only)
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "Generate an infographic of today's weather in Tokyo" \
  --aspect 16:9 --resolution 1K --google-search \
  --out "<workspace>/genius_output"
```

### Batch (mixed providers ok)
```json
[
  {"prompt": "红苹果", "aspect": "1:1", "resolution": "1K", "name": "apple"},
  {"prompt": "minimal blue icon", "model": "gpt-image-2", "aspect": "1:1", "quality": "low", "name": "icon"}
]
```

### Local async (client-side)
```bash
python3 -u "<skill_dir>/scripts/cpa_image.py" "neon alley" \
  --model gpt-image-2 --aspect 1:1 --quality low --name "neon" --async \
  --out "<workspace>/genius_output"

python3 -u "<skill_dir>/scripts/cpa_image.py" --status <job_id> --out "<workspace>/genius_output"
python3 -u "<skill_dir>/scripts/cpa_image.py" --wait <job_id> --timeout 600 --out "<workspace>/genius_output"
python3 -u "<skill_dir>/scripts/cpa_image.py" --list-jobs --out "<workspace>/genius_output"
```

## Models / Params

| Model | Provider | API | aspect | resolution / size | extra |
|---|---|---|---|---|---|
| `gemini-3.1-flash-image` | cpa-jp | generateContent | 1:1 2:3 3:2 3:4 4:3 4:5 5:4 9:16 16:9 21:9 1:4 4:1 1:8 8:1 | 0.5K 1K 2K 4K | `--ref` `--google-search` |
| `gpt-image-2` | cpa-us | images | 1:1 3:2 2:3 4:3 3:4 5:4 4:5 16:9 9:16 21:9 9:21 2:1 1:2 auto | **仅 1K**（2K/4K coerce→1K）+ 固定 `--size` 预设 | `--size` `--quality` `--output-format` `--ref`(edits)；回读 `actual_size` |

gpt-image-2（CPA-US 实测，2026-08-05）：

- **只有 1K 像素档**；`quality` 改变画质/耗时，**不抬分辨率**
- `--resolution 2K/4K` 与 legacy `--size 3840x2160` 等会 **coerce 到同比例 1K 预设**
- 真 2K/4K 请用 **Gemini**（`gemini-3.1-flash-image --resolution 2K|4K`）

CPA-US 1K size 矩阵（UI + live `actual_size`）：

| aspect | size |
|---|---|
| 1:1 | 1024x1024 |
| 16:9 | 1672x941 |
| 9:16 | 941x1672 |
| 4:3 | 1443x1090 |
| 3:4 | 1090x1443 |
| 3:2 | 1536x1024 |
| 2:3 | 1024x1536 |
| 5:4 | 1408x1120 |
| 4:5 | 1120x1408 |
| 21:9 | 1920x832 |
| 9:21 | 832x1920 |
| 2:1 | 1792x896 |
| 1:2 | 896x1792 |
| auto | auto |

> `GENIUS_RESULT` 含 `size=`（请求/映射后）与 `actual_size=`（文件真实宽高）。

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

### Log / job rotation (optional)

| Var | Default | Meaning |
|---|---|---|
| `CPA_IMAGE_LOG_MAX_MB` | 10 | main `cpa_image_log.jsonl` rotate threshold (MB) |
| `CPA_IMAGE_LOG_KEEP_DAYS` | 7 | delete rotated `cpa_image_log_*.jsonl` older than N days |
| `CPA_IMAGE_LOG_MAX_ARCHIVES` | 20 | keep at most N main-log archives |
| `CPA_IMAGE_JOB_LOG_MAX_MB` | 5 | rotate each `Jobs/<id>.log` when larger |
| `CPA_IMAGE_JOB_KEEP_DAYS` | 7 | delete job json/log older than N days |
| `CPA_IMAGE_JOB_MAX_FILES` | 100 | keep newest N job status json (paired logs pruned) |

Also accepts `CPA_IMAGE_LOG_MAX_BYTES` / `CPA_IMAGE_JOB_LOG_MAX_BYTES` if you prefer bytes over MB.

本地文件搜索顺序：

1. `<skill_dir>/.env`
2. `<skill_dir>/scripts/.env`
3. `<skill_dir>/Genius_cpa_image.env`

## Resource Map

- `scripts/cpa_image.py`
- `scripts/test.py`
- `.env.example`
- `references/usage.md`
- `evals/evals.json`
- `agents/openai.yaml`

## Log layout

| Path | Rotation |
|---|---|
| `genius_output/Logs/cpa_image_log.jsonl` | size → `cpa_image_log_YYYYMMDD_HHMMSS.jsonl`; age + archive-count prune |
| `genius_output/Jobs/<job_id>.json` | age + max-files prune |
| `genius_output/Jobs/<job_id>.log` | size rotate; age + count prune with jobs |

Cleanup runs at task start / async worker start (`clean_old_logs`).

## Final Response

Report path, model, provider, aspect/resolution/size, actual_size, quality, duration, task_id, failures.
