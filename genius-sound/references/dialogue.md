# Dialogue & narration (对白&旁白)

Lines fitted to lips, character voices kept consistent across takes, and narration. Voice and efforts are generated with Seed Audio (`gen`), narration with MiMo TTS (`tts`), both through genius-voice. All of it lands in the dialogue predub (D).

## Mouth windows

1. `spot grid <project> --shot S0xx --crop W:H:X:Y` around the mouth or beak.
2. Mark, frame by frame: open, closed, half. Each opening is a syllable or a call; a closed run inside a word is a bilabial (b, p, m).
3. Write the window as `[first open, last open]` and keep the syllable pattern in the script notes.

Measured on the Odyssey clip (30 fps):

| Shot | Pattern | Line that fitted |
|---|---|---|
| S003 hero, lips | open f85–87, closed f88–92, open f93→ smile | "Out cold." — one word per opening (2.83s / 3.10s) |
| S015 hero in helmet | open f703–709 ("o"), closed f710–715, open f716–727 | "Nobody!" — the closed run is the b |
| S019 giant | wide open f939–951, no closing | a wordless growl; "Hm?" would not fit an open mouth |
| S017 giant | wide open for the whole 1.5s shot | a roar |

Off-screen time is free: back to camera, a helmet over the mouth, an eye close-up, a cutaway. Any line fits as long as it does not cover another character's visible mouth. Mark it `offscreen: true`; this is where story lines go.

## Budgets

| Speech | Rate that fits naturally |
|---|---|
| Mandarin, normal | 4–5 characters per second |
| English, normal | 3–4 syllables per second |
| Whisper | about 3 syllables per second |
| A slow, huge voice | about 2.5 syllables per second |

Count syllables against the window first, then write. A window that holds two openings gets a two-syllable line.

## Writing lines

- Follow the source when the story is recognisable. Odyssey: the name "Nobody" (无人), and the Cyclops' "gift": "I will eat you last."
- Animals make animal sounds (foley) unless the user wants talking animals.
- Wide-open sustained mouths are roars or screams (efforts); short mouth flicks are words.
- Put each line's translation in `sub_text` when the user wants subtitles; genius-subtitle `from-sound` reads it.

## Voice takes (Seed Audio)

- One take per line. A whole-scene timeline in one request drifted 0.2–0.4s per line and added words; per-line takes placed locally hit the lips.
- **Anchor**: the character's longest, most typical line, generated from the full `voice` description. Every later line sends the anchor as `--ref` and starts "In the exact voice of @音频1, …". `dialogue gen` orders anchors first and records `ref`.
- Built prompt: `[0.1s:<gen_len>s] <voice or "In the exact voice of @音频1, <name>"> <direction> in <language>: "<line>" Only the clean dry voice, close microphone, no music, no ambience, no reverb.`
- Whisper: write "a clear, audible stage whisper" and give `gen_len` ≥ 1.5 × the spoken length. "barely audible" lost words.
- Short shouts that must fill a long mouth window: ask for the stretch ("stretching the first syllable a little: \"Noo-body!\"").
- Efforts (roar, growl, gasp, chuckle): a voice cue with a `prompt` and no `line`, in the character's `@音频1` voice so it matches. Efforts also go into the M&E.
- Output is quiet (peaks around −32 dBFS); placement normalises each slice to its `peak`.

## Narration (MiMo TTS)

A cue with `kind: "narration"`. The narrator's voice, in order: `tts_voice` (a MiMo preset ID), else a clone of the anchor take, else designed from `voice`. Mark the first narration line `anchor` so later lines clone it; `direction` goes in as `--style` once the voice is a preset or a clone. TTS has no length limit and no lip sync; set `at` and keep lines from overlapping. Narration counts as off screen in `dialogue check stem` (±0.5s).

Measured 2026-11-04: a designed anchor (6.56s) and a cloned second line (2.08s) both read back word for word by ASR; the pair took 7s.

## FX presets (`characters.*.fx`)

| Preset | Chain |
|---|---|
| `dry` | none |
| `room` | short echo 45/90 ms, low decay |
| `cave` | echo 60/120 ms, more decay |
| `giant` | pitch −3 semitones (asetrate + atempo, length kept), bass +5 dB at 110 Hz, cave echo 70/140 ms |

A raw ffmpeg filter chain also works; `pitch` (semitones) overrides the preset.

## Placing

- `at` = where the take's `in` point lands. To start the voice on frame F: `at = F / fps − (voice onset in the take − in)`. Get the onset from `dialogue check takes` (ASR word start) rather than silence detection: silence detection caught a breath 0.15s before the word.
- Two words that must hit two openings: two cues on the same take, split on the gap between the words.
- `dialogue place` writes `work/stems/dialogue.wav` (every voice and narration cue) and `efforts.wav` (non-verbal voice cues, for the M&E). `mix master` re-renders both, so `place` is only needed for `check stem`.
- On-screen tolerance in `check stem` is −0.12 / +0.18s (audio early is more visible than late). ASR word starts run 0.05–0.1s late, so a +0.05 reading is on time.
- A line that runs into the next character's visible mouth: start it earlier (if off screen), shorten with `tempo` ≤ 1.15, or regenerate shorter.

## Failure handling

| Symptom | Do |
|---|---|
| `check takes` CHECK | Listen if possible; whispers and pitched voices are often only misheard (Grip the wool → Rip the wall, Out cold → Alcohol). Regenerate under a new `take` name with a clearer direction or longer `gen_len`; the old file lands in `未采用`. |
| `check stem` CHECK on an on-screen line | Nudge `at` by −Δ; if the take is too long for the window, cut it into two cues (`in`/`out`) on a word gap, set `tempo` ≤ 1.15, or regenerate shorter. |
| PROVIDER_ERROR from genius-voice | Report the message. `gen` keeps going and lists failures at the end; rerun with `--only`. |
