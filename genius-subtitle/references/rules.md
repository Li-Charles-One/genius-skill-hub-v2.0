# Subtitle rules

## Sources

| Command | Text from | Timing |
|---|---|---|
| `from-sound <dir> [--project P]` | a genius-sound project (`sound.json`, or genius-dub `dub.json`): every voice / narration cue with a `line`, plus its `sub_text` translations | `sub` / `split_subs` frames as written; otherwise derived from the mouth `window` (or `at`) with the timing rules below |
| `from-asr <dir> [--language auto\|zh\|en]` | genius-voice ASR of the video | utterances cut at clause punctuation into pieces that fit one line, timed from the word timestamps, then the timing rules |
| `from-srt <dir> <file> [--lang L]` | an existing SRT; a bilingual SRT is split by language line by line | kept as written; only the gap rule is applied |

ASR assumes the audio and picture streams start together (true for genius-sound mixes). Each import replaces `events`; translate by writing the other layout languages into `events[].text`, then run `check`.

## Limits (`check`)

| | Characters per line | Reading speed (adult) | Source |
|---|---|---|---|
| Simplified Chinese | 16 | 9 characters / s | Netflix Simplified Chinese Timed Text Style Guide (checked 2026-11-04) |
| English | 42 | 20 characters / s | 42: Netflix subtitle template; 20 cps: secondary sources quoting the Netflix English guide, not checked against it |

Duration 5/6 s to 7 s per event; at least 2 empty frames between events. Spaces do not count in Chinese. Other languages get only the duration, gap and missing-text checks.

Fixes for flags: LINE or FAST — condense the translation, or split the event in two at a pause (two events with their own frames); SHORT — extend into the gap after it; GAP — end the earlier event sooner; MISSING — write the translation.

## Chinese text (applied to `zh` at check and render)

- No commas or full stops: each becomes one space. `来，独眼巨人……尝尝这个。` → `来 独眼巨人……尝尝这个`.
- Enumeration commas (、) stay inside a list, never at the end of a line.
- Ellipsis is U+2026 (`…`, or `……`); ASCII `...` is converted.
- Question and exclamation marks stay.
- Names and key terms use their established translation (Odysseus 奥德修斯, Polyphemus 波吕斐摩斯, "Nobody" 无人).
- Other languages keep their own punctuation.

Non-verbal sounds (animals, roars, gasps, laughs) are not subtitled unless the user asks for SDH captions.

## Timing (derived events)

- In: the speech start. A shot change within 0.27 s (8 frames at 30 fps) either side moves the in point onto it.
- Out: 0.3 s after the speech ends and at least 5/6 s after in. A shot change within 0.4 s before or 0.27 s after the out point ends the event on the frame before it, unless that would drop it below 5/6 s.
- Shots come from a genius-footage brief next to the video or in the sound project (`src/clip.footage.json`), else genius-footage `measure.py`, else ffmpeg scene cuts (cached in `work/cuts.json`).

On the Odyssey clip the derived events matched the hand-tuned genius-dub events frame for frame (9 of 9).

## Layout (render)

- `layout` lists languages top to bottom: `zh,en` puts Chinese on top.
- Top line 4.26% of picture height (46 px at 1080), lower lines 2.78% (30 px). White, thin dark outline. One line per language; long lines are not wrapped (`check` flags them).
- Letterboxed picture: subtitles sit in the bottom bar when it holds all lines (a 128 px bar at 1080 holds two); otherwise 6% above the bottom of the frame.
- Fonts: Chinese — Source Han Sans SC Medium, PingFang SC, Microsoft YaHei, Noto Sans CJK SC; Latin — Helvetica Neue, Arial, DejaVu Sans. `--check` shows the ones found.

## Outputs

- `out/<title>.srt`: one line per language in each event, top language first.
- `out/<title>.ass`: the same layout with fonts and sizes.
- `out/<video>_subs.mp4`: burned with libass when ffmpeg has the `subtitles` filter, else with Pillow PNG overlays placed by frame number (`--png` forces it). Re-encodes the video (x264 CRF 16), copies the audio.

SRT and ASS times are frame ÷ fps plus the video stream's start time (`info.start`): a picture that starts at 0.046 s shows frame 85 at 2.879 s, not 2.833 s.

Check placement with a frame grab inside two or three events: `ffmpeg -i out/<video>_subs.mp4 -vf "select='eq(n,1000)'" -frames:v 1 check.jpg`.
