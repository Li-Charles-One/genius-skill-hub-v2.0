---
name: genius-footage
description: "Genius 素材说明书：给一条视频（素材或成片）生成剪辑用的 .footage.md：逐帧精确的镜头表、带说话人和可下刀点的台词表、人物、内容分段、金句、重拍与废片、可能听错的词；口播（一镜到底、单人对镜头讲）可加口播模式，另出停顿、语气词、句内重复起头和按字精确到帧的精剪建议；拉片模式给一条或几条参考片（本地文件或链接）出拉片报告：结构与叙事、节奏数据与剪辑手法、视听语言、包装和可借鉴手法，几条一起拉时另出一份汇总对比；多条素材并行；视频下载模式只下载链接（B 站、抖音、小红书等）；也可只出逐帧精确的镜头表，或只出花字表（成片里每个花字、人名条的原文、入点出点、位置和出场方式）。用户说「给这条素材做说明书」「帮我筛一下这条素材」「这条素材能用哪些、哪句可以下刀」「一共几个镜头、每个镜头第几帧到第几帧」「先把这个片子逐帧过一遍」「这条口播帮我出说明书和精剪建议」「口播里哪些停顿、口误、重复要剪掉」「这片子一共多少花字、每个什么时候出现」「把花字时间扒出来，我要重做花字」「帮我拉一下这几条参考片」「拉片，看看人家怎么剪的」「这几条素材一起跑说明书」「把这几个链接的视频下下来」时使用。不要用于一般的视频总结或点评（用 genius-omni），不要用于单纯语音转文字（用 genius-voice），不要用于实际剪辑、拼时间线、导出或生成视频（口播模式只给精剪建议）。"
metadata:
  version: "2.9.0"
---

# Genius Footage（素材说明书）

This skill exists to write **one footage brief per clip** for an editor: `<clip>.footage.md` (readable), `<clip>.footage.json` (full data: word times, measurements) and `<clip>.footage/` (storyboards), next to the clip. For a reference film it writes a breakdown instead: `<clip>.breakdown.md` / `.breakdown.json` (see Breakdown), plus one `拉片汇总-<time>.md` for several films. On request it writes the overlay sheet instead: `<clip>.overlays.md` / `.overlays.json` / `.overlays/` (see Overlay Sheet). Nothing else.

Format: AG_FOOTAGE/1.1, produced by `scripts/footage.py`. Cut detection rules: `references/measurement.md`. Editing lexicon read into the shot-description prompt (用途, 景别, 角度, 运镜, 标记): `references/lexicon.md` (edit it, not the code). Trigger checks: `evals/evals.json`. Dated measurements behind these rules: `references/field-notes.md`.

## Non-Negotiables

- Frame numbers, timecode, shot count and line start/end come only from local frame measurement (`measure.py`) and ASR word times (Doubao, `asr.py`). The model describes and judges, and refers to shots, lines, people and segments by ID only (S/U/P/G); the script converts IDs to frames.
- In the overlay sheet the model names numbered storyboard cells only; every frame comes from the sampling grid, or from a frame-labelled strip the agent looked at when it corrects one. Never have the model watch the video and report overlay times.
- Possible mishearings are proposed in `待确认`, never written into the transcript.
- The brief (or overlay sheet) is the deliverable: report status and paths, do not paste it unless asked.

## Run

