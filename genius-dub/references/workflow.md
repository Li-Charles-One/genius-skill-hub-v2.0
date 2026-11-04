# Workflow, checkpoints and failure handling

## Checkpoint ① — story, tone, languages

Before writing a line, show the user what the picture says and ask only what changes the result:

| Ask | Why |
|---|---|
| Is this a known story (myth, film, novel)? Played straight or as comedy? | 2026-11-04: the first reading made the animals talk and played it for laughs; the user meant the Odyssey, played straight. |
| Dialogue language | The user switched to English after the Chinese script was approved; asking first saves a rewrite. |
| Subtitles: none / single / bilingual, which language on top, burned or external | Bilingual means Chinese on top, larger, and the other language below, unless the user says otherwise. |
| Deliverables and destination (Desktop, a folder, a zip) | `pack --dest`. |

Lead with the story reading: shot-backed beats (shot IDs), what each character is doing and the visual details that decide meaning (who grips what, who covers whose mouth, what is handed over). If a detail is ambiguous (an object the model calls an ice-cream cone), write lines that work either way and say so.

## Checkpoint ② — the script

A table: `#`, shot, window (seconds), character, line, direction, on/off screen. Add a line count per window: syllables you can fit (see `lipsync-and-script.md`). Offer one alternative for the line that carries the twist. Do not generate before the user confirms.

## Stage order

1. `init` → genius-footage brief → story reading → ①.
2. `lipgrid` per speaking shot → windows → script → ②.
3. Anchors, `gen --dry-run`, `gen`, `check takes`, retakes.
4. `place`, `check stem`, nudges.
5. Bed prompts, `gen --beds`, `env` checks, trims and mutes.
6. `mix`, `check final`, fixes.
7. `subs`, frame grabs.
8. `notes`, `pack`.

Report status at each stage in one line (users ask "咋样啦" while generation runs). Run Seed Audio jobs one at a time; long batches go in the background, with a completion notice instead of polling.

## Failure handling

| Symptom | Do |
|---|---|
| `check takes` CHECK | Listen if possible; whispers and pitched voices are often only misheard. Regenerate under a new `take` name with a clearer direction or longer `gen_len`; keep the old file (it lands in `未采用`). |
| `check stem` CHECK on an on-screen line | Nudge `at` by −Δ; if the take is too long for the window, cut it into two cues (`in`/`out`) on a word gap, set `tempo` ≤ 1.15, or regenerate shorter. |
| `check final` MASKED | Raise the cue's `peak`, add a `mutes` window on the bed that sits under it, or lower that bed's `lufs`. |
| `check final` MISHEARD | Compare with `check stem`. If the stem also mishears, it is the take; if only the mix does, treat it as MASKED. |
| Bed has a sound you did not ask for | `env <bed>`; `trim` the bed or mute the window. Note it in `notes`. |
| BGM sections do not follow the requested timeline | Accept small drift; if a beat is missing, regenerate that bed or split it into two beds. |
| `subs` DEPENDENCY_MISSING | SRT/ASS are already written. Install Pillow in a venv and rerun `subs` with that Python. |
| PROVIDER_ERROR from genius-voice | Report the message. `gen` keeps going and lists failures at the end; rerun with `--only`. |
