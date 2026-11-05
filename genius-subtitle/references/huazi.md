# 花字模式（huazi.py）

Designed captions (花字), name bars (人名条) and data callouts laid over a finished video. One folder per video, `<video>-huazi/`, driven by `huazi.json`. Templates are HTML/CSS; a headless Chromium browser captures every frame with alpha; ffmpeg packs one alpha MOV per item and burns a preview.

## Workflow

1. `huazi.py --check`: ffmpeg, a browser (Chrome / Edge / Chromium / Brave, or `HUAZI_BROWSER`), HEVC-alpha support, Source Han Sans SC.
2. Pick a style: `huazi.py templates` lists the built-in ones (t1–t5) and custom ones. Ask the user for the brand colour (6 hex digits) unless given; a template's `default_brand` is its reference look (t5 is meant for gold).
3. `huazi.py init <video> --template T --brand HEX`. With `<video>.overlays.json` next to the video (genius-footage overlay sheet) or `--overlays FILE`, every 花字 and 人名条 becomes an item with its frames, side and height; otherwise `items` is empty and you write them.
4. Edit `huazi.json` items (schema below). `init` only guesses: set `type` from the content (a parameter → `number`, a heading with points → `list`, …), mark emphasis with `{…}`, move `y` off faces and busy areas, and keep the text the user's (see rules).
5. `huazi.py preview <dir> --ids …` (3–6 items, one of each type and side) renders the items on real frames into `preview/preview_<template>.png`. Several templates at once: `--template t1-light-band,t3-bold-type`. Show the sheet; get the style confirmed before rendering everything.
6. `huazi.py render <dir>` (or `--ids` for some). Look at a frame of two or three MOVs before reporting.

## huazi.json

```json
{
 "template": "t1-light-band", "brand": "E1251B",
 "safe": {"x": 0.075, "top": 0.07}, "bottom_limit": 0.80,
 "items": [
  {"id": "H07", "type": "number", "align": "left", "y": 0.34, "in": 8940, "out": 9097, "preview_frame": 8932,
   "fields": {"kicker": "功率升级", "lines": ["加热功率从2500W", "提升至"], "number": {"value": "2600", "unit": "W"}}}
 ]
}
```

| Field | Meaning |
|---|---|
| `type` | `title` one line · `stack` two lines staggered · `number` lines + big number after the last line · `list` heading + `items` · `name` name bar |
| `align` | `left` / `right`: anchored to the side margin (`safe.x` of the width); `center`: centred |
| `y` | top edge as a share of the height; clamped so the item stays below `safe.top` and its bottom above `bottom_limit` (the subtitle zone) |
| `in` / `out` | first and last frame, inclusive (overlay sheet frames) |
| `preview_frame` | background frame for `preview`; use a clean frame of the same shot when the video already carries old 花字 |
| `fields.lines` | main lines; `{…}` marks emphasis (bigger / bolder / brand colour, by template); digits and Latin get the number font automatically |
| `fields.kicker` · `sub` · `items` · `en` · `ghost` | small label · subtitle line · bullet points · English line · outlined background word (templates that use it) |
| `fields.number` | `{"value": "2600", "unit": "W"}` for `number` |
| `fields.name` · `role` | for `name` |

## Rules

- Text comes from the user or the overlay sheet, verbatim. Splitting into lines and marking `{…}` is layout; rewording is not. `en`, `ghost` and any English are additions: add them only when the user agrees, and say what each one says.
- Fonts must be free for commercial use with the licence on file: Source Han Sans SC (system install, SIL OFL), Noto Serif SC = 思源宋体, Barlow, Rajdhani (all SIL OFL, in `assets/huazi/fonts/` with their OFL files). Do not reference system fonts such as PingFang, Songti or Microsoft YaHei in a template: they are not licensed for video use.
- Keep faces, product and the subtitle zone clear; check the preview for it.
- Text on bright footage needs a backing (band, panel, shadow); look at the preview on the brightest shot.

## Output

`out/<id>.mov` per item, full frame, transparent outside the caption, starting at the item's `in`; `out/<title>_huazi.mp4` burned preview (all rendered items over the video); `out/huazi.md` the list (id, text, in, out, file).

| `--format` | Codec | Alpha | Size (3 s, 720p) | Where |
|---|---|---|---|---|
| `hevc` (default on macOS) | HEVC with alpha (VideoToolbox), `hvc1` | **premultiplied**, tagged premultiplied | ≈1.4 MB | Final Cut, Premiere / Resolve on macOS, QuickTime |
| `prores` (default elsewhere) | ProRes 4444 | **straight**, tagged straight | ≈64 MB | every NLE |

