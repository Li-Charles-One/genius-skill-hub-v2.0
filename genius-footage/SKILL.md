---
name: genius-footage
description: "Genius 素材说明书：给一条视频（素材或成片）生成剪辑用的 .footage.md：逐帧精确的镜头表、带说话人和可下刀点的台词表、人物、内容分段、金句、重拍与废片、可能听错的词；口播（一镜到底、单人对镜头讲）可加口播模式，另出停顿、语气词、句内重复起头和按字精确到帧的精剪建议；拉片模式给一条或几条参考片（本地文件或链接）出拉片报告：结构与叙事、节奏数据与剪辑手法、视听语言、包装和可借鉴手法，几条一起拉时另出一份汇总对比；多条素材并行，素材可以是本地文件或视频链接；也可只出逐帧精确的镜头表，或只出花字表（成片里每个花字、人名条的原文、入点出点、位置和出场方式）。用户说「给这条素材做说明书」「帮我筛一下这条素材」「这条素材能用哪些、哪句可以下刀」「一共几个镜头、每个镜头第几帧到第几帧」「先把这个片子逐帧过一遍」「这条口播帮我出说明书和精剪建议」「口播里哪些停顿、口误、重复要剪掉」「这片子一共多少花字、每个什么时候出现」「把花字时间扒出来，我要重做花字」「帮我拉一下这几条参考片」「拉片，看看人家怎么剪的」「这几条素材一起跑说明书」时使用。不要用于一般的视频总结或点评（用 genius-omni），不要用于单纯语音转文字（用 genius-voice），不要用于只下载视频不分析（用 genius-download），不要用于实际剪辑、拼时间线、导出或生成视频（口播模式只给精剪建议）。"
metadata:
  version: "2.13.0"
---

# Genius Footage（素材说明书）

This skill exists to write **one footage brief per clip** for an editor: `<clip>.footage.md` (readable), `<clip>.footage.json` (full data: word times, measurements) and `<clip>.footage/` (storyboards), next to the clip. For a reference film it writes a breakdown instead: `<clip>.breakdown.md` / `.breakdown.json` (see Breakdown), plus one `拉片汇总-<time>.md` for several films. On request it writes the overlay sheet instead: `<clip>.overlays.md` / `.overlays.json` / `.overlays/` (see Overlay Sheet). Nothing else.

Format: AG_FOOTAGE/1.1, produced by `scripts/footage.py`. Cut detection rules: `references/measurement.md`. Editing lexicon read into the shot-description prompt (用途, 景别, 角度, 运镜, 标记): `references/lexicon.md` (edit it, not the code). Trigger checks: `evals/evals.json`. Dated measurements behind these rules: `references/field-notes.md`.

## Non-Negotiables

- Frame numbers, timecode, shot count and line start/end come only from local frame measurement (`measure.py`, frame differences checked against the local TransNetV2 model) and ASR word times (Doubao, `asr.py`). The model describes and judges, and refers to shots, lines, people and segments by ID only (S/U/P/G); the script converts IDs to frames.
- In the overlay sheet the model names numbered storyboard cells only; every frame comes from the sampling grid, or from a frame-labelled strip the agent looked at when it corrects one. Never have the model watch the video and report overlay times.
- Possible mishearings are proposed in `待确认`, never written into the transcript.
- The brief (or overlay sheet) is the deliverable: report status and paths, do not paste it unless asked.

## Run

