---
name: genius-sound
description: "Genius 声音后期：给一段视频做电影级声音后期，七个模块可单独调用也可整片串联：定点、对白&旁白（对口型配音）、拟音、音效&环境、配乐、混录&母带（按网络、平台、广电、Netflix 规格出母带，导出 DME 分轨与 M&E 国际声轨）、交付打包。用户说「给这段无声片配台词、配音、音效和配乐」「把这段片子重新配成英文」「只给这段视频配个 BGM」「给这段加环境声和脚步声」「这几轨按广电标准出母带」「导出 DME 分轨和国际声轨」「把声音工程打包」时使用。不要用于：字幕制作、翻译或烧录（用 genius-subtitle）；单句朗读、纯文本旁白、单独生成一个音效或一首歌、语音转文字（用 genius-voice）；视频内容总结（用 genius-omni）；素材说明书或镜头表（用 genius-footage）；产品宣传片（用 video-shotcraft）；剪辑画面。"
metadata:
  version: "2.0.3"
---

# Genius Sound（声音后期）

This skill exists to give **a clip a film-grade soundtrack, one department at a time or end to end**: spotting, dialogue and narration, foley, effects and ambience, music, re-recording mix and master, delivery. One project folder per clip, driven by `sound.json` (schema: `references/sound-json.md`; genius-dub `dub.json` projects load too). Generation and ASR go through **genius-voice**; shots come from **genius-footage**; `scripts/sound.py` does the rest. Subtitles belong to **genius-subtitle** (`from-sound` reads this project).

## Pick a module

| The user wants | Module | Commands | Read |
|---|---|---|---|
| Read the picture, agree story and tone, mouth / action frames, cue sheet | spot 定点 | `spot init`, `spot grid`, `spot sheet` | `references/spot.md` |
| Lines fitted to lips, character voices, efforts, narration | dialogue 对白&旁白 | `dialogue gen`, `dialogue place`, `dialogue check takes\|stem` | `references/dialogue.md` |
| Footsteps, cloth, props, animal calls on the action | foley 拟音 | `foley gen`, `foley place` | `references/foley.md` |
| Hard and design effects, ambience beds | sfx 音效&环境 | `sfx gen`, `env` | `references/sfx-ambience.md` |
| Score, BGM, source music | music 配乐 | `music gen`, `env` | `references/music.md` |
| Mix, master to a delivery spec, DME stems, M&E, intelligibility | mix 混录&母带 | `mix master [--spec]`, `mix check` | `references/mix-master.md` |
| Package the project with a README | deliver 交付 | `deliver pack` | this file |

A single module still works on a project: `spot init` (cheap), a one-question checkpoint ①, that module, then `mix master`. "Only a BGM": write a `music` bed, `music gen`, `mix master`; if `spot init` reports `original_sound: present`, add the `production` dialogue bed so the picture's own sound is kept and ducks the music. "Master these stems to TV spec": `spot init` on the picture, beds with `file` and `kind`, `mix master --spec tv24`.

## Non-Negotiables

- Two checkpoints before any paid generation: **① story, tone, languages, departments and spec**, **② the script** (every line with its shot and frame window) or, for other departments, the spotting list. Questions: `references/spot.md`.
- Read the picture with genius-footage before interpreting it. Follow a recognisable source story; animals make animal sounds unless the user asks them to talk.
- Every frame, second and level comes from measurement: shots from the footage brief, mouth and contact frames from `spot grid`, sync from `dialogue check stem`, spec compliance from the `mix master` result, intelligibility from `mix check`. Never claim sync, audibility or compliance without that output.
- ASR checks words and times only. Timbre, acting, foley, effects and music taste are unverified until the user listens: say so in the report.

## Run

```bash
python3 "<skill_dir>/scripts/sound.py" --check
python3 "<skill_dir>/scripts/sound.py" spot init <clip> [--dir DIR] [--title T] [--language en|zh|...]
python3 "<skill_dir>/scripts/sound.py" spot grid <project> --shot S012 [--crop W:H:X:Y] [--step 1] [--cols 10] [--motion]
python3 "<skill_dir>/scripts/sound.py" spot sheet <project>
python3 "<skill_dir>/scripts/sound.py" dialogue gen|foley gen|sfx gen|music gen <project> [--only IDS] [--dry-run] [--force]
python3 "<skill_dir>/scripts/sound.py" dialogue place <project>
python3 "<skill_dir>/scripts/sound.py" dialogue check <project> takes|stem
python3 "<skill_dir>/scripts/sound.py" foley place <project>
python3 "<skill_dir>/scripts/sound.py" mix master <project> [--spec web|stream|ebu|tv24|netflix]
python3 "<skill_dir>/scripts/sound.py" mix check <project>
python3 "<skill_dir>/scripts/sound.py" deliver pack <project> [--dest DIR]
python3 "<skill_dir>/scripts/sound.py" env <audio> [--window 0.5]
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe` and the genius-voice skill (keys in its `scripts/.env`); genius-footage for the brief. Both are found next to this skill or in the usual skill folders; `GENIUS_VOICE_DIR` / `GENIUS_FOOTAGE_DIR` point elsewhere. Stdlib only.

