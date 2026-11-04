---
name: genius-dub
description: "Genius 配音：给一段无声或需要重配的视频片段做整套声音并交付：看懂剧情、按口型写台词、角色配音（豆包 Seed Audio 逐句生成、逐帧对口型）、动物声与音效、环境声、BGM、混音（对白避让、响度）、中英双语字幕（中上英下，可烧录进画面）、分轨与源文件打包附文件说明。用户说「给这段无声电影设计台词、配音、配音效和 BGM」「把这段片子重新配成英文」「给配好的片子加中英字幕烧进去」「把配音工程打包、写个文件说明」时使用。不要用于单句朗读、旁白，或只生成一个音效、一首歌（用 genius-voice），不要用于语音转文字（用 genius-voice），不要用于视频内容总结（用 genius-omni），不要用于给素材出说明书或镜头表（用 genius-footage），不要用于成片交付前质检（用 genius-video-qc），不要用于产品宣传片（用 video-shotcraft），不要用于剪辑画面。"
metadata:
  version: "1.0.0"
---

# Genius Dub（配音）

This skill exists to give **one clip a complete new soundtrack**: lines fitted to the lips, animal and foley sounds, ambience, BGM, a mix, bilingual subtitles and a packaged project. One project folder per clip, driven by one file, `dub.json` (schema: `references/dub-json.md`). Generation and ASR go through **genius-voice**; shots come from **genius-footage**; `scripts/dub.py` does everything else.

## Non-Negotiables

- Two checkpoints with the user before any paid generation: **① story, tone and languages** (dialogue language, subtitle layout), **② the script** (every line with its shot and frame window). Questions and order: `references/workflow.md`.
- Read the picture with genius-footage before interpreting it. Follow a recognisable source story; animals make animal sounds unless the user asks them to talk.
- Every frame and second comes from measurement: shots from the footage brief, mouth windows from `dub.py lipgrid`, placement from `dub.py check stem`, intelligibility from `dub.py check final`. Never claim sync or audibility without that output.
- ASR checks words and times only. Timbre, acting, sound effects and music taste are unverified until the user listens: say so in the report.

## Run

```bash
python3 "<skill_dir>/scripts/dub.py" --check
python3 "<skill_dir>/scripts/dub.py" init <clip> [--dir DIR] [--title T] [--language en|zh|...]
python3 "<skill_dir>/scripts/dub.py" lipgrid <project> --shot S012 [--crop W:H:X:Y] [--step 1] [--cols 10]
python3 "<skill_dir>/scripts/dub.py" gen <project> [--only IDS] [--beds] [--dry-run] [--force]
python3 "<skill_dir>/scripts/dub.py" check <project> takes|stem|final
python3 "<skill_dir>/scripts/dub.py" place <project>
python3 "<skill_dir>/scripts/dub.py" mix <project>
python3 "<skill_dir>/scripts/dub.py" subs <project> [--no-burn] [--png]
python3 "<skill_dir>/scripts/dub.py" pack <project> [--dest DIR]
python3 "<skill_dir>/scripts/dub.py" env <audio> [--window 0.5]
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe` and the genius-voice skill (keys in its `scripts/.env`); genius-footage for the brief. Stdlib only, except burning subtitles when ffmpeg lacks the `subtitles` filter: then run `subs` with a Python that has Pillow (a venv: `python3 -m venv .venv`, then `.venv/bin/pip install Pillow`; Windows `.venv\Scripts\pip`). `--check` reports which burn path is available.

## Workflow

1. `--check`, then `init` (copies the clip to `<project>/src/`, probes fps/frames, finds the letterbox).
2. genius-footage `footage.py <project>/src/clip.mp4` → shots, people, segments. Present the story reading → **checkpoint ①**.
3. For each shot with a visible mouth or beak: `lipgrid --shot` with a crop on the mouth; read open/close frames into windows (`references/lipsync-and-script.md`).
4. Write `characters` and `cues` (lines sized to the windows, off-screen lines where no mouth shows) and a script table → **checkpoint ②**.
5. Mark one `anchor` line per character; `gen --dry-run`, then `gen`; `check takes`; retake failures under a new `take` name.
6. Set `at` per cue; `place`; `check stem`; nudge flagged cues; repeat.
7. Write bed prompts (SFX segments, ambience, BGM); `gen --beds`; `env` each bed against the cue times you asked for; add `trim` / `mutes` for stray sounds (`references/sound-and-mix.md`).
8. `mix` → `check final`. MASKED lines: raise them or mute the bed under them, then mix again.
9. `subs` (`references/subtitles.md`); grab a frame inside two or three subtitles to check placement.
10. Add deviations to `notes`; `pack --dest <where the user wants it>`.

Post a one-line status at each stage; generation runs take minutes.

## Report

The final video paths (dubbed, subtitled), loudness and true peak as printed by `mix`, the `check stem` and `check final` lines that are not OK, the package path and file count, the `notes`, and what still needs the user's ears. Failures print `Error [CODE]: …`: `INPUT_NOT_FOUND` 3, `UNSUPPORTED_FORMAT` 4, `DEPENDENCY_MISSING` 5, `PROVIDER_ERROR` 6, `TIMEOUT` 7. Report the code and message as-is.

## Gotchas

- Mixing clips that each start with an `adelay` shifted a whole dialogue stem earlier by the first clip's delay (2.75s, 2026-11-04). `place` and `mix` anchor every mix with a full-length silent input; keep that if you edit them.
- A silent clip's audio track can be longer than the picture (43.467s vs 43.4s). The timeline comes from frames / fps.
- One-take timeline generation drifted 0.2–0.4s per line and added words; per-line takes placed locally landed every lip-synced line within 0.1s.
- Whispers dropped words ("Easy…" missing, "Grip" lost) until the prompt said "clear, audible stage whisper" and the window was ~1.5× the spoken length.
- ASR mishears whispers and pitched voices (Grip the wool → Rip the wall, Out cold → Alcohol). `check final` labels that MISHEARD, not MASKED; compare with `check stem` and listen.
- Beds at −27/−26 LUFS buried the dialogue: ASR found 2 of 10 lines. At −32/−30 with dialogue compressed and +5 dB, all 10. A giant's sniff SFX sat on "Who is there?" and hid it until muted under the line.
- An SFX segment returned a loud sound that was not in its prompt (37.4–40s, under the closing shot). `env` shows it; trim or mute.
- First story reading was a comedy with talking animals; the user meant the Odyssey played straight. Checkpoint ① exists for this.
- This machine's Homebrew ffmpeg had neither `drawtext` nor `subtitles`; burning went through Pillow PNG overlays.

## Resource Map

- `scripts/dub.py`: every subcommand above.
- `references/workflow.md`: checkpoints, questions, stage order, failure handling.
- `references/dub-json.md`: project file schema.
- `references/lipsync-and-script.md`: reading mouth windows, syllable budgets, writing and placing lines.
- `references/sound-and-mix.md`: Seed Audio prompt templates, voice consistency, bed checks, FX presets, mix targets.
- `references/subtitles.md`: bilingual layout, Chinese subtitle rules, timing and snapping, burn-in.
- `evals/evals.json`: trigger and behaviour checks.
- `agents/openai.yaml`: Codex/UI metadata.