```bash
python3 "<skill_dir>/scripts/setup.py"        # once per machine: TransNetV2 venv and model
python3 "<skill_dir>/scripts/footage.py" --check
python3 "<skill_dir>/scripts/footage.py" <clip|url> [<clip|url> …] [--talking-head | --breakdown] [--script script.txt] [--jobs 6] [--max-requests 8] [--model M] [--output text|json]
python3 "<skill_dir>/scripts/measure.py" <clip> [--output json]     # shot list only: no model, no brief
python3 "<skill_dir>/scripts/overlays.py" <clip> [--fps 1] [--model M] [--output text|json]   # overlay sheet only
python3 "<skill_dir>/scripts/selftest.py"     # offline check after editing the scripts: no network, no keys
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`, and TransNetV2 for shot detection: `scripts/setup.py` builds a venv with numpy and onnxruntime and downloads the MIT-licensed ONNX model (31 MB, SHA-256 checked) from Hugging Face (`huggingface.co/elya5/transnetv2`, mirror `huggingface.co/edgetools/transnetv2`) into a per-machine folder outside the skill (`~/.local/share/genius-footage`, `%LOCALAPPDATA%\genius-footage` on Windows, or `GENIUS_FOOTAGE_HOME`), so a synced skill folder never carries one machine's venv to another. It uses `uv` when present, otherwise Python 3.10+ with pip. The scripts switch to that venv by themselves; without it they stop with `DEPENDENCY_MISSING`: run `setup.py`, then rerun. The model is Gemini 4 on the CPA relay (`FOOTAGE_MODEL`, default `gemini-4-hydrogen-xhigh`); its key lives in `scripts/.env`, never in the package: `FOOTAGE_API_KEY` (or `CPA_API_KEY`), optional `FOOTAGE_BASE_URL` (default `https://cpa-jp.charles-ai.space/v1`). A `FOOTAGE_MODEL` / `--model` starting with `mimo-` (e.g. `mimo-v2.6-pro`) goes to Xiaomi MiMo instead: its key, `MIMO_API_KEY`, and optional `MIMO_BASE_URL` (default `https://api.xiaomimimo.com/v1`) are shared with genius-voice and read from its `scripts/.env` like the Doubao key below; the environment or this `scripts/.env` overrides them. Speech needs `DOUBAO_API_KEY` (Doubao file ASR 2.0 at `https://openspeech.bytedance.com/api/v3/auc/bigmodel/`, `scripts/asr.py`): the key belongs to genius-voice and is read from its `scripts/.env` (next to this skill, or `GENIUS_VOICE_DIR`); a `DOUBAO_API_KEY` in the environment or this `scripts/.env` overrides it; without it the transcript is skipped and the status is `needs_review`.

- Local video, or an `http(s)` link (or a whole share message), downloaded first (see Links). The folder next to the clip must be writable; otherwise it fails with `UNSUPPORTED_FORMAT`.
- Gemini: every request goes to `generateContent` and explicitly sends `generationConfig.thinkingConfig.thinkingLevel: "high"`, including image, video and text-only requests; the `-xhigh` model-name suffix is not a substitute. Files go inline as base64.
- MiMo (`mimo-*`): OpenAI-style `chat/completions` with `thinking: {"type": "enabled"}` (no thinking level), images as `image_url` and the whole-clip proxy as `video_url` at 2 fps. Thinking counts against the 32768-token output budget: a storyboard answer that thinks through all of it comes back empty and is asked once more. About 4.5× slower than Gemini on the default mode (`references/field-notes.md`).
- `--script`: a script or keyword file (names, brands, models). The model uses it to flag likely mishearings.
- Steps: `measure.py` (cuts frame by frame; frame differences and TransNetV2 read one decode, a cut both find is confirmed, a cut only one finds becomes a doubtful cut, a frame-difference suspect TransNetV2 scores below 0.1 is skipped) → doubtful cuts judged by the model on a storyboard → every shot described from its first / middle / last frames → `asr.py` with speaker labels (words → frame ranges and cut points: pause ≥4 frames is a clean cut, <2 frames at punctuation is run-together) → one whole-clip request (summary, people, segments, highlights, retakes, unusable shots, suspect words) → validate.
- A model request that fails or comes back short is asked once more by the script. One that fails twice leaves a hole instead of failing the clip: the brief is still written, the hole is listed in 待确认 and the status is `needs_review`. Only when the model returned nothing at all does the clip fail.
- Measured cuts and the transcript are cached per file (the folder is printed by `--check`), so a rerun, or another mode on the same clip, only repeats the model requests. To fill a hole, rerun the same command.
- Clips longer than 30 minutes skip the whole-clip step (warned).

