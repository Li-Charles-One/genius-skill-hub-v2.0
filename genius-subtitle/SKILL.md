---
name: genius-subtitle
description: "Genius 字幕：给成片做字幕并交付。台词来自 genius-sound 声音工程、语音识别或现成 SRT；中英双语排版，按 Netflix 规范检查行长、阅读速度与时长，对齐镜头切点，输出 SRT/ASS 并烧录进画面。另有花字模式：做花字、人名条、数据标注，用内置模板或按参考图、品牌规范自定义，渲染成透明通道 MOV；可按 genius-footage 的花字表重做旧花字。用户说「给这条视频加中英字幕」「把字幕烧进去」「这个 SRT 帮我检查有没有太长太快」「给这条片子加花字和人名条」时使用。不要用于单纯语音转文字（用 genius-voice）、扒成片里现有花字的文字和时间（用 genius-footage）、配音配乐混音（用 genius-sound）、产品宣传片（用 video-shotcraft）、视频内容总结（用 genius-omni）。"
metadata:
  version: "1.2.1"
---

# Genius Subtitle（字幕）

This skill exists to **put subtitles on a finished video**: get the text (a genius-sound project, ASR, or an SRT), translate, check against subtitle limits, render SRT and ASS, burn in. One folder per video, driven by `subs.json`; `scripts/subs.py` does the work, ASR goes through **genius-voice**, shots come from **genius-footage**. Rules, limits and sources: `references/rules.md`.

**花字模式** (designed captions, name bars, data callouts; not dialogue subtitles) is `scripts/huazi.py`, one folder per video driven by `huazi.json`; workflow, schema, templates, alpha and custom templates: `references/huazi.md`.

## Pick a mode

| The user wants | Mode |
|---|---|
| Dialogue / narration as subtitles (SRT, ASS, burned) | 字幕: the source table below |
| 花字, 人名条, titles or data callouts on a video; redo old 花字 from an overlay sheet; a new 花字 template from a reference | 花字: `huazi.py`, `references/huazi.md` |

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
- 花字: get the style confirmed on a `preview` sheet before rendering all items; keep the user's text verbatim (layout and `{…}` emphasis only), add English or decorative words only with their consent, and use only the commercially free fonts listed in `references/huazi.md`.

## Run

```bash
python3 "<skill_dir>/scripts/subs.py" --check
python3 "<skill_dir>/scripts/subs.py" init <video> [--dir DIR] [--title T] [--layout zh,en]
python3 "<skill_dir>/scripts/subs.py" from-sound <dir> [--project P]
python3 "<skill_dir>/scripts/subs.py" from-asr <dir> [--language auto|zh|en]
python3 "<skill_dir>/scripts/subs.py" from-srt <dir> <file.srt> [--lang zh|en]
python3 "<skill_dir>/scripts/subs.py" check <dir>
python3 "<skill_dir>/scripts/subs.py" render <dir> [--no-burn] [--png]

python3 "<skill_dir>/scripts/huazi.py" --check
python3 "<skill_dir>/scripts/huazi.py" templates
python3 "<skill_dir>/scripts/huazi.py" init <video> [--overlays X.overlays.json] [--template T] [--brand HEX]
python3 "<skill_dir>/scripts/huazi.py" preview <dir> [--ids H03,N3] [--template T1,T2] [--brand HEX]
python3 "<skill_dir>/scripts/huazi.py" render <dir> [--ids …] [--format hevc|prores] [--no-burn]
python3 "<skill_dir>/scripts/huazi.py" new-template <id> [--from T] [--name 名称]
```

`<skill_dir>` is this skill folder; on Windows use `python`. Needs `ffmpeg` / `ffprobe`; genius-voice for `from-asr`. Stdlib only, except burning when ffmpeg lacks the `subtitles` filter: then run `render` with a Python that has Pillow (a venv: `python3 -m venv .venv`, then `.venv/bin/pip install Pillow`; Windows `.venv\Scripts\pip`). `--check` reports which burn path is available. `huazi.py` also needs a Chromium browser (Chrome, Edge, Chromium or Brave; `HUAZI_BROWSER` to point at one) and Source Han Sans SC installed; HEVC with alpha needs macOS (VideoToolbox).

## Workflow

1. `--check`, `init` (probes fps, frames, start time and the letterbox; default folder `<video>-subs/`, or the sound project with `--dir`).
2. Import from one source.
3. Translate: fill the missing layout languages in `events[].text`.
4. `check`; fix LINE / FAST / SHORT / GAP / MISSING (`references/rules.md`); check again.
5. `render`; grab a frame inside two or three events to check placement.

Inside a genius-sound project the files land in `<project>/out/`, where `deliver pack` picks them up; re-burn after every new mix (pack skips a burned video older than the mix).

