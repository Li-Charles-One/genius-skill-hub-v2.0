---
name: genius-footage
description: "Genius 素材说明书：给一条视频（素材或成片）生成剪辑用的 .footage.md（AG_FOOTAGE/1.1）：逐帧精确的镜头表、带说话人和可下刀点的台词表、人物、内容分段、金句、重拍与废片、可能听错的词；口播（一镜到底、单人对镜头讲）可加口播模式，跳过逐帧切点核对，另出停顿、语气词、句内重复起头和按字精确到帧的精剪建议；拉片模式给一条或几条参考片（本地文件或链接）出拉片报告：结构与叙事、节奏数据与剪辑手法、视听语言、包装和可借鉴手法，几条一起拉时另出一份汇总对比；多条素材默认 6 条并行；视频下载模式只下载链接（B 站等用 yt-dlp，抖音、小红书用已登录的浏览器取文件）；也可只出逐帧精确的镜头表，或只出花字表（成片里每个花字、人名条的原文、约 0.1 秒精度的入点出点、位置和出场方式）。用户说「给这条素材做说明书」「帮我筛一下这条素材」「这条素材能用哪些、哪句可以下刀」「一共几个镜头、每个镜头第几帧到第几帧」「先把这个片子逐帧过一遍」「这条口播帮我出说明书和精剪建议」「口播里哪些停顿、口误、重复要剪掉」「这片子一共多少花字、每个什么时候出现」「把花字时间扒出来，我要重做花字」「帮我拉一下这几条参考片」「拉片，看看人家怎么剪的」「这几条素材一起跑说明书」「把这几个链接的视频下下来」时使用。不要用于一般的视频总结或点评（用 genius-omni），不要用于单纯语音转文字（用 genius-voice），不要用于实际剪辑、拼时间线、导出或生成视频（口播模式只给精剪建议）。"
metadata:
  version: "2.8.0"
---

# Genius Footage（素材说明书）

This skill exists to write **one footage brief per clip** for an editor: `<clip>.footage.md` (readable), `<clip>.footage.json` (full data: word times, measurements) and `<clip>.footage/` (storyboards), next to the clip. For a reference film it writes a breakdown instead: `<clip>.breakdown.md` / `.breakdown.json` (see Breakdown), plus one `拉片汇总-<time>.md` for several films. On request it writes the overlay sheet instead: `<clip>.overlays.md` / `.overlays.json` / `.overlays/` (`scripts/overlays.py`, see Overlay Sheet). Nothing else.

Format: AG_FOOTAGE/1.1, produced by `scripts/footage.py`. Cut detection rules: `references/measurement.md`. Editing lexicon read into the shot-description prompt (用途, 景别, 角度, 运镜, 标记): `references/lexicon.md` (edit it, not the code). The cut check keeps its own coarse categories. Trigger checks: `evals/evals.json`.

## Non-Negotiables

- Frame numbers, timecode, shot count and line start/end come only from local frame measurement (`measure.py`) and ASR word times (Doubao, `asr.py`). The model describes and judges, and refers to shots, lines, people and segments by ID only (S/U/P/G); the script converts IDs to frames.
- In the overlay sheet the model names numbered storyboard cells only; every frame comes from the sampling grid, or from a frame-labelled strip the agent looked at when it corrects one. Never have the model watch the video and report overlay times.
- Possible mishearings are proposed in `待确认`, never written into the transcript.
- The brief (or overlay sheet) is the deliverable: report status and paths, do not paste it unless asked.

## Run