## Full pipeline

1. `--check`, `spot init`, genius-footage on `src/clip.mp4`, story reading → **checkpoint ①**.
2. `spot grid` on each speaking or acting shot; windows → script and spotting list; `spot sheet` → **checkpoint ②**.
3. Dialogue: mark one `anchor` per character, `dialogue gen --dry-run`, `dialogue gen`, `dialogue check takes`, retakes under a new `take`; set `at`, `dialogue place`, `dialogue check stem`, nudge.
4. Foley: contact frames, cues, `foley gen`, slices, `at`.
5. Effects, ambience, music: bed prompts, `sfx gen`, `music gen`, `env` each bed against what you asked for; `trim` / `mutes` for stray sounds.
6. `mix master --spec …` → `mix check`; fix MASKED lines and master again.
7. Add deviations to `notes`; `deliver pack --dest <where the user wants it>`.

Post a one-line status at each stage; generation runs take minutes. Run Seed Audio jobs one at a time; long batches go in the background with a completion notice instead of polling.

## Deliver

`deliver pack` builds `<title>_源文件/` and a zip: the mixed video, the original clip, scripts and cue sheet, `04_分轨/DME` (master, D, M, E, ME at 48 kHz 24-bit) and `04_分轨/素材轨` (dialogue, foley and every bed), generated takes split into used / unused, the project file, a copy of the scripts, check records and `文件说明.md`. Subtitle files and burned videos that genius-subtitle wrote into `out/` are carried along; a burned video older than the current mix is skipped.

## Report

The mixed video path, the spec with measured loudness and true peak and PASS / FAIL as printed by `mix master`, the `dialogue check stem` and `mix check` lines that are not OK, the package path and file count, the `notes`, and what still needs the user's ears. Failures print `Error [CODE]: …`: `INPUT_NOT_FOUND` 3, `UNSUPPORTED_FORMAT` 4, `DEPENDENCY_MISSING` 5, `PROVIDER_ERROR` 6, `TIMEOUT` 7. Report the code and message as-is.

## Gotchas

- Mixing clips that each start with an `adelay` shifted a whole dialogue stem earlier by the first clip's delay (2.75s, 2026-11-04). Placement and predub anchor every mix with a full-length silent input; keep that if you edit them.
- The Odyssey clip's picture starts at 0.066 s. Muxing the master from zero with `-shortest` put the sound 46 ms ahead of the picture and cut the last 3 frames (genius-dub did this too); `mix master` now starts the sound at the picture's start time and keeps every frame.
- A silent clip's audio track can be longer than the picture (43.467s vs 43.4s), and its video stream can start late (start_time 0.066s): frame numbers from pts came out one frame late. The timeline comes from frames ÷ fps; `spot grid` counts frames from the selection.
- The AI clip repeated every 5th frame (24→30 fps pulldown); motion reads 0 there. `spot grid --motion` prints them as `=`.
- The static-gain master keeps dynamics: a whisper sat 5.7 dB lower than in genius-dub's dynamic loudnorm mix at the same integrated loudness, with the same line-to-bed ratio. ffmpeg's `alimiter` auto-levels and delays by its lookahead unless `level=false:latency=true`; the master sets both, and D + M + E then match the master to a −70 dB mean residual.
- The craft lessons from the same runs live in the module that applies them: story reading in `references/spot.md`; one take per line, stage whispers and misheard whispers in `references/dialogue.md`; bed levels and stray SFX in `references/sfx-ambience.md`; whole-file `mix check` misses in `references/mix-master.md`.

## Resource Map

- `scripts/sound.py`: CLI, module routing, `--check`, `env`.
- `scripts/core.py`: project file, shots, generation and ASR bridges to genius-voice, placement, loudness.
- `scripts/spot.py`: `spot init`, `spot grid`, `spot sheet`.
- `scripts/dialogue.py`: dialogue placement and ASR checks.
- `scripts/mix.py`: predub, ducking, delivery specs, master, DME and M&E export, `mix check`.
- `scripts/deliver.py`: `deliver pack` and the package README.
- `references/spot.md`: project start, checkpoints, frame grids, cue sheet.
- `references/dialogue.md`: mouth windows, budgets, writing, voice takes, narration, FX presets, placement.
- `references/foley.md`: contact frames, foley takes and slicing, placement.
- `references/sfx-ambience.md`: effect and ambience beds, bed checks, levels.
- `references/music.md`: score prompts, measured behaviour, source music, ducking.
- `references/mix-master.md`: predubs, master chain, delivery specs, stems, M&E, intelligibility fixes.
- `references/sound-json.md`: project file schema.
- `evals/evals.json`: trigger and behaviour checks.
- `agents/openai.yaml`: Codex/UI metadata.