## Talking Head（口播）

Use `--talking-head` when the clip is one person talking to camera in one take (口播, 一镜到底, 自拍讲解); ask if unsure, since a real multi-camera clip loses its weak cuts.

- Measured hard cuts stay; weak suspects are not sent to the model (hand-held shake, gestures and turning read as cuts there) and are marked `skipped`, not review items.
- Section 9 of the brief, from word times only: dead air, fillers at a line start or after punctuation, restarts inside a line. Hints, not cuts.
- The whole-clip request returns segments over lines, visual events tied to lines, and `keep[]`: line ID + `from` / `to` words copied verbatim from that line, in playback order. The script turns them into frames and writes section 8 精剪建议 (its padding and merging rule is printed there) plus `keep` / `edit` in the JSON. Quotes a little off still match (within a quarter of their characters, ≥4 characters), a `to` may close one of the next 3 lines, and `None` / `null` mean line start / end; a `from` / `to` that still does not match goes to `待确认` and `review.unmatched_keep`.
- The brief stays a brief: assembling or exporting the edit is a separate step for the editor or an editing tool.
- In the default mode, a clip that looks like 口播 gets a warning suggesting `--talking-head`; the mode never switches by itself.

## Several Clips（并行）

Pass several clips (or links) to one command: they run `--jobs` (default 6) at a time, and the text report has one section per clip. Do not start several commands at once instead: the cap on model requests in flight, `--max-requests` (default `FOOTAGE_MAX_REQUESTS` or 8), is per process, and more risks 429 / 5xx from the provider (retried after 5 / 15 / 30 s; lower the cap if retries pile up). Of those, requests carrying a whole-clip video (~30MB each) are capped at `FOOTAGE_MAX_VIDEO_REQUESTS` (default 2): more at once ran the CPA relay out of memory. One clip failing does not stop the others; its section shows `Error [CODE]` and the exit code is the first failure's.

## Breakdown（拉片）

`--breakdown` for a finished reference film the user wants to learn from, not footage to cut. Same measured shot list, cut check, shot descriptions and transcript; the whole-clip request instead answers how the film is built, by shot IDs, and the script adds rhythm figures computed from the measured shots (mean / median shot, cuts per minute, cuts per 5 / 10 / 30 s, per-segment pace, 景别 / 角度 / 运镜 counts).

- `<clip>.breakdown.md`: 1 概览 · 2 结构与叙事 (hook, arc, emotion curve, ending, selling points, segments with their narrative function) · 3 节奏与剪辑 (measured figures and curve, pace, 卡点, transitions, techniques) · 4 视听语言 · 5 包装 · 6 可借鉴手法 · 7 人物 · 8 镜头 · 9 台词 · 10 待确认. Every shot range the model cites gets its timecode.
- Several films with `--breakdown` also get `拉片汇总-<YYYYMMDD-HHMM>.md` next to the first one: a measured side-by-side table, then one text-only model request over the breakdowns (共同套路, 各自特色, 节奏对比, 可复用的结构模板, 拍摄与剪辑清单). `--no-compare` skips it; a failed comparison only warns.
- Report the 拉片 path(s) and the 汇总 path; do not paste the report unless asked.

## Links