Browser screenshots carry straight alpha. VideoToolbox tags HEVC alpha as premultiplied, so `render` premultiplies the frames before encoding; without that the tag and the pixels disagree and every glow and soft edge comes out too bright. Checked 2026-11-05 on H07 of 京东.mp4: the unpremultiplied HEVC decoded with RGB above alpha on 6107 of 6642 semi-transparent pixels; premultiplied, 33 (compression noise). The tag was read through AVFoundation (`AlphaChannelMode`). The burned preview overlays each MOV with the matching `alpha=` mode. If an editor shows dark or bright fringes, its clip setting for alpha interpretation disagrees with the table above.

## Templates

| id | Name | Look |
|---|---|---|
| `t1-light-band` | 光带科技 | gradient bold text with glow on a brand light band that fades at both ends; staggered lines with dot matrix; offset squares, ×, barcode dashes; orbit ellipse or HUD ring |
| `t2-cinema-serif` | 电影极简 | thin serif, wide tracking, [brackets], staggered lines, no backing; blur-in |
| `t3-bold-type` | 粗字排版 | no backing; bold italic with big/small contrast via `{…}`; brand sheen sweeping the line end; ▶ subtitle |
| `t4-glass-cube` | 玻璃方块 | light + heavy italic mix; slanted brand panels; rotating glass cubes, square particles, arc |
| `t5-black-gold` | 黑金质感 | metallic white-to-brand (gold) bold italic; outlined ghost of the first line; ◀◀ lines; gold light line with flare; reveal by light sweep |

Each is `assets/huazi/templates/<id>/`: `meta.json` (name, description, default brand, fonts, reference), `style.css`, optional `decorate.js`. Reference images the user gave were used for style only; shapes and layouts are original.

## Template contract (also for custom templates)

`assets/huazi/runtime.js` builds the same markup for every template, so a template is mostly CSS:

```text
.hz.type-<type>.align-<align>          (--dur, --out: seconds)
  .hz-deco.hz-back                     decorations behind (decorate.js fills it)
  .hz-ghost .hz-kicker                 when given
  .hz-line.hz-l1[.hz-last].hz-a > .hz-bar + .hz-t (+ .hz-num > .hz-v + .hz-u on the last line of a number)
  .hz-items > li.hz-a > .hz-bullet + span
  .hz-sub.hz-a > .hz-bullet + span     (name: .hz-l1 holds .hz-t.hz-n; .hz-sub holds the role)
  .hz-en.hz-a
  .hz-deco.hz-front                    decorations in front
inline: .hz-lat (digits / Latin), .hz-em ({…})
```

- Colours only through `rgb(var(--brand))`, `--brand-light`, `--brand-deep` (each "r,g,b"; light and deep are mixed from the brand by `huazi.py`). In SVG use `style="stroke:rgba(var(--brand),.6)"`, not presentation attributes.
- Motion only through CSS animations and SVG SMIL: `huazi.py` pauses all of them and sets the time for each frame (`window.hzSeek`), so no `setTimeout`, `requestAnimationFrame` loops or random values. `base.css` gives `.hz-a` an entrance (`--d` delay) and an exit at `--out`; a template may replace them. Loops (`infinite`) are fine.
- `decorate.js` defines `window.HZ_DECORATE(el, item, api)`; `api.rel(node)` gives a node's box inside the item, unaffected by entrance transforms; `api.svg(w, h, inner)` wraps SVG that may overflow.
- Design canvas is 1280×720 whatever the video size; the stage is scaled.

## Custom mode

When the user brings a reference image, a brand guide or asks for a look none of t1–t5 has:

1. Name what to take from the reference (type, backing, decorations, motion) and tell the user it is style only.
2. `huazi.py new-template <id> --from <closest template> --name <中文名>`; edit `style.css`, `decorate.js` and `meta.json` (`description`, `reference`, `default_brand`, `fonts`) under the contract.
3. `preview` with one item of every type the video uses, on the brightest and the busiest shot; fix overlaps, wrapping and readability; repeat until the user confirms.
4. Custom templates live next to the built-in ones in `assets/huazi/templates/` (`"custom": true`); a skill update that replaces the folder drops them, so keep a copy of the template folder with the project.
