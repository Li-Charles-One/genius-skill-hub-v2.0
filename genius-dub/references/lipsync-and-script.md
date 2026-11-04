# Mouth windows, line budgets, placement

## Reading a window

1. `dub.py lipgrid <project> --shot S0xx --crop W:H:X:Y` with the crop around the mouth or beak (one full-frame grab first to find it). The script prints which frames each row holds.
2. Mark, frame by frame: open, closed, half. Each opening is a syllable or a call; a closed run inside a word is a bilabial (b, p, m).
3. Write the window as `[first open, last open]` and keep the syllable pattern in the script notes.

Measured on the Odyssey clip (30 fps):

| Shot | Pattern | Line that fitted |
|---|---|---|
| S003 hero, lips | open f85–87, closed f88–92, open f93→ smile | "Out cold." — one word per opening (2.83s / 3.10s) |
| S015 hero in helmet | open f703–709 ("o"), closed f710–715, open f716–727 | "Nobody!" — the closed run is the b |
| S019 giant | wide open f939–951, no closing | a wordless growl; "Hm?" would not fit an open mouth |
| S017 giant | wide open for the whole 1.5s shot | a roar |
| S013 duck | openings at f612, f624, f634, f648 | four quacks, one per opening |
| S012 lamb | small f566–569, wide f589–592 | one bleat starting at f566 |

## Off-screen time is free

Back to camera, a helmet over the mouth, an eye close-up, a cutaway: any line fits as long as it does not cover another character's visible mouth. Mark it `offscreen: true`. This is where the story lines go.

## Budgets

| Speech | Rate that fits naturally |
|---|---|
| Mandarin, normal | 4–5 characters per second |
| English, normal | 3–4 syllables per second |
| Whisper | about 3 syllables per second |
| A slow, huge voice | about 2.5 syllables per second |

Count syllables against the window first, then write. A window that holds two openings gets a two-syllable line.

## Writing lines

- Follow the source when the story is recognisable. Odyssey example: the name "Nobody" (无人), and the Cyclops' "gift": "I will eat you last."
- Animals: animal sounds only, unless the user wants talking animals.
- Wide-open sustained mouths are roars or screams; short mouth flicks are words.
- Keep a line's meaning even if the take comes back with an extra word; record the difference in `notes` and subtitle what is said.

## Placing

- `at` = where the take's `in` point lands. To start the voice on frame F: `at = F / fps − (voice onset in the take − in)`. Get the onset from `check takes` (ASR word start) rather than silence detection: silence detection caught a breath 0.15s before the word.
- Two words that must hit two openings: two cues on the same take, split on the gap between the words.
- After `place`, `check stem`: on-screen tolerance is −0.12 / +0.18s (audio early is more visible than late). ASR word starts run 0.05–0.1s late, so a +0.05 reading is on time.
- A line that runs into the next character's visible mouth: start it earlier (if off screen), shorten with `tempo` ≤ 1.15, or regenerate shorter.
