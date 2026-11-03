---
name: genius-footage
description: "Genius 素材说明书：给一条视频素材生成剪辑用的 .footage.md（AG_FOOTAGE/1.0）：逐帧精确的镜头表、带说话人和可下刀点的台词表、人物、内容分段、金句、重拍与废片、可能听错的词；也可只出逐帧精确的镜头表。用户说「给这条素材做说明书」「帮我筛一下这条素材」「这条素材能用哪些、哪句可以下刀」「一共几个镜头、每个镜头第几帧到第几帧」时使用。不要用于一般的视频总结或点评（用 genius-omni），不要用于单纯语音转文字（用 genius-voice），不要用于成片交付前质检（用 genius-video-qc），不要用于剪辑或生成视频。"
metadata:
  version: "2.0.0"
---

# Genius Footage（素材说明书）

This skill exists to write **one footage brief per clip** for an editor: `<clip>.footage.md` (readable), `<clip>.footage.json` (full data: word times, measurements) and `<clip>.footage/` (storyboards), next to the clip. Nothing else.

Format: AG_FOOTAGE/1.0 (`ArtisticCut/AG_FOOTAGE.md`). Cut detection rules: `references/measurement.md`. Trigger checks: `evals/evals.json`.

## Non-Negotiables

- Frame numbers, timecode, shot count and line start/end come only from local frame measurement (`measure.py`) and ASR word times (genius-voice). The model describes and judges, and refers to shots, lines, people and segments by ID only (S/U/P/G); the script converts IDs to frames.
- Possible mishearings are proposed in `待确认`, never written into the transcript.
- The brief is the deliverable: report status and paths, do not paste the brief unless asked.

## Run

```bash
python3 "<skill_dir>/scripts/footage.py" --check
python3 "<skill_dir>/scripts/footage.py" <clip> [--script script.txt] [--model M] [--output text|json]
python3 "<skill_dir>/scripts/measure.py" <clip> [--output json]     # shot list only: no model, no brief
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`; no Python packages. The model key lives in `scripts/.env`, never in the package: `FOOTAGE_API_KEY` (or `CPA_API_KEY`); optional `FOOTAGE_BASE_URL` (default the CPA relay) and `FOOTAGE_MODEL` (default `gemini-4-argon-high`). Speech comes from genius-voice in a sibling folder (`FOOTAGE_VOICE_SCRIPT` points elsewhere); without it the transcript is skipped and the status is `needs_review`.

- Local video only. The folder next to the clip must be writable; otherwise it fails with `UNSUPPORTED_FORMAT`.
- `--script`: a script or keyword file (names, brands, models). The model uses it to flag likely mishearings.
- Steps: `measure.py` (cuts frame by frame) → doubtful cuts checked on a storyboard → every shot described from its first / middle / last frames → genius-voice `asr --speakers` (words → frame ranges and cut points: pause ≥4 frames is a clean cut, <2 frames at punctuation is run-together) → one whole-clip request (summary, people, segments, highlights, retakes, unusable shots, suspect words) → validate.
- Clips longer than 30 minutes skip the whole-clip step (warned).
- Run one clip at a time; parallel runs make the CPA gateway return 502 (retried after 5 / 15 / 30 s). A 3-minute clip with ~120 shots took about 15 minutes.

## Report

The status (`ok` / `needs_review`), counts (shots, lines, people, segments), the `.footage.md` path, and every review, validation and warning line as printed. `needs_review` with only uncertain words is normal: list them for the user to confirm.

Failures print `Error [CODE]: …` with a non-zero exit: `INPUT_NOT_FOUND` 3, `UNSUPPORTED_FORMAT` 4, `DEPENDENCY_MISSING` 5, `PROVIDER_ERROR` 6, `TIMEOUT` 7. Report the code and message as-is.

## Gotchas

- The storyboard check of doubtful cuts is not stable on ambiguous pictures: on a collage where panels pop in one by one, two runs judged 6 of 43 suspects differently. Shot counts can differ by a few between runs; measured cuts never change.
- Fast camera moves are still checked with only first / middle / last frames. Check one-frame shots in the table.
- On a finished edit with music, sung lyrics and speech can land in one line, and cut points then fall inside the lyrics.
- Homophones survive ASR (采销 → 彩销); they appear as suspect words when the script or on-screen text shows the right spelling.
