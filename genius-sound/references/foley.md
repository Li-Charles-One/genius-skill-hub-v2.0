# Foley (拟音)

Sounds performed to picture: footsteps, cloth, props, hand contacts, animal calls. Every foley cue is placed on a frame like a line of dialogue; that is what separates it from effects beds. Foley goes into the effects predub (E).

## Reading the action

1. `spot grid <project> --shot S0xx --crop W:H:X:Y --motion` with the crop on the feet, hands, object or beak.
2. Mark the contact frames: heel down, hand closes, object lands, beak opens. In the motion column a contact usually shows as a sharp drop after a busy run; confirm on the grid, because camera moves and transitions move the whole crop.
3. Skip repeated frames (`=`); the contact is on a real frame.

Measured on the Odyssey clip: the duck shot S013 opened its beak at f612, f624, f634 and f648 (four quacks, one per opening); the lamb in S012 opened small at f566–569 and wide at f589–592 (one bleat starting at f566). On a full-frame pan (S018) the only sharp drop was a transition, not a contact.

## Takes

A cue with `kind: "foley"` and a `prompt` (Seed Audio, no reference). Generate a short run of the sound and slice it, rather than one take per hit:

- Animals: "A white duck quacks several times…" → slice one call per opening with `in`/`out`, reuse slices across shots.
- Footsteps: one run per surface and shoe ("slow leather sandal steps on dry cave stone, eight steps, no music, no voices"), sliced per step.
- Props and hands: one take per action ("a hand gripping thick sheep's wool, leather bracer creak").

Prompt rules: name the material, the action and the count; end with "no music, no voices, no speech, no ambience". `foley gen --dry-run` prints every prompt.

## Placing

`at` = the contact time; set `in` on the attack of the hit (find it with `sound.py env takes/<take>.wav --window 0.05`) so the slice starts on the sound, not on silence. `foley place` writes `work/stems/foley.wav` and `foley_events.tsv`; `mix master` re-renders it. Default peak −8 dBFS per cue; set `peak` per cue for distant or soft sounds.

genius-dub 1.x projects used `kind: "sound"`; it is read as foley.
