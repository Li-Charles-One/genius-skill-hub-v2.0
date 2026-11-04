# sound.json

Everything lives in `<project>/sound.json`, written by `spot init` and edited by the agent. A genius-dub 1.x project's `dub.json` loads the same way and is written back under its own name. Paths are relative to the project folder (absolute paths work for `file`). Times: `at` in seconds, `window` / `sub` in frames (inclusive).

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
  "narr": {"name": "旁白", "voice": "沉稳的中年男声，嗓音低沉温暖，语速偏慢，像纪录片旁白。"},
  "duck": {"name": "duck", "fx": "dry"}
 },
 "cues": [
  {"id": "12", "char": "ody", "anchor": true, "take": "ody_12", "line": "Here, Cyclops... taste this.",
   "direction": "speaks low and careful, forcing himself to stay calm,", "window": [991, 1055], "offscreen": true,
   "in": 0.0, "out": 2.2, "at": 33.0, "peak": -7, "sub_text": {"zh": "来，独眼巨人……尝尝这个"}},
  {"id": "01a", "char": "ody", "take": "ody_01b", "line": "Out cold.", "direction": "says in a clear, audible stage whisper,",
   "window": [85, 100], "in": 0.10, "out": 0.66, "at": 2.75},
  {"id": "08", "char": "poly", "take": "poly_08", "prompt": "In the exact voice of @音频1, the giant roars. No words.",
   "at": 25.9, "label": "roar"},
  {"id": "n1", "char": "narr", "kind": "narration", "anchor": true, "line": "三千年前，一位英雄被困在巨人的洞穴里。",
   "direction": "低沉、克制", "at": 1.0},
  {"id": "15a", "char": "duck", "kind": "foley", "take": "duck_15", "prompt": "[0s:3.5s] A white duck quacks several times...",
   "in": 0.14, "out": 0.42, "at": 37.88, "peak": -10, "label": "quack"}
 ],
 "beds": [
  {"id": "bgm", "kind": "music", "at": 0, "lufs": -32, "duck": true, "prompt": "Instrumental film score only... [0s:10.4s] ..."},
  {"id": "amb", "kind": "amb", "at": 0, "lufs": -39, "prompt": "[0s:43.4s] Continuous ambience inside a vast stone cave..."},
  {"id": "sfx_b", "kind": "sfx", "at": 10.43, "lufs": -30, "mutes": [[11.3, 13.1, 0.12]], "prompt": "..."},
  {"id": "sfx_c", "kind": "sfx", "at": 27.43, "lufs": -31, "trim": [0, 10.3], "prompt": "..."},
  {"id": "production", "kind": "dialogue", "file": "src/clip.mp4"}
 ],
 "mix": {"spec": "web", "vo_boost_db": 5},
 "notes": ["deviations from the script and known issues, shown in the package README"]
}
```

## Characters

| Field | Meaning |
|---|---|
| `name` | How prompts refer to the character after the anchor ("In the exact voice of @音频1, the warrior …"). Write it in the dialogue language. |
| `voice` | Full voice description used until an anchor exists (gender, age, accent, timbre, pace); for a narrator, the MiMo `--design` text. |
| `tts_voice` | Narrator only: a MiMo preset voice ID; wins over `ref` and `voice`. |
| `fx` | `dry`, `room`, `cave`, `giant`, or a raw ffmpeg filter chain. |
| `pitch` | Semitones, overrides the preset. |
| `ref` | Set by `dialogue gen` after the anchor take; later lines send it as `@音频1` (voice) or `--clone` (narration). |
| `peak` | Default peak dBFS for this character's cues. |

## Cues

| Field | Meaning |
|---|---|
| `id` | Unique, also the default take name. |
| `char` | Character key. |
| `kind` | `voice` (default: lines and efforts), `narration` (MiMo TTS), `foley`. `sound` from genius-dub reads as `foley`. |
| `take` | WAV name in `takes/` (no extension). Several cues may slice one take. A new name means a new generation. |
| `line`, `direction` | Spoken text and how it is said. A voice cue without `line` is an effort and also goes into the M&E. |
| `prompt` | Replaces the built prompt (foley, efforts). Without a `[a s:b s]` tag one is added from `gen_len`. |
| `anchor` | Generate this cue first and use its take as the character's `ref`. |
| `gen_len` | Seconds requested from Seed Audio; default 1.5 × window + 0.1. |
| `lang` | Language of this line when it differs from `language`. |
| `window` | Frames where the sound belongs: the mouth or contact window on screen, or the intended span off screen. |
| `offscreen` | No lips visible: `dialogue check stem` tolerates ±0.5s instead of −0.12/+0.18s. |
| `in`, `out` | Slice of the take, seconds. |
| `at` / `at_frame` | Where `in` lands on the timeline. |
| `peak`, `tempo`, `fx`, `pitch` | Per-cue level (default −6 dialogue, −8 foley), speed (≤ 1.15 stays natural) and colour. |
| `label` | Shown in the cue sheet and README for cues without a line. |
| `sub_text`, `sub`, `split_subs`, `no_sub` | Subtitle data: translations, explicit subtitle frames, one take split into several events, spoken but not subtitled. Read by genius-subtitle `from-sound`; genius-sound ignores them. |

## Beds

| Field | Meaning |
|---|---|
| `id` | Generated file `beds/<id>.wav`. |
| `kind` | `music`, `sfx`, `amb`, `foley`, `dialogue`. Without it (genius-dub projects): `bgm*`/`music*`/`score*` → music, `amb*`/`bg*`/`room*` → amb, else sfx. |
| `file` | Use this audio (or a video's audio) instead of generating. |
| `prompt` | Seed Audio prompt, ≤ 120 s, with `[a s:b s]` tags. |
| `at` | Timeline start. |
| `lufs` | Target for the bed's own loudness; defaults music −32, amb −39, sfx / foley −30, dialogue unchanged. |
| `duck` | Dialogue ducks it. |
| `trim` | `[start, end]` in bed time. |
| `mutes` | `[[start, end, gain], …]` in bed time after trim. |

## Mix

`spec` (delivery spec, see `mix-master.md`), `vo_boost_db` (dialogue gain after compression). genius-dub's `lufs` / `tp` / `lra` are dropped on the first `mix master` (they matched `web`).

## Written by the script

`characters.*.ref` (by `dialogue gen` on anchors), `mix.spec` and `mix.measured` (by `mix master`), `work/stems/*.wav` and `*_events.tsv`, `work/checks/*.json`, `定点表.md` (by `spot sheet`).
