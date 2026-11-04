# Spot (定点): project, story, frames, cue sheet

The spotting session decides what sound goes where before anything is generated. Every module starts from here; a single-module request only needs `spot init` and a short checkpoint ①.

## Start

`sound.py spot init <clip> [--dir DIR] [--title T] [--language en|zh|…]` copies the clip to `<project>/src/`, probes fps and frames (the timeline comes from frames ÷ fps, not from the audio track), finds the letterbox and reports `original_sound`:

- `none`: a silent clip; every sound is new.
- `present`: the picture has its own sound. To keep it (only adding music, ambience or effects), add a bed `{"id": "production", "kind": "dialogue", "file": "src/clip.mp4"}`: it joins the dialogue predub and ducks the music. To replace it (a redub), leave it out.

Then run genius-footage on `<project>/src/clip.mp4` for shots, people and segments. `spot grid --shot` and `spot sheet` read the shot list from `src/clip.footage.json`.

## Checkpoint ① — story, tone, languages

Show the user what the picture says and ask only what changes the result:

| Ask | Why |
|---|---|
| Is this a known story (myth, film, novel)? Played straight or as comedy? | 2026-11-04: the first reading made the animals talk and played it for laughs; the user meant the Odyssey, played straight. |
| Dialogue language | The user switched to English after the Chinese script was approved; asking first saves a rewrite. |
| Which departments: dialogue, narration, foley, effects, ambience, music | A single-module request ("just a BGM") skips the rest. |
| Delivery spec (web, stream, ebu, tv24, netflix) and destination | `mix master --spec`, `deliver pack --dest`. |

Lead with the story reading: shot-backed beats (shot IDs), what each character does and the visual details that decide meaning (who grips what, who covers whose mouth, what is handed over). If a detail is ambiguous (an object the model calls an ice-cream cone), write sound that works either way and say so.

## Checkpoint ② — the script or spotting list

Dialogue: a table of `#`, shot, window (seconds), character, line, direction, on/off screen, plus syllables per window (`dialogue.md`). Other modules: a spotting list of what sound lands where (shot, seconds, sound, module). Offer one alternative for the line or sound that carries the twist. Generate nothing before the user confirms.

## Frame grids

`spot grid <project> --shot S012 [--crop W:H:X:Y] [--step 1] [--cols 10] [--motion]` tiles the shot's frames into `work/grid/<name>.jpg` and prints which frames each row holds. Grab one full frame first to find the crop.

- Dialogue: crop on the mouth or beak and read open / closed frames (`dialogue.md`).
- Foley: crop on the feet, hands or object and read the contact frame (`foley.md`). `--motion` adds the mean luma change per frame inside the crop: a sharp drop after a busy run is a candidate contact. It is a reading aid, not a detector: camera moves and transitions move the whole crop. Confirm every contact on the grid.
- Repeated frames print as `=`: the Odyssey clip (30 fps, AI-generated) repeated every 5th frame (24→30 fps pulldown). A sound cannot land on a repeated frame's "new" motion; use the next real frame.

## Cue sheet

`spot sheet <project>` writes `定点表.md`: every shot with its dialogue / narration and foley cues (by `at`, else by window), unplaced cue IDs, and every bed with its type, start, target and whether its file exists. Show it at checkpoint ② and after placement; `deliver pack` includes it.
