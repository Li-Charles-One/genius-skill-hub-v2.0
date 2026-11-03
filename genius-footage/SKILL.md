---
name: genius-footage
description: "Genius 素材说明书：给一条视频素材生成剪辑用的 .footage.md（AG_FOOTAGE/1.0）：逐帧精确的镜头表、带说话人和可下刀点的台词表、人物、内容分段、金句、重拍与废片、可能听错的词。用户说「给这条素材做说明书」「帮我筛一下这条素材」「这条素材能用哪些、哪句可以下刀」时使用。不要用于一般的视频总结或点评（用 genius-omni），不要用于单纯语音转文字（用 genius-voice），不要用于成片交付前质检（用 genius-video-qc），不要用于剪辑或生成视频。"
metadata:
  version: "1.0.0"
---

# Genius Footage（素材说明书）

This skill exists to write **one footage brief per clip** for an editor: `<clip>.footage.md` (readable), `<clip>.footage.json` (full data: word times, measurements) and `<clip>.footage/` (storyboards), next to the clip. Nothing else.

Format: AG_FOOTAGE/1.0 (`ArtisticCut/AG_FOOTAGE.md`). Trigger checks: `evals/evals.json`.

## Non-Negotiables

- Frame numbers, timecode, shot count and line start/end come only from local frame measurement (genius-omni `measure.py`) and ASR word times (genius-voice). The model describes and judges, and refers to shots, lines, people and segments by ID only (S/U/P/G); the script converts IDs to frames.
- Possible mishearings are proposed in `待确认`, never written into the transcript.
- The brief is the deliverable: report status and paths, do not paste the brief unless asked.

## Run

```bash
python3 "<skill_dir>/scripts/footage.py" --check
python3 "<skill_dir>/scripts/footage.py" <clip> [--script script.txt] [--provider ID] [--model M] [--output text|json]
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe` and two sibling skills: genius-omni (measurement, storyboards, model calls and its `scripts/.env` keys) and genius-voice (ASR, its own keys). Override their locations with `FOOTAGE_OMNI_DIR` (omni's `scripts/` folder) and `FOOTAGE_VOICE_SCRIPT` (path to `voice.py`).

- Local video only. The folder next to the clip must be writable; otherwise it fails with `UNSUPPORTED_FORMAT`.
- `--script`: a script or keyword file (names, brands, models). The model uses it to flag likely mishearings.
- Steps: genius-omni `video-shots` (cuts measured frame by frame, doubtful spots checked on a storyboard, every shot described) → genius-voice `asr --speakers` (words → frame ranges and cut points: pause ≥4 frames is a clean cut, <2 frames at punctuation is run-together) → one whole-clip request (summary, people, segments, highlights, retakes, unusable shots, suspect words) → validate.
- Without genius-voice the transcript is skipped and the status is `needs_review`. Clips longer than omni's `VISION_MAX_SINGLE_SEC` skip the whole-clip step (warned).
- Run one clip at a time; parallel runs make the CPA gateway return 502. A 3-minute clip with ~120 shots took about 15 minutes.

## Report

The status (`ok` / `needs_review`), counts (shots, lines, people, segments), the `.footage.md` path, and every review, validation and warning line as printed. `needs_review` with only uncertain words is normal: list them for the user to confirm.

Failures print `Error [CODE]: …` with a non-zero exit (codes as in genius-omni: `INPUT_NOT_FOUND`, `UNSUPPORTED_FORMAT`, `DEPENDENCY_MISSING`, `PROVIDER_ERROR`, `TIMEOUT`). Report the code and message as-is.

## Gotchas

- Shot boundaries inside fast camera moves are still checked with only first / middle / last frames; a whip pan the measurement calls doubtful can be split by the storyboard check. Check one-frame shots in the table.
- On a finished edit with music, sung lyrics and speech can land in one line, and cut points then fall inside the lyrics.
- Homophones survive ASR (采销 → 彩销); they appear as suspect words when the script or on-screen text shows the right spelling.
