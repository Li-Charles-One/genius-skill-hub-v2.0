---
name: genius-subtitle
description: "Genius 字幕：给一条成片做字幕并交付：台词来源可以是 genius-sound 声音工程（台词与译文）、视频的语音识别（豆包 ASR，按句切成一行一条），或现成的 SRT；中英等双语排版（默认中上英下、中文字号大），按 Netflix 规范检查每行字数、阅读速度、时长与间隔，中文标点规则（不用逗号句号、改空格），按镜头切点对齐出入点；输出 SRT、ASS，并烧录进画面（遇黑边放进黑边）。用户说「给这条视频加中英字幕」「把字幕烧进去」「这条 vlog 出个字幕文件」「把配好音的片子加上双语字幕」「这个 SRT 帮我检查一下有没有太长太快」「把英文字幕翻成中英双语」时使用。不要用于单纯语音转文字或会议纪要（用 genius-voice），不要用于花字、标题、动态文字包装，不要用于配音、音效、配乐或混音（用 genius-sound），不要用于视频内容总结（用 genius-omni）。"
metadata:
  version: "1.0.2"
---

# Genius Subtitle（字幕）

This skill exists to **put subtitles on a finished video**: get the text (a genius-sound project, ASR, or an SRT), translate, check against subtitle limits, render SRT and ASS, burn in. One folder per video, driven by `subs.json`; `scripts/subs.py` does the work, ASR goes through **genius-voice**, shots come from **genius-footage**. Rules, limits and sources: `references/rules.md`.

## Pick a source

| The user has | Command |
|---|---|
| A genius-sound project (lines and translations already written) | `init <project>/out/<title>_mix.mp4 --dir <project>`, then `from-sound <project>` |
| A video with speech and no text | `init <video>`, then `from-asr <dir> --language zh\|en` |
| An SRT (one language or bilingual) | `init <video>`, then `from-srt <dir> <file.srt>` |

Then translate into every `layout` language (`events[].text`), `check`, fix, `render`.

## Non-Negotiables

- Ask the layout before importing when the user has not said it: languages top to bottom, burned in or files only. Bilingual default: Chinese on top, larger.
- Translation is your work: write it into `subs.json`, keep names in their established form, and show the user the subtitle table before burning a long video.
- Run `check` before `render` and report what is still flagged; never claim lines fit or read in time without that output.
- ASR text is a draft: names and terms it mishears stay wrong until someone reads them.

## Run

```bash
python3 "<skill_dir>/scripts/subs.py" --check
python3 "<skill_dir>/scripts/subs.py" init <video> [--dir DIR] [--title T] [--layout zh,en]
python3 "<skill_dir>/scripts/subs.py" from-sound <dir> [--project P]
python3 "<skill_dir>/scripts/subs.py" from-asr <dir> [--language auto|zh|en]
python3 "<skill_dir>/scripts/subs.py" from-srt <dir> <file.srt> [--lang zh|en]
python3 "<skill_dir>/scripts/subs.py" check <dir>
python3 "<skill_dir>/scripts/subs.py" render <dir> [--no-burn] [--png]
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`; genius-voice for `from-asr`. Stdlib only, except burning when ffmpeg lacks the `subtitles` filter: then run `render` with a Python that has Pillow (a venv: `python3 -m venv .venv`, then `.venv/bin/pip install Pillow`; Windows `.venv\Scripts\pip`). `--check` reports which burn path is available.

## Workflow

1. `--check`, `init` (probes fps, frames, start time and the letterbox; default folder `<video>-subs/`, or the sound project with `--dir`).
2. Import from one source.
3. Translate: fill the missing layout languages in `events[].text`.
4. `check`; fix LINE / FAST / SHORT / GAP / MISSING (`references/rules.md`); check again.
5. `render`; grab a frame inside two or three events to check placement.

Inside a genius-sound project the files land in `<project>/out/`, where `deliver pack` picks them up; re-burn after every new mix (pack skips a burned video older than the mix).

## Report

The SRT, ASS and burned video paths, the burn path (libass or PNG overlay) and placement (letterbox bar or picture bottom), the `check` lines still flagged, and which text came from ASR unreviewed. Failures print `Error [CODE]: …`: `INPUT_NOT_FOUND` 3, `UNSUPPORTED_FORMAT` 4, `DEPENDENCY_MISSING` 5, `PROVIDER_ERROR` 6, `TIMEOUT` 7. Report the code and message as-is.

## Gotchas

- A mixed video's picture started at 0.046 s: SRT times from frame ÷ fps alone ran 46 ms early. `init` records the start and every time carries it; burned PNG overlays go by frame number.
- This machine's Homebrew ffmpeg had neither `drawtext` nor `subtitles`; burning went through Pillow PNG overlays (43 s at 1080p: 26 s).
- `from-srt` splits a bilingual SRT by script, line by line: any line with Chinese characters goes to `zh`. A single-language SRT that mixes scripts on one line needs `--lang`.
- ASR wrote 三千 as 3千; numbers and names in ASR text need a read.

## Resource Map

- `scripts/subs.py`: every command above.
- `references/rules.md`: sources, limits and their origin, Chinese text rules, timing, layout, outputs.
- `evals/evals.json`: trigger and behaviour checks.
- `agents/openai.yaml`: Codex/UI metadata.