## Report

The SRT, ASS and burned video paths, the burn path (libass or PNG overlay) and placement (letterbox bar or picture bottom), the `check` lines still flagged, and which text came from ASR unreviewed. Failures print `Error [CODE]: …`: `INPUT_NOT_FOUND` 3, `UNSUPPORTED_FORMAT` 4, `DEPENDENCY_MISSING` 5, `PROVIDER_ERROR` 6, `TIMEOUT` 7. Report the code and message as-is.

花字: the preview sheet path(s), the template and brand colour, the MOV format and its alpha mode (HEVC premultiplied / ProRes straight), the burned preview and `out/huazi.md` paths, and any item changed from the source text or left unchecked.

## Gotchas

- A mixed video's picture started at 0.046 s: SRT times from frame ÷ fps alone ran 46 ms early. `init` records the start and every time carries it; burned PNG overlays go by frame number.
- This machine's Homebrew ffmpeg had neither `drawtext` nor `subtitles`; burning went through Pillow PNG overlays (43 s at 1080p: 26 s).
- `from-srt` splits a bilingual SRT by script, line by line: any line with Chinese characters goes to `zh`. A single-language SRT that mixes scripts on one line needs `--lang`.
- ASR wrote 三千 as 3千; numbers and names in ASR text need a read.
- 花字 HEVC alpha: VideoToolbox tags it premultiplied while browser frames are straight; unpremultiplied files came out with too-bright glows (6107 of 6642 soft pixels off on 京东.mp4 H07). `render` premultiplies first. ffmpeg's libx265 here could not encode alpha at all.
- 花字 on a finished edit: the burned preview stacks the new 花字 over the old ones; the MOVs are for the clean timeline. Set `preview_frame` to a clean frame for style sheets.
- A negative margin cancelling trailing letter-spacing made Chrome wrap the last character of every serif line; `base.css` forbids wrapping, lines break only where `fields.lines` does.
- Capture ran about 14 frames/s at 720p (H03: 150 frames in 10.5 s); re-encoding the 7-min burned preview took about 2.5 min.
- Orbitron's A has no crossbar: an outlined MIDEA read as MIDER. Check Latin display fonts on the actual words.
- `quick_validate.py` wants every asset path named in this file: a new custom template's files must be added to the Resource Map.

## Resource Map

- `scripts/subs.py`: every command above.
- `references/rules.md`: sources, limits and their origin, Chinese text rules, timing, layout, outputs.
- `scripts/huazi.py`: 花字模式, every `huazi.py` command above (DevTools capture, alpha encode, burn).
- `references/huazi.md`: 花字 workflow, `huazi.json` schema, rules, alpha formats, templates, template contract, custom mode.
- `assets/huazi/runtime.js` (layout, seek), `assets/huazi/base.css` (canvas, fonts, entrance and exit).
- Templates: `assets/huazi/templates/t1-light-band/meta.json`, `assets/huazi/templates/t1-light-band/style.css`, `assets/huazi/templates/t1-light-band/decorate.js`; `assets/huazi/templates/t2-cinema-serif/meta.json`, `assets/huazi/templates/t2-cinema-serif/style.css`; `assets/huazi/templates/t3-bold-type/meta.json`, `assets/huazi/templates/t3-bold-type/style.css`; `assets/huazi/templates/t4-glass-cube/meta.json`, `assets/huazi/templates/t4-glass-cube/style.css`, `assets/huazi/templates/t4-glass-cube/decorate.js`; `assets/huazi/templates/t5-black-gold/meta.json`, `assets/huazi/templates/t5-black-gold/style.css`, `assets/huazi/templates/t5-black-gold/decorate.js`; `assets/huazi/templates/t6-camping/meta.json`, `assets/huazi/templates/t6-camping/style.css`, `assets/huazi/templates/t6-camping/decorate.js`; `assets/huazi/templates/t7-collage-paper/meta.json`, `assets/huazi/templates/t7-collage-paper/style.css`, `assets/huazi/templates/t7-collage-paper/decorate.js`.
- Fonts (SIL OFL, licence beside each): `assets/huazi/fonts/BarlowCondensed-SemiBold.ttf`, `assets/huazi/fonts/OFL-Barlow.txt`, `assets/huazi/fonts/Rajdhani-Bold.ttf`, `assets/huazi/fonts/Rajdhani-SemiBold.ttf`, `assets/huazi/fonts/OFL-Rajdhani.txt`, `assets/huazi/fonts/NotoSerifSC.ttf`, `assets/huazi/fonts/OFL-NotoSerifSC.txt`.
- `evals/evals.json`: trigger and behaviour checks.
- `agents/openai.yaml`: Codex/UI metadata.
