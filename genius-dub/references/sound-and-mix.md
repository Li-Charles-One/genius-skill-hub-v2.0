# Prompts, voice consistency, beds, mix

All generation is genius-voice `gen` (Seed Audio 1.0): one request per take or bed, ≤ 120 s, ≤ 3000 characters. `dub.py gen --dry-run` prints every prompt first.

## Voice takes

- One take per line. A whole-scene timeline in one request drifted 0.2–0.4s per line and added words; per-line takes placed locally hit the lips.
- **Anchor**: the character's longest, most typical line, generated from the full `voice` description. Every later line sends the anchor as `--ref` and starts "In the exact voice of @音频1, …". `gen` orders anchors first and records `ref`.
- Built prompt: `[0.1s:<gen_len>s] <voice or "In the exact voice of @音频1, <name>"> <direction> in <language>: "<line>" Only the clean dry voice, close microphone, no music, no ambience, no reverb.`
- Whisper: write "a clear, audible stage whisper" and give `gen_len` ≥ 1.5 × the spoken length. "barely audible" lost words.
- Short shouts that must fill a long mouth window: ask for the stretch ("stretching the first syllable a little: \"Noo-body!\"").
- Non-verbal (roar, growl, gasp, chuckle): a `prompt` with "No words", in the character's `@音频1` voice so it matches.
- Output is quiet (peaks around −32 dBFS); `place` normalises each slice to its `peak`.

## Animal and foley takes

Generate a short run of calls ("quack, quack-quack"), then slice one call per opening with `in`/`out`. Reuse slices across shots.

## Beds

| Bed | Prompt opening | Notes |
|---|---|---|
| SFX segment | "Cinematic sound effects only, no music, no voices, no speech, no ambience bed." then one `[a s:b s]` line per event | Split the film into segments of ~10–20s at shot boundaries; `at` = segment start. |
| Ambience | `[0s:<duration>s] Continuous ambience …. No music, no voices, no speech.` | One bed, full length. |
| BGM | "Instrumental film score only, no vocals, no lyrics, no sound effects." then sections by story beat | Measured: the build, the quiet drop and the swell landed; the requested action section collapsed to a 2s peak. |

After generation, `dub.py env beds/<id>.wav --window 0.5` and compare loud windows with the cues you asked for. One SFX segment came back with an unrequested loud sound under the closing shot; `trim` removed it. SFX that sits under a line (a giant's sniff under "Who is there?") gets a `mutes` window.

## FX presets (`characters.*.fx`)

| Preset | Chain |
|---|---|
| `dry` | none |
| `room` | short echo 45/90 ms, low decay |
| `cave` | echo 60/120 ms, more decay |
| `giant` | pitch −3 semitones (asetrate + atempo, length kept), bass +5 dB at 110 Hz, cave echo 70/140 ms |

## Mix targets

| Element | Target |
|---|---|
| Dialogue | compressor 4:1, +5 dB (`vo_boost_db`), limiter; keys the ducking |
| BGM | −32 LUFS, ducked by dialogue (sidechain 8:1) |
| Ambience | −39 LUFS |
| SFX segments | −30 LUFS |
| Final | loudnorm −16 LUFS integrated, −1.5 dBTP (online delivery) |

Measured: beds at −27 / −26 LUFS buried the whispers and the giant (ASR heard 2 of 10 lines); these targets heard all 10. `mix` copies the picture stream and writes AAC 256 kbps.