```bash
python3 "<skill_dir>/scripts/footage.py" --check
python3 "<skill_dir>/scripts/footage.py" <clip|url> [<clip|url> …] [--talking-head | --breakdown] [--script script.txt] [--jobs 6] [--max-requests 8] [--model M] [--output text|json]
python3 "<skill_dir>/scripts/footage.py" --download-only <url> [<url> …] [--download-dir DIR]   # 视频下载 only, no analysis
python3 "<skill_dir>/scripts/measure.py" <clip> [--output json]     # shot list only: no model, no brief
python3 "<skill_dir>/scripts/overlays.py" <clip> [--fps 1] [--model M] [--output text|json]   # overlay sheet only
python3 "<skill_dir>/scripts/selftest.py"     # offline check after editing the scripts: no network, no keys
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`; no Python packages. The model key lives in `scripts/.env`, never in the package: `FOOTAGE_API_KEY` (or `CPA_API_KEY`); optional `FOOTAGE_BASE_URL` (default the CPA relay `https://cpa-jp.charles-ai.space/v1`) and `FOOTAGE_MODEL` (default `gemini-4-hydrogen-xhigh`). Speech needs `DOUBAO_API_KEY` (Doubao file ASR 2.0 at `https://openspeech.bytedance.com/api/v3/auc/bigmodel/`, `scripts/asr.py`): the key belongs to genius-voice and is read from its `scripts/.env` (next to this skill, or `GENIUS_VOICE_DIR`); a `DOUBAO_API_KEY` in the environment or this `scripts/.env` overrides it; without it the transcript is skipped and the status is `needs_review`.