```bash
python3 "<skill_dir>/scripts/footage.py" --check
python3 "<skill_dir>/scripts/footage.py" <clip|url> [<clip|url> …] [--talking-head | --breakdown] [--script script.txt] [--jobs 6] [--max-requests 8] [--model M] [--workers 3] [--output text|json]
python3 "<skill_dir>/scripts/footage.py" --download-only <url> [<url> …] [--download-dir DIR]   # 视频下载 only, no analysis
python3 "<skill_dir>/scripts/measure.py" <clip> [--output json]     # shot list only: no model, no brief
python3 "<skill_dir>/scripts/overlays.py" <clip> [--fps 1] [--model M] [--workers 3] [--output text|json]   # overlay sheet only
python3 "<skill_dir>/scripts/overlays.py" <clip> --look ID FIRST-LAST[:STEP]     # agent check: labelled frames
python3 "<skill_dir>/scripts/overlays.py" <clip> --fix ["ID in=N" "ID out=N" "ID text=…" "ID drop" …]   # agent check: apply
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`; no Python packages. The model key lives in `scripts/.env`, never in the package: `FOOTAGE_API_KEY` (or `CPA_API_KEY`); optional `FOOTAGE_BASE_URL` (default the CPA relay `https://cpa-jp.charles-ai.space/v1`) and `FOOTAGE_MODEL` (default `gemini-4-argon-high`). Speech needs `DOUBAO_API_KEY` (Doubao file ASR 2.0 at `https://openspeech.bytedance.com/api/v3/auc/bigmodel/`, `scripts/asr.py`, a copy of genius-voice's ASR code, so footage never calls genius-voice's script): the key belongs to genius-voice and is read from its `scripts/.env` (next to this skill, or `GENIUS_VOICE_DIR`); a `DOUBAO_API_KEY` in the environment or this `scripts/.env` overrides it; without it the transcript is skipped and the status is `needs_review`.

- Local video, or an `http(s)` link downloaded first with `yt-dlp` (≤1080p mp4, into `--download-dir`, default `~/Downloads/genius-footage/`; `--cookies-from-browser chrome` for yt-dlp sites that need a login). Without `yt-dlp` a link fails with `DEPENDENCY_MISSING`; ask before installing it (`brew install yt-dlp`). Per site, see Download. The folder next to the clip must be writable; otherwise it fails with `UNSUPPORTED_FORMAT`.
- `--script`: a script or keyword file (names, brands, models). The model uses it to flag likely mishearings.
- Steps: `measure.py` (cuts frame by frame) → doubtful cuts judged by the model on a storyboard (six frames each side of a jump, nine per second across a sustained change) → every shot described from its first / middle / last frames → `asr.py` with speaker labels (words → frame ranges and cut points: pause ≥4 frames is a clean cut, <2 frames at punctuation is run-together) → one whole-clip request (summary, people, segments, highlights, retakes, unusable shots, suspect words) → validate.
- Clips longer than 30 minutes skip the whole-clip step (warned).

## Talking Head（口播）

Use `--talking-head` when the clip is one person talking to camera in one take (口播, 一镜到底, 自拍讲解); ask if unsure, since a real multi-camera clip loses its weak cuts.

- Measured hard cuts stay; weak suspects are not sent to the model (hand-held shake, gestures and turning read as cuts there) and are marked `skipped`, not review items.
- From word times only, section 9 of the brief: dead air ≥0.8 s, fillers (嗯呃额啊哦唔 at a line start or after punctuation), restarts inside a line (a run of ≥3 characters said again, or 我我-type stutters). Hints, not cuts.
- The whole-clip request returns segments over lines (`us`), visual events tied to lines, and `keep[]`: line ID + `from` / `to` words copied verbatim from that line, in playback order. The script turns them into frames (first word −6, last word +12, never into a neighbouring word; a repeated `from` resolves to its last occurrence), merges pieces closer than 20 frames, and writes section 8 精剪建议 plus `keep` / `edit` in the JSON. A `from` / `to` that does not match the line goes to `待确认` and `review.unmatched_keep`.
- The brief stays a brief: assembling or exporting the edit is a separate step for the editor or an editing tool.
- In the default mode, a clip with ≤2 measured shots, >50 suspects and speech over 60% gets a warning suggesting `--talking-head`; the mode never switches by itself.

## Several Clips（并行）

Pass several clips (or links) to one command: they run `--jobs` (default 6) at a time, and the text report has one section per clip. Do not start several commands at once instead: the cap below is per process.

- Within a clip, speech and the whole-clip proxy start at once and run beside the storyboard steps; storyboard sheets go `--workers` (default 3) at a time.
- All clips share one cap on model requests in flight, `--max-requests` (default `FOOTAGE_MAX_REQUESTS` or 8): more make the CPA gateway return 502 (retried after 5 / 15 / 30 s). Cut measurement runs in separate processes, one per clip; ASR (Doubao) and downloads are not capped.
- One clip failing does not stop the others; its section shows `Error [CODE]` and the exit code is the first failure's.
- Measured single-clip: an 8-min clip with 217 shots took 7.2 min at 3 workers (17 min one sheet at a time), with no 502.

