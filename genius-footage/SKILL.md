---
name: genius-footage
description: "Genius 素材说明书：给一条视频素材生成剪辑用的 .footage.md（AG_FOOTAGE/1.1）：逐帧精确的镜头表、带说话人和可下刀点的台词表、人物、内容分段、金句、重拍与废片、可能听错的词；也可只出逐帧精确的镜头表。用户说「给这条素材做说明书」「帮我筛一下这条素材」「这条素材能用哪些、哪句可以下刀」「一共几个镜头、每个镜头第几帧到第几帧」时使用。不要用于一般的视频总结或点评（用 genius-omni），不要用于单纯语音转文字（用 genius-voice），不要用于成片交付前质检，不要用于剪辑或生成视频。"
metadata:
  version: "2.3.4"
---

# Genius Footage（素材说明书）

This skill exists to write **one footage brief per clip** for an editor: `<clip>.footage.md` (readable), `<clip>.footage.json` (full data: word times, measurements) and `<clip>.footage/` (storyboards), next to the clip. Nothing else.

Format: AG_FOOTAGE/1.1, produced by `scripts/footage.py`. Cut detection rules: `references/measurement.md`. Editing lexicon read into the shot-description prompt (用途, 景别, 角度, 运镜, 标记): `references/lexicon.md` (edit it, not the code). The cut check keeps its own coarse categories. Trigger checks: `evals/evals.json`.

## Non-Negotiables

- Frame numbers, timecode, shot count and line start/end come only from local frame measurement (`measure.py`) and ASR word times (Doubao, `asr.py`). The model describes and judges, and refers to shots, lines, people and segments by ID only (S/U/P/G); the script converts IDs to frames.
- Possible mishearings are proposed in `待确认`, never written into the transcript.
- The brief is the deliverable: report status and paths, do not paste the brief unless asked.

## Run

```bash
python3 "<skill_dir>/scripts/footage.py" --check
python3 "<skill_dir>/scripts/footage.py" <clip> [--script script.txt] [--model M] [--workers 3] [--output text|json]
python3 "<skill_dir>/scripts/measure.py" <clip> [--output json]     # shot list only: no model, no brief
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`; no Python packages. The model key lives in `scripts/.env`, never in the package: `FOOTAGE_API_KEY` (or `CPA_API_KEY`); optional `FOOTAGE_BASE_URL` (default the CPA relay `https://cpa-jp.charles-ai.space/v1`) and `FOOTAGE_MODEL` (default `gemini-4-argon-high`). Speech needs `DOUBAO_API_KEY` (Doubao file ASR 2.0 at `https://openspeech.bytedance.com/api/v3/auc/bigmodel/`, `scripts/asr.py`, a copy of genius-voice's ASR code, so footage never calls genius-voice's script): the key belongs to genius-voice and is read from its `scripts/.env` (next to this skill, or `GENIUS_VOICE_DIR`); a `DOUBAO_API_KEY` in the environment or this `scripts/.env` overrides it; without it the transcript is skipped and the status is `needs_review`.

- Local video only. The folder next to the clip must be writable; otherwise it fails with `UNSUPPORTED_FORMAT`.
- `--script`: a script or keyword file (names, brands, models). The model uses it to flag likely mishearings.
- Steps: `measure.py` (cuts frame by frame) → doubtful cuts judged by the model on a storyboard (six frames each side of a jump, nine per second across a sustained change) → every shot described from its first / middle / last frames → `asr.py` with speaker labels (words → frame ranges and cut points: pause ≥4 frames is a clean cut, <2 frames at punctuation is run-together) → one whole-clip request (summary, people, segments, highlights, retakes, unusable shots, suspect words) → validate.
- Clips longer than 30 minutes skip the whole-clip step (warned).
- Speech and the whole-clip proxy start at once and run beside the storyboard steps; storyboard sheets go `--workers` (default 3) at a time. Run one clip at a time; more requests in flight make the CPA gateway return 502 (retried after 5 / 15 / 30 s). Measured: an 8-min clip with 217 shots took 7.2 min at 3 workers (17 min one sheet at a time), with no 502.

## Report

The status (`ok` / `needs_review`), counts (shots, lines, people, segments), the `.footage.md` path, and every review, validation and warning line as printed. `needs_review` with only uncertain words is normal: list them for the user to confirm.

Failures print `Error [CODE]: …` with a non-zero exit: `INPUT_NOT_FOUND` 3, `UNSUPPORTED_FORMAT` 4, `DEPENDENCY_MISSING` 5, `PROVIDER_ERROR` 6, `TIMEOUT` 7. Report the code and message as-is.

## Gotchas

- The model has the final say on doubtful cuts; the timeline stays measured. A one-frame jump starts on the frame the model points to; a sustained change starts on its measured first frame. 2.1.0 re-run (2026-11-03): on emsmart (35 suspects, CG + live) one suspected cut differed between three runs (X35 f4335 flips new shot ↔ unsure); on baiting 0 of 28 differed. No temperature is pinned, so an unsure-versus-cut boundary can flip between runs; a flipped unsure goes to review, never into the timeline silently. CG content swaps and picture-in-picture go to review as unsure.
- One model answer can omit the first groups of a sheet: a baiting run lost X01–X03, and the same page returned all three on three re-calls. Those suspects stay unchecked and land in review, so re-call a page whose answer came back short.
- Do not feed the lexicon to the cut check: its near-pairs (遮挡转场 / 遮挡穿过, 黑场 / 闪白, 叠化 / CG 内容替换) made verdicts flip (5–8 of 35 between runs).
- Two suspects close together on one transition (f4056 / f4062) can place the same cut a few frames apart between runs.
- On a finished edit with music, sung lyrics and speech can land in one line, and cut points then fall inside the lyrics.
- Homophones survive ASR (采销 → 彩销); they appear as suspect words when the script or on-screen text shows the right spelling.

## Resource Map

- `scripts/footage.py`: the brief, end to end; `--check`.
- `scripts/measure.py`: frame-by-frame cut measurement; the shot list on its own.
- `scripts/asr.py`: Doubao file ASR with word times and speaker labels.
- `scripts/client.py`: model requests (CPA relay by default) and the compressed whole-clip proxy.
- `scripts/storyboard.py`: exact-frame storyboard sheets with drawn-in labels.
- `references/measurement.md`, `references/lexicon.md`, `evals/evals.json`, `agents/openai.yaml`.
