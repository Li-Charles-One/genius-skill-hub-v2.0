# Music (配乐)

Score and source music as beds (`kind: "music"`), generated with Seed Audio or supplied as files. Music goes into the music predub (M); `duck: true` lowers it under dialogue.

## Prompt

"Instrumental film score only, no vocals, no lyrics, no sound effects." plus a style line, then one `[a s:b s]` section per story beat, cut at shot boundaries from the cue sheet:

```text
Instrumental film score only, no vocals, no lyrics, no sound effects. Dark ancient Greek epic mood.
[0s:10.4s] Very quiet and secretive: a low sustained string drone, sparse soft plucked lyre notes…
[10.4s:25.1s] Tension slowly builds: sneaking low pizzicato strings, a faint deep male choir hum rising underneath.
[25.1s:31.3s] Sudden full orchestral hit, then chaotic action: pounding war drums, brass stabs, fast agitated strings.
[31.3s:37.8s] The music drops away to a single low held cello note…
[37.8s:43.4s] A dark dissonant low brass chord swells slowly, ending on a lingering low note.
```

`music gen <project> [--only IDS] [--dry-run] [--force]` generates every music bed with a `prompt` and no file yet. One request is ≤ 120 s; a longer film gets one bed per sequence, each starting at its `at`.

Measured (43s Odyssey clip): the build, the quiet drop and the final swell landed where asked; the requested action section collapsed to a 2s peak. Accept small drift; if a beat is missing, regenerate that bed or split it into two beds.

## Source music

Music playing inside the scene (a radio, a lyre on screen) is a separate bed without `duck`, placed and levelled like an effect; say "diegetic, small room, slightly distant" in the prompt.

## Levels and ducking

Default target −32 LUFS for the bed's own loudness; `duck: true` puts a sidechain compressor (8:1, keyed by the dialogue predub) on it. Measured on a narration test: music under the narration sat 19 dB lower than in the music-only stretch. Check a bed with `sound.py env beds/<id>.wav --window 0.5`.

A user's own music file: a bed with `file` and `kind: "music"`; it is mixed, ducked and never regenerated.
