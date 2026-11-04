# Subtitles

## Layout (bilingual, film-release style)

- `subtitles.layout` lists languages top to bottom: `["zh", "en"]` puts Chinese on top.
- Top line 4.26% of picture height (46 px at 1080), bottom line 2.78% (30 px). White, thin dark outline.
- Letterboxed picture: subtitles sit in the bottom bar when it is taller than the two lines (128 px bar at 1080 holds both); otherwise 6% above the bottom of the frame.
- Fonts by OS: Chinese — Source Han Sans SC Medium, PingFang SC, Microsoft YaHei, Noto Sans CJK SC; Latin — Helvetica Neue, Arial, DejaVu Sans. `--check` shows the ones found.

## Chinese text rules

- No full stop at the end of a line; commas, 顿号 and semicolons become a space: `来，独眼巨人……尝尝这个` → `来 独眼巨人……尝尝这个` (`subs` applies this to `zh`).
- Keep `？` `！` `……`.
- Use the established translation of names and key terms (Odysseus 奥德修斯, Polyphemus 波吕斐摩斯, "Nobody" 无人).
- The English line keeps its own punctuation.

## Timing

Derived when a cue has no `sub`:

- In: the window start (on-screen speech) or `at`.
- Out: at least 0.8 s after in, and 0.3 s after the window end.
- A shot change within 8 frames of the in point moves the in point onto it; a shot change within 12 frames after (or 8 before) the out point ends the subtitle on the frame before it, unless that would drop below 0.8 s.
- Consecutive subtitles keep a 2-frame gap.
- One take with two sentences: `split_subs`.

On the Odyssey clip the derived events landed within 5 frames of the hand-tuned ones.

Non-verbal sounds (animals, roars, gasps, laughs) are not subtitled unless the user asks for SDH-style captions.

## Outputs and burn-in

- `out/<title>.srt`: one line per language in each event, top language first.
- `out/<title>.ass`: the same layout with fonts and sizes.
- `out/<title>_dub_subs.mp4`: burned with libass when ffmpeg has the `subtitles` filter, else with Pillow PNG overlays (`--png` forces it). Re-encodes video (x264 CRF 16), copies audio.

Check placement with a frame grab inside two or three events, e.g. `ffmpeg -ss 36.6 -i out/<title>_dub_subs.mp4 -frames:v 1 check.jpg`.