## Breakdown（拉片）

`--breakdown` for a finished reference film the user wants to learn from, not footage to cut. Same measured shot list, cut check, shot descriptions and transcript; the whole-clip request instead answers how the film is built, by shot IDs, and the script adds rhythm figures computed from the measured shots (mean / median shot, cuts per minute, cuts per 5 / 10 / 30 s, per-segment pace, 景别 / 角度 / 运镜 counts).

- `<clip>.breakdown.md`: 1 概览 · 2 结构与叙事 (hook, arc, emotion curve, ending, selling points, segments with their narrative function) · 3 节奏与剪辑 (measured figures and curve, pace, 卡点, transitions, techniques) · 4 视听语言 · 5 包装 · 6 可借鉴手法 · 7 人物 · 8 镜头 · 9 台词 · 10 待确认. Every shot range the model cites gets its timecode.
- Several films with `--breakdown` also get `拉片汇总-<YYYYMMDD-HHMM>.md` next to the first one: a measured side-by-side table, then one text-only model request over the breakdowns (共同套路, 各自特色, 节奏对比, 可复用的结构模板, 拍摄与剪辑清单). `--no-compare` skips it; a failed comparison only warns.
- Report the 拉片 path(s) and the 汇总 path; do not paste the report unless asked.

## Download（视频下载）

Fully automatic, in the script: `--download-only` when the user only wants the files; any other mode downloads links first by itself. Files go to `--download-dir` (default `~/Downloads/genius-footage/`), named `<title ≤60 bytes> [<id>].mp4`; a link already there is not downloaded again. Several links download `--jobs` at a time.

| Site | Route | Checked 2026-11-11 |
|---|---|---|
| B 站 and other yt-dlp sites | yt-dlp, ≤1080p | 2 links, 1080p |
| 小红书 | RedFox; then yt-dlp (link must carry `xsec_token`, refused without); then ego browser | RedFox 62 s 1280×720 at 0.7 Mb/s (the browser got the same note at 1.0 Mb/s); yt-dlp 70 s 1496×720 |
| 抖音 (`douyin.com`, `v.douyin.com` short links) | RedFox; then ego browser | RedFox, 3 links in parallel: 1080×1920 at 1.3–1.6 Mb/s (the browser got 720×1280 at 0.7 Mb/s, one 576×1024 at 0.09 Mb/s); a share message works |

