# dub.json

Everything lives in `<project>/dub.json`, written by `init` and edited by the agent. Paths are relative to the project folder. Times: `at` in seconds, `window` / `sub` in frames (inclusive).

```json
{
 "title": "奥德修斯与独眼巨人_英文配音",
 "summary": "one paragraph for the package README",
 "clip": "src/clip.mp4",
 "video": {"width": 1920, "height": 1080, "fps": 30.0, "frames": 1302, "duration": 43.4},
 "picture": {"top": 128, "bottom": 951},
 "language": "en",
 "characters": {
  "ody": {"name": "the warrior", "voice": "A Greek warrior hero, late thirties, deep slightly husky steady voice,",
          "fx": "room", "ref": "takes/ody_12.wav", "peak": -7},
  "poly": {"name": "the giant", "voice": "A colossal one-eyed giant, extremely deep, slow, gravelly voice,", "fx": "giant"},
  "duck": {"name": "duck", "fx": "dry"}
 },
 "cues": [
  {"id": "12", "char": "ody", "anchor": true, "take": "ody_12", "line": "Here, Cyclops... taste this.",
   "direction": "speaks low and careful, forcing himself to stay calm,", "window": [991, 1055], "offscreen": true,
   "in": 0.0, "out": 2.2, "at": 33.0, "peak": -7, "sub_text": {"zh": "来，独眼巨人……尝尝这个"}},
  {"id": "01a", "char": "ody", "take": "ody_01b", "line": "Out cold.", "direction": "says in a clear, audible stage whisper,",
   "window": [85, 100], "in": 0.10, "out": 0.66, "at": 2.75, "sub_text": {"zh": "醉倒了"}},
  {"id": "01b", "char": "ody", "take": "ody_01b", "in": 0.68, "out": 1.10, "at": 2.96, "label": "second word of 01a"},
  {"id": "15a", "char": "duck", "kind": "sound", "take": "duck_15", "prompt": "[0s:3.5s] A white duck quacks several times...",
   "in": 0.14, "out": 0.42, "at": 37.88, "peak": -10, "label": "quack"}
 ],
 "beds": [
  {"id": "bgm", "at": 0, "lufs": -32, "duck": true, "prompt": "Instrumental film score only... [0s:10.4s] ..."},
  {"id": "sfx_b", "at": 10.43, "lufs": -30, "mutes": [[11.3, 13.1, 0.12]], "prompt": "..."},
  {"id": "sfx_c", "at": 27.43, "lufs": -31, "trim": [0, 10.3], "prompt": "..."}
 ],
 "subtitles": {"layout": ["zh", "en"]},
 "mix": {"lufs": -16, "tp": -1.5, "lra": 14, "vo_boost_db": 5},
 "notes": ["deviations from the script and known issues, shown in the package README"]
}
```

## Characters

| Field | Meaning |
|---|---|
| `name` | How prompts refer to the character after the anchor ("In the exact voice of @音频1, the warrior …"). Write it in the dub language. |
| `voice` | Full voice description used until an anchor exists (gender, age, accent, timbre, pace). |
| `fx` | `dry`, `room`, `cave`, `giant` (pitch −3 semitones, bass, cave echo), or a raw ffmpeg filter chain. |
| `pitch` | Semitones, overrides the preset. |
| `ref` | Set by `gen` after the anchor take; later lines of this character send it as `@音频1`. |
| `peak` | Default peak dBFS for this character's cues. |

## Cues

| Field | Meaning |
|---|---|
| `id` | Unique, also the default take name. |
| `char`, `kind` | `kind` is `voice` (default) or `sound`. |
| `take` | WAV name in `takes/` (no extension). Several cues may slice one take. A new name means a new generation. |
| `line`, `direction` | Spoken text and how it is said; `gen` builds the prompt from these. |
| `prompt` | Replaces the built prompt (sounds, non-verbal voice such as roars, gasps, laughs). Without a `[a s:b s]` tag one is added from `gen_len`. |
| `anchor` | Generate this cue first and use its take as the character's `ref`. |
| `gen_len` | Seconds requested from Seed Audio; default 1.5 × window + 0.1. |
| `window` | Frames where the line belongs: the mouth window on screen, or the intended span off screen. |
| `offscreen` | No lips visible: `check stem` tolerates ±0.5s instead of −0.12/+0.18s. |
| `in`, `out` | Slice of the take, seconds. |
| `at` / `at_frame` | Where `in` lands on the timeline. |
| `peak`, `tempo`, `fx`, `pitch` | Per-cue level, speed (≤ 1.15 stays natural) and colour. |
| `sub_text` | Subtitle text in other languages, e.g. `{"zh": "…"}`; the spoken language comes from `line`. |
| `sub` | Explicit subtitle frames `[in, out]`; otherwise derived (see `subtitles.md`). |
| `split_subs` | `[{"sub": [f0, f1], "text": {"en": "…", "zh": "…"}}]`: one take, several subtitle events. |
| `no_sub` | Spoken but not subtitled. |
| `label` | Shown in the event table and README for cues without a line. |

## Beds

`id` (file `beds/<id>.wav`), `at` (timeline start), `lufs` (target for the bed's own loudness), `duck` (dialogue ducks it), `trim` `[start, end]` in bed time, `mutes` `[[start, end, gain], …]` in bed time after trim, `prompt` (≤ 120 s, with `[a s:b s]` tags).

## Written by the script

`subtitles.events` (by `subs`), `mix.measured` (by `mix`), `characters.*.ref` (by `gen` on anchors), `work/checks/*.json`, `work/stems/vo_events.tsv`.
