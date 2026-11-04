# Mix & master (混录&母带)

`mix master <project> [--spec web|stream|ebu|tv24|netflix]` does the re-recording mix and the master in one run, from the cues and beds in the project file. The spec is remembered in `mix.spec`; default `web`.

## Predub (D / M / E)

| Predub | Holds | Processing |
|---|---|---|
| D dialogue | voice and narration cues (`work/stems/dialogue.wav`), `dialogue` beds (production sound) | compressor 4:1, +`vo_boost_db` (default 5 dB), limiter; keys the ducking |
| M music | `music` beds | `duck: true` beds: sidechain 8:1 keyed by D |
| E effects | foley cues (`work/stems/foley.wav`), `sfx` and `amb` beds | `duck: true` works here too |
| X efforts | non-verbal voice cues (`work/stems/efforts.wav`), D's processing | only for the M&E |

Each bed is levelled to its own `lufs` (defaults: music −32, ambience −39, sfx and foley beds −30; `dialogue` beds keep their level), trimmed, muted and delayed to `at`. Placed cues are re-rendered on every run, so a changed `at` needs no separate `place`.

## Master

1. Measure the integrated loudness of D + M + E (dialogue-gated for `netflix`).
2. Apply one static gain to reach the target, then a true-peak limiter (4× oversampled, ceiling 0.3 dB under the spec). If the limiter pulls the loudness down, correct the gain and render again (at most 3 passes).
3. Export with that same gain: `out/stems/<title>_master.wav`, `_D`, `_M`, `_E` and `_ME` (M + E + efforts), 48 kHz 24-bit. D + M + E equals the master before the limiter.
4. Mux the master into `out/<title>_mix.mp4` (picture copied, AAC 256 kbps), the sound offset to the picture stream's start time so frame n and the sound at n / fps play together; record `mix.measured`.

The result prints `PASS` / `FAIL` against the spec:

| Spec | Integrated | Tolerance | True peak | Use |
|---|---|---|---|---|
| `web` | −16 LUFS | ±1 LU | −1.5 dBTP | online video, social (default) |
| `stream` | −14 LUFS | ±1 LU | −1 dBTP | platforms that normalise to −14 (YouTube-style) |
| `ebu` | −23 LUFS | ±0.5 LU | −1 dBTP | EBU R128 broadcast |
| `tv24` | −24 LKFS | ±2 LU | −2 dBTP | ATSC A/85; China TV GY/T 282-2014 also targets −24 LKFS (its true-peak limit was not checked against the standard text) |
| `netflix` | −27 LKFS dialogue-gated | ±2 LU | −2 dBTP | Netflix Sound Mix Specifications |

`netflix` gating is an approximation: loudness is measured only over the placed spoken lines. Netflix specifies ITU-R BS.1770-1 dialogue gating (Dolby Dialogue Intelligence); check with Dolby Media Meter or an equivalent before a real delivery. Cinema (85 dB SPL room calibration) and surround (5.1/7.1) are not produced: every source is stereo.

Measured on the Odyssey clip (43.4s): `web` −16.0 LUFS / −1.8 dBTP, `ebu` −23.0, `tv24` −24.0, `netflix` −27.0 gated (−27.9 over the whole programme); D + M + E minus the master left a −70 dB mean residual.

## Intelligibility

`mix check <project>` runs ASR on the mixed video and labels each spoken line OK, MASKED (nothing heard) or MISHEARD (other words heard).

| Symptom | Do |
|---|---|
| MASKED | Raise the cue's `peak`, add a `mutes` window on the bed under it, or lower that bed's `lufs`; master again. |
| MISHEARD | Compare with `dialogue check stem`. If the stem also mishears, it is the take. If only the mix does, ASR the line's window alone (cut it from `_master.wav`): on the Odyssey clip the whole-file check dropped "I will eat you last" while the window alone read the same in the old and new masters. Only then treat it as MASKED. |
| FAIL on true peak | The limiter aims 0.3 dB under the ceiling; if the measured peak is still over, lower the loudest bed or the cue's `peak` and master again. |
| FAIL on loudness | The limiter could not reach the target without squashing: lower the loudest bed, then master again. |

## External stems

Any bed may point at a file instead of generating: `{"id": "score", "kind": "music", "file": "/path/score.wav", "duck": true}`. Kinds `dialogue`, `music`, `sfx`, `amb` and `foley` route to D, M, E, E and E. A user's finished stems can be mastered this way after `spot init` on the picture.