- Local video, or an `http(s)` link, downloaded first (see Download). The folder next to the clip must be writable; otherwise it fails with `UNSUPPORTED_FORMAT`.
- Every model request explicitly sends `generationConfig.thinkingConfig.thinkingLevel: "high"`, including image, video and text-only requests; a `-high` model-name suffix is not a substitute. This uses the Gemini 3/4 [thinking-level API](https://ai.google.dev/gemini-api/docs/generate-content/thinking), not the legacy `thinkingBudget` parameter.
- Fallback model: a `FOOTAGE_MODEL` starting with `mimo-` (e.g. `mimo-v2.6-pro`, with `FOOTAGE_BASE_URL` / `FOOTAGE_API_KEY` set to Xiaomi's endpoint and key) goes to Xiaomi's OpenAI-style `chat/completions` with `thinking: {"type": "enabled"}` instead, which has no thinking level. Use it only when the CPA relay is down: it was about 5.6× slower on the default mode and once thought through its whole output budget (`references/field-notes.md`).
- `--script`: a script or keyword file (names, brands, models). The model uses it to flag likely mishearings.
- Steps: `measure.py` (cuts frame by frame) → doubtful cuts judged by the model on a storyboard → every shot described from its first / middle / last frames → `asr.py` with speaker labels (words → frame ranges and cut points: pause ≥4 frames is a clean cut, <2 frames at punctuation is run-together) → one whole-clip request (summary, people, segments, highlights, retakes, unusable shots, suspect words) → validate.
- A model request that fails or comes back short is asked once more by the script. One that fails twice leaves a hole instead of failing the clip: the brief is still written, the hole is listed in 待确认 and the status is `needs_review`. Only when the model returned nothing at all does the clip fail.
- Measured cuts and the transcript are cached per file (the folder is printed by `--check`), so a rerun, or another mode on the same clip, only repeats the model requests. To fill a hole, rerun the same command.
- Clips longer than 30 minutes skip the whole-clip step (warned).

## Talking Head（口播）

Use `--talking-head` when the clip is one person talking to camera in one take (口播, 一镜到底, 自拍讲解); ask if unsure, since a real multi-camera clip loses its weak cuts.

- Measured hard cuts stay; weak suspects are not sent to the model (hand-held shake, gestures and turning read as cuts there) and are marked `skipped`, not review items.
- Section 9 of the brief, from word times only: dead air, fillers at a line start or after punctuation, restarts inside a line. Hints, not cuts.
- The whole-clip request returns segments over lines, visual events tied to lines, and `keep[]`: line ID + `from` / `to` words copied verbatim from that line, in playback order. The script turns them into frames and writes section 8 精剪建议 (its padding and merging rule is printed there) plus `keep` / `edit` in the JSON. A `from` / `to` that does not match the line goes to `待确认` and `review.unmatched_keep`.
- The brief stays a brief: assembling or exporting the edit is a separate step for the editor or an editing tool.
- In the default mode, a clip that looks like 口播 gets a warning suggesting `--talking-head`; the mode never switches by itself.

## Several Clips（并行）

Pass several clips (or links) to one command: they run `--jobs` (default 6) at a time, and the text report has one section per clip. Do not start several commands at once instead: the cap on model requests in flight, `--max-requests` (default `FOOTAGE_MAX_REQUESTS` or 8), is per process, and more makes the CPA gateway return 502 (retried after 5 / 15 / 30 s; lower the cap if retries pile up). One clip failing does not stop the others; its section shows `Error [CODE]` and the exit code is the first failure's.

## Breakdown（拉片）

`--breakdown` for a finished reference film the user wants to learn from, not footage to cut. Same measured shot list, cut check, shot descriptions and transcript; the whole-clip request instead answers how the film is built, by shot IDs, and the script adds rhythm figures computed from the measured shots (mean / median shot, cuts per minute, cuts per 5 / 10 / 30 s, per-segment pace, 景别 / 角度 / 运镜 counts).

- `<clip>.breakdown.md`: 1 概览 · 2 结构与叙事 (hook, arc, emotion curve, ending, selling points, segments with their narrative function) · 3 节奏与剪辑 (measured figures and curve, pace, 卡点, transitions, techniques) · 4 视听语言 · 5 包装 · 6 可借鉴手法 · 7 人物 · 8 镜头 · 9 台词 · 10 待确认. Every shot range the model cites gets its timecode.
- Several films with `--breakdown` also get `拉片汇总-<YYYYMMDD-HHMM>.md` next to the first one: a measured side-by-side table, then one text-only model request over the breakdowns (共同套路, 各自特色, 节奏对比, 可复用的结构模板, 拍摄与剪辑清单). `--no-compare` skips it; a failed comparison only warns.
- Report the 拉片 path(s) and the 汇总 path; do not paste the report unless asked.

## Download（视频下载）

Fully automatic, in the script: `--download-only` when the user only wants the files; any other mode downloads links first by itself. Files go to `--download-dir` (default `~/Downloads/genius-footage/`), named `<title ≤60 bytes> [<id>].mp4`; a link already there is not downloaded again. A whole share message (「7.12 复制打开抖音… https://v.douyin.com/… 复制此链接」) works as input.

- B 站 and other sites: `yt-dlp` (≤1080p; `--cookies-from-browser chrome` when a login is needed). Without `yt-dlp` a link fails with `DEPENDENCY_MISSING`; ask before installing it (`brew install yt-dlp`).
- 抖音 / 小红书: RedFox first, a paid API (about ¥0.03 a call; links sent there leave this machine). Its key lives in `scripts/.env` as `REDFOX_API_KEY`: the user writes it, never ask for it in chat. Without it, or when it fails, the script falls back by itself to yt-dlp (小红书) and the logged-in ego browser.
- A 小红书 link must carry `xsec_token` (copied from search results or the share button); without it the site shows nothing and the script refuses.
- A login or verification wall in the browser route fails with a hint: ask the user to log in in ego, then rerun.

Routes per site, measurements and why the simpler routes do not work: `references/download.md`.

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
- A whip-pan between two scenes is not detected as a cut (`references/measurement.md`); the two scenes stay in one shot.
- `needs_review` listing 模型请求失败 means a request failed twice: rerun the same command, only the missing requests cost time again.

## Resource Map

- `scripts/footage.py`: the brief (or 拉片 breakdown and comparison), end to end, one or several clips; `--download-only`; `--check`.
- `scripts/measure.py`: frame-by-frame cut measurement; the shot list on its own.
- `scripts/overlays.py`: the overlay sheet (花字表), end to end, and its agent check (`--look`, `--fix`).
- `scripts/asr.py`: Doubao file ASR with word times and speaker labels.
- `scripts/client.py`: model requests (CPA relay by default), the retry loop, storyboard questions asked side by side with one re-ask, the per-file cache and the compressed whole-clip proxy.
- `scripts/storyboard.py`: exact-frame storyboard sheets with drawn-in labels.
- `scripts/download.py`: links → local mp4 (RedFox, yt-dlp, ego browser).
- `scripts/selftest.py`: offline self-test on a built clip.
- `references/measurement.md`, `references/lexicon.md`, `references/overlays.md`, `references/download.md`, `references/field-notes.md`, `evals/evals.json`, `agents/openai.yaml`.