A link, or a whole share message (「7.12 复制打开抖音… https://v.douyin.com/… 复制此链接」), is downloaded first through the genius-download skill (found next to this skill, in a usual skill folder, or at `GENIUS_DOWNLOAD_DIR`; `--check` shows which), then analysed like a local file. `--download-dir` and `--cookies-from-browser` are passed on; files land in genius-download's folder by default. Without genius-download a link fails with `DEPENDENCY_MISSING`. When the user only wants the files, use genius-download itself.

## Overlay Sheet（花字表）

For a finished edit whose 花字 (designed captions) and 人名条 (name lower thirds) are to be redesigned or covered. Not part of the brief, and it leaves the AG_FOOTAGE format alone.

Read `references/overlays.md` before running `overlays.py`: it holds what 入点 / 出点 / 可读 / 框 mean, what is and is not listed, and the **agent check that is required before delivering** (open every `check_*.jpg`, find the right frame with `--look`, apply with `--fix`, or `--fix` alone when nothing needs changing). `--fps 2` when overlays may be shorter than about one second.

## Report

The status (`ok` / `needs_review`), counts (shots, lines, people, segments), in talking-head mode the 精剪建议 line (pieces, seconds vs source), the `.footage.md` path, and every review, validation and warning line as printed. `needs_review` with only uncertain words is normal: list them for the user to confirm.

Breakdown: per film the status, counts and `.breakdown.md` path, then the `拉片汇总` path. Several clips: one block per clip, failures included.

Overlay sheet, after the agent check: the counts (花字, 人名条, other packaging), the `.overlays.md` path, and what the check changed (or that nothing needed changing).

Failures print `Error [CODE]: …` with a non-zero exit: `INPUT_NOT_FOUND` 3, `UNSUPPORTED_FORMAT` 4, `DEPENDENCY_MISSING` 5, `PROVIDER_ERROR` 6, `TIMEOUT` 7. Report the code and message as-is.

## Gotchas

- An unsure-versus-cut verdict can flip between runs (no temperature is pinned); a flipped unsure goes to review, never into the timeline silently. CG content swaps and picture-in-picture go to review as unsure.
- On a finished edit with music, sung lyrics and speech can land in one line, and cut points then fall inside the lyrics.
- Homophones survive ASR (采销 → 彩销); they appear as suspect words when the script or on-screen text shows the right spelling.
- ASR line numbering can differ between two transcriptions of one clip, so compare edits by frames, not U IDs.
- A whip-pan between two scenes is weak for both detectors (`references/measurement.md`): it reaches the storyboard check only when one of them flags it, otherwise the two scenes stay in one shot.
- A 24p picture stored on a 60 timebase reports `fps` 60 (the stream's nominal rate) while `tc_fps` and every timecode count 24; frame numbers are decoded pictures either way.
- TransNetV2 runs on the CPU in every clip's process; with several clips at once (`--jobs`) the runs share the cores, and other heavy work on the machine slows them a lot (see field notes). Its frames go through a temporary file of about 3.9 KB per frame (≈350 MB per hour at 25 fps).
- `needs_review` listing 模型请求失败 means a request failed twice: rerun the same command, only the missing requests cost time again.

## Resource Map

- `scripts/footage.py`: the brief (or 拉片 breakdown and comparison), end to end, one or several clips or links; `--check`.
- `scripts/measure.py`: frame-by-frame cut measurement, checked against TransNetV2; the shot list on its own.
- `scripts/transnet.py`: TransNetV2 on onnxruntime (windowing, per-frame probabilities), the per-machine folder, and the switch into its venv.
- `scripts/setup.py`: one-time per-machine setup of that venv and model; `--check` reports only.
- `scripts/overlays.py`: the overlay sheet (花字表), end to end, and its agent check (`--look`, `--fix`).
- `scripts/asr.py`: Doubao file ASR with word times and speaker labels.
- `scripts/client.py`: model requests (Gemini on the CPA relay, or Xiaomi MiMo), the shared key lookup, the retry loop, storyboard questions asked side by side with one re-ask, the per-file cache and the compressed whole-clip proxy.
- `scripts/storyboard.py`: exact-frame storyboard sheets with drawn-in labels.
- `scripts/selftest.py`: offline self-test on a built clip.
- `references/measurement.md`, `references/lexicon.md`, `references/overlays.md`, `references/field-notes.md`, `evals/evals.json`, `agents/openai.yaml`.