A whole share message (「7.12 复制打开抖音… https://v.douyin.com/… 复制此链接」) works as input: it goes to RedFox as-is, and its link to the other routes.

RedFox（红狐数据, redfox.hk）: a paid API, about ¥0.03 a call, `POST https://redfox.hk/story/api/parseWork/videoDownload/{douyin|xhs}` with header `REDFOX_API_KEY` and body `{"url": "<link or share message>"}`; success is `code` 2000 with `data.videoUrl` (or a `resources[]` item of `type` video). The key lives in `scripts/.env` as `REDFOX_API_KEY` (the user writes it; never ask for it in chat). Measured: 4 links in parallel in 11 s. No key, an error code (3201 = balance used up; each call costs 0.6 points), a note without video, or a failed file download falls back silently to the next route; `--check` shows whether the key is set. Links sent there leave this machine.

The browser route needs ego lite (`ego-browser` on PATH) with the user logged in to the site; each download opens its own task space and closes it. 抖音: the 精选 player (`jingxuan?modal_id=<id>`) is opened, and the file the player requests (a `douyinvod.com` URL carrying `__vid=<id>`) is saved from that page. 小红书: the file comes from the note data, `window.__INITIAL_STATE__.note.noteDetailMap[<id>].note.video.media.stream` (highest `height`). A login or verification wall fails with a hint: ask the user to log in in ego, then rerun.

Why not simpler:
- yt-dlp 抖音: its extractor (`tiktok.py`, `DouyinIE`) calls `/aweme/v1/web/aweme/detail/` with the video ID only; the site now needs an `a_bogus` signature that obfuscated page JavaScript computes, which yt-dlp does not run (a TODO in its source). The API answers 403 and yt-dlp says "Fresh cookies are needed" even with logged-in cookies.
- 抖音 in a fresh browser tab: opening `/video/<id>` redirects to 精选 with some other video; the page carries no video data and the `<video>` plays a `blob:`. Always check the saved file's duration against the page.
- 小红书 without `xsec_token`: the site answers 404「当前笔记暂时无法浏览」, in yt-dlp and in the browser alike. Links copied from search results or the share button have it.

## Overlay Sheet（花字表）

For a finished edit whose 花字 (designed captions) and 人名条 (name lower thirds) are to be redesigned or covered. Not part of the brief, and it leaves the AG_FOOTAGE format alone.

- Steps: find (one frame per second, `--fps`, on numbered 384×216 storyboard sheets, 40 cells each; the model names the cells each overlay is on) → read (one full-resolution frame per overlay, 60% of the way through its cells; the model copies the text and boxes it) → edges (cells cropped around that box, about every 0.1 s across the gap between two samples; the model picks the first / last cell where any part shows, searching up to two more seconds out when it already shows at a run's outer end) → `measure.py` cuts say how each one enters and leaves (with a cut, a few frames before or after one, or inside a shot).
- In and out are a reference for the editor, who sets the exact frames: about 0.1 s precision (one edge cell, 5 frames at 50 fps), no every-frame pass. Definitions in the sheet: 入点 = first cell where any element shows (lines, bars and sparkles that lead the text included); 出点 = last cell where any shows, inclusive (an editor enters 出点 + 1); 可读 = first cell where its first line is complete. The box is the model's, on the full-resolution frame: approximate, widen it before covering an old overlay.
- Listed with sampled times only (± one sample): 3D text signs (字牌), title cards, full-screen graphics, labels. Not listed: dialogue subtitles, watermarks, text filmed in the scene. Not provided: the frame each further line of a multi-line overlay appears.
- `--fps 2` doubles the find sheets; use it when overlays may be shorter than about one second.

### Agent check, before delivering

The model's sheet is checked by the agent, roughly, and the agent corrects the final output. Every frame the agent writes comes from a labelled frame it looked at, never from playback or estimation.

1. Open every `<clip>.overlays/check_*.jpg`: one row per overlay, cropped to its box. `ID-1` is one cell before 入点 and should not show it, `ID-2` 入点 and `ID-3` 出点 should, `ID-4` one cell after 出点 should not. Compare the table text with `read_NN.jpg` when in doubt.
2. Roughly right passes: up to about 0.2 s off is fine, so a faint first frame of a fade showing in `ID-1` is not a fault, nor an empty `ID-2` on a cut frame or an empty `ID-3` at the tail of a fade-out (edges are snapped to cuts and the last faint frames count). Fix what is clearly wrong: the overlay plainly in `ID-1` or `ID-4`, missing from `ID-2` or `ID-3`, wrong text, not a 花字 / 人名条 at all, or a review line that does not hold (先在上一个镜头出现 is right only if it already shows before that cut).
3. To find the right frame: `--look ID FIRST-LAST[:STEP]` writes a strip cropped to that overlay (`full` instead of an ID for the whole frame), each cell labelled with its frame number, at most 40 cells.
4. Apply: `--fix "N1 in=1149" "H06 text=…" "H12 drop"`, or `--fix` alone when nothing needs changing. Timecode, duration and the enter / leave wording are recomputed; the sheet's status becomes ok and its last section lists what the check changed.

## Report

The status (`ok` / `needs_review`), counts (shots, lines, people, segments), in talking-head mode the 精剪建议 line (pieces, seconds vs source), the `.footage.md` path, and every review, validation and warning line as printed. `needs_review` with only uncertain words is normal: list them for the user to confirm.

Breakdown: per film the status, counts and `.breakdown.md` path, then the `拉片汇总` path. Several clips: one block per clip, failures included.

Overlay sheet, after the agent check: the counts (花字, 人名条, other packaging), the `.overlays.md` path, and what the check changed (or that nothing needed changing).

Failures print `Error [CODE]: …` with a non-zero exit: `INPUT_NOT_FOUND` 3, `UNSUPPORTED_FORMAT` 4, `DEPENDENCY_MISSING` 5, `PROVIDER_ERROR` 6, `TIMEOUT` 7. Report the code and message as-is.

## Gotchas

- The model has the final say on doubtful cuts; the timeline stays measured. A one-frame jump starts on the frame the model points to; a sustained change starts on its measured first frame. 2.1.0 re-run (2026-11-03): on emsmart (35 suspects, CG + live) one suspected cut differed between three runs (X35 f4335 flips new shot ↔ unsure); on baiting 0 of 28 differed. No temperature is pinned, so an unsure-versus-cut boundary can flip between runs; a flipped unsure goes to review, never into the timeline silently. CG content swaps and picture-in-picture go to review as unsure.
- One model answer can omit the first groups of a sheet: a baiting run lost X01–X03, and the same page returned all three on three re-calls. Those suspects stay unchecked and land in review, so re-call a page whose answer came back short.
- Do not feed the lexicon to the cut check: its near-pairs (遮挡转场 / 遮挡穿过, 黑场 / 闪白, 叠化 / CG 内容替换) made verdicts flip (5–8 of 35 between runs).
- Two suspects close together on one transition (f4056 / f4062) can place the same cut a few frames apart between runs.
- On a finished edit with music, sung lyrics and speech can land in one line, and cut points then fall inside the lyrics.
- Homophones survive ASR (采销 → 彩销); they appear as suspect words when the script or on-screen text shows the right spelling.
- Overlay text must be read on the full-resolution frame: on 384-px cells the model misread brand names differently every run and once invented text (「拿捏Midea！」 for 「京东JWELL」). The read pass got 20/20 on 京东.mp4 (7:10, 17 花字 + 3 人名条, hand-checked baseline, 2026-11-05).
- Overlay edges on that clip (2.4.1: 0.1 s cells, edges snapped to a measured cut inside their cell): out-points 20/20 within 5 frames; in-points 17/20, late on faint fade-ins (H07 +10, H11 +6) because the model picks the first cell it can clearly see. Exit wording matched the hand check on 18/20; a cut `measure.py` misses (weak suspects stay unchecked here) turns 随镜头切走 into 在镜头内消失. 4 min, about 29 requests at 3 workers. 2.4.0's extra every-frame pass took 7 min and still left fade-ins 3–6 frames late.
- Agent check on 京东.mp4 (2.5.0): 4 check sheets and 2 `--look` strips, one fix (人名条 text 「韩 耘」 → 「韩耘」, letter spacing read as a space); after it count and text 20/20, out-points 20/20 and in-points 18/20 within 5 frames, the other two faint fade-in starts within 0.2 s, passed as roughly right.
- A run widened into the previous shot can take other text there for the overlay: N1 came out 14 and 24 frames early on two runs (a 3D sign in the crop). True early entries (H16, H17) look the same, so every 先在上一个镜头出现 goes to review.
- 3D text signs get listed as 花字 on the find sheets; the read pass sees no overlay text on them and moves them to other packaging as 字牌或实拍文字, with a warning. A caption that grows out of a 3D sign can carry the sign's text in its read (H06 once read 爆款 / 的诞生 / …).
- Talking head on a hand-held 口播 (IMG_7724, 6:32, one take, 2026-11-10): the default mode flagged 381 weak suspects (90 sheets, about 20 min) and the cut check turned the one take into 12 shots (IMG_7722, 3:57: 6). `--talking-head` (2.6.0): 1 shot, 3 min 16 s. Its keep[] gave 20 pieces, 209 s; against a hand-made edit of the same clip (208 s) 187 s overlap (90%). It kept two messy restart passages the hand edit dropped (~8 s) and moved the hook to the front on its own. ASR line numbering differs between runs (63 vs 66 lines), so compare edits by frames, not U IDs.
- Once in two runs the single shot-description request got no reply within 300 s (`TIMEOUT`, exit 7); the rerun passed in about a minute. Timeouts are not retried, so rerun the clip.
- Boxes drawn on storyboard sheets are unreliable; on the full-resolution frame they were right on 22 of 23, the miss a half-drawn name bar.

## Resource Map

- `scripts/footage.py`: the brief (or 拉片 breakdown and comparison), end to end, one or several clips; links via yt-dlp; `--download-only`; `--check`.
- `scripts/measure.py`: frame-by-frame cut measurement; the shot list on its own.
- `scripts/overlays.py`: the overlay sheet (花字表), end to end.
- `scripts/asr.py`: Doubao file ASR with word times and speaker labels.
- `scripts/client.py`: model requests (CPA relay by default) and the compressed whole-clip proxy.
- `scripts/storyboard.py`: exact-frame storyboard sheets with drawn-in labels.
- `references/measurement.md`, `references/lexicon.md`, `evals/evals.json`, `agents/openai.yaml`.
