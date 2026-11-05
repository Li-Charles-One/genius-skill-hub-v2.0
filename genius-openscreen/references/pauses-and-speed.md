# Pauses and Speed

Load this before cutting pauses or adding speed regions.

## The scan

```bash
python3 "<skill_dir>/scripts/scan_take.py" <take.mp4> [--track] [--output json]
python3 "<skill_dir>/scripts/scan_take.py" --latest
```

On Windows, use `python` instead of `python3`.

**What it reads**

- The take.
- Its cursor telemetry `<take>.mp4.cursor.json`, which sits next to the take. Format version 2: `samples[]` with `timeMs`, `cx`, `cy`, `visible` and `interactionType` (`move`, `click` or `mouseup`). Coordinates are fractions of the screen. Times are seconds into the take.
- `--latest` picks the newest take in OpenScreen's recordings folder:

  | OS | Folder | Status |
  |:--|:--|:--|
  | macOS | `~/Library/Application Support/openscreen/recordings/` | Verified |
  | Windows | `%APPDATA%\openscreen\recordings\` | Expected, unverified |
  | Linux | `~/.config/openscreen/recordings/` | Expected, unverified |

  The editor's `getCurrentDocument` gives a project's asset label, and the `.session.json` next to a take gives its `screenVideoPath`.

**What it reports**

- Audio level.
- Frozen-picture spans.
- Clicks and double-clicks.
- Drags: press-to-release moves over 0.01 of the screen that last at least 0.2 s. These are text selections or drags.
- Flicks: pointer moves of at least 1.5 screen widths per second.
- Idle-cursor spans.
- Pause candidates as trim ranges.

`--track` adds the cursor position every 0.1 s, for placing keyframes; with `--output json` it is the `track_0_1s` list of `[t, x, y]`. Needs ffmpeg and ffprobe. A 57 s 4K-class take scans in about 5 s.

## What counts as a pause

- **Silent takes are common.** The take often has no voice: the mic is off and the audio sits around −90 dB. OpenScreen's transcript is then empty, so pauses must come from the picture and the cursor.
- **Frozen picture.** ffmpeg `freezedetect` at n = −70 dB, d = 0.8 s, run at about half resolution.
  - −50 dB counts typing and streaming text as frozen, because changed text is a tiny part of the frame.
  - −80 dB is too strict: ticking UI counters split every freeze into pieces.
- **The cursor is not in the raw video.** With `cursorCaptureMode: editable-overlay`, OpenScreen draws the pointer later, so a frozen picture can still contain an acting user. A pause is a frozen picture **and** an idle cursor, lasting 1.5 s or more.
- **Cut the inside of a pause.** Keep 0.3 s at each end so the cut does not feel abrupt (`--pad`).
- **Retyped prompts.** The scan does not see a false start: the user types, stops, clears the input and types again. At the end of each freeze inside a typing span, call `getFrames` to see whether the input was cleared. If so, cut from just after the first keystroke of the abandoned attempt to the point in the retype where the input shows the same text again (for example "n" to "na"), so the cut is invisible. In one 143 s take this single cut saved 11 s, more than any pause trim.

**Leave these alone**

- Frozen spans where the cursor moves or drags: the user is acting.
- Hesitations of 1–1.5 s mid-typing: cutting them makes the rhythm choppy.
- The tail, where the pointer goes off to stop the recording. Ask before trimming it, and check its frames first: the last seconds may hold the payoff, such as an AI answer finishing.
- Words, when the take does have speech (`getTranscriptWords`): never cut inside one.

**Applying the trims**

- Apply the candidates you agree with in one `addTrims` call. Trims are in source seconds.
- Report the total cut.

## Speed

- **What to speed up.** Waits where the picture changes slowly but never freezes, such as AI output streaming in, builds and installs. These are better sped up than trimmed, since the viewer still sees progress. 3× was accepted.
- **Where the region goes.** `addSpeed` covers from just after the user's last action that started the wait (for example the click that expanded the output) until the result is complete. It ends before the user's next action.
- **Zooms inside the region.** Merge the zoom keyframes inside it into one zoom (see `zoom-keyframes.md`). Check that the zoom's out-move bounds in `getCurrentDocument` still clear the next trim and the next zoom.
- **Time saved.** (region length − trims inside it) × (1 − 1/speed). For example, 11.1 s with a 1.17 s trim at 3× saves 6.6 s.
