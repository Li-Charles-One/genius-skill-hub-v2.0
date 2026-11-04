# Sound effects & ambience (音效&环境)

Hard effects (impacts, falls, fire), design effects (whooshes, rumbles, the supernatural) and ambience (backgrounds, room tone). They are generated as beds: one Seed Audio request per bed, ≤ 120 s, ≤ 3000 characters, placed at `at`. Both go into the effects predub (E).

## Beds

| Bed | `kind` | Prompt opening | Notes |
|---|---|---|---|
| SFX segment | `sfx` | "Cinematic sound effects only, no music, no voices, no speech, no ambience bed." then one `[a s:b s]` line per event | Split the film into segments of ~10–20s at shot boundaries; `at` = segment start. |
| Ambience | `amb` | `[0s:<duration>s] Continuous ambience …. No music, no voices, no speech.` | One bed per location; a scene change gets a new bed starting at the cut. |

`sfx gen <project> [--only IDS] [--dry-run] [--force]` generates every `sfx` and `amb` bed that has a `prompt` and no file yet.

## Checking a bed

`sound.py env beds/<id>.wav --window 0.5` prints the loudness per window. Compare loud windows with the events you asked for.

- One SFX segment came back with an unrequested loud sound under the closing shot (37.4–40s); `trim` removed it.
- An effect that sits under a line (a giant's sniff under "Who is there?") gets a `mutes` window `[start, end, gain]` in bed time after trim.
- Note every trim and mute in `notes`.

## Levels

Default targets (the bed's own integrated loudness before the master gain): `sfx` −30 LUFS, `amb` −39 LUFS; set `lufs` per bed. Measured: beds at −27 / −26 LUFS buried the whispers and the giant (ASR heard 2 of 10 lines); −30 / −39 heard all.

## External effects

A bed with `file` (any audio, relative to the project or absolute) and `kind: "sfx"` or `"amb"` is mixed like a generated one and never regenerated.
