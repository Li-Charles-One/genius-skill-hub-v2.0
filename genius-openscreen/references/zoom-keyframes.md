# Zoom Keyframes: Cursor-Centered Tracking

Load this before planning zooms. The numbers were measured on OpenScreen with a 3322×2160 take at padding 0. Re-measure them (see Checking) if a later OpenScreen version behaves differently.

## Why manual keyframes

- `addAutoZooms` zooms only on clicks and ignores text-selection drags. It uses 1.25–1.8× and skips the first seconds. The user called that "far from dynamic enough".
- `focusMode: "auto"` follows the pointer with a dead zone, so the cursor often rests in a corner of the frame.
- `focusMode: "manual"` with `focus` set to the cursor's telemetry `(cx, cy)` puts the cursor tip within about 1% of frame center.
- A chain of manual zooms is the camera path, and each zoom in it is a keyframe.

## Mechanics

- **Scale.** `depth`: 1=1.25×, 2=1.50×, 3=1.80×, 4=2.20×, 5=3.50×, 6=5.00×. `customScale` takes any factor up to the clip's limit; 2.5 was accepted. Quote the returned `renderedScale`, never the depth.
- **In/out move.** It lasts 0.6 + 0.55·ln(scale) s of screen time: 0.92 s at 1.8×, 1.03 s at 2.2×, 1.10 s at 2.5×. The in-move ends at `startSec` and the out-move starts at `endSec`.
- **Chain.** Two zooms at most 1.5 s apart on screen, on the same clip with no trim between them, chain together. The camera then pans from one to the next instead of zooming out, and the scale changes along the pan too.
- **Pan.** It lasts 1 s of screen time from the first zoom's `endSec` and eases out:

  | Time into pan | 0.2 s | 0.4 s | 0.6 s | 0.8 s |
  |:--|:--|:--|:--|:--|
  | Distance covered | 40% | 72% | 89% | 97% |

  A pan may run into the next zoom's span.
- **Gap over 1.5 s, or a trim between.** The camera zooms out to full view and back in. Use this on purpose at scene changes.
- **Frame edges.** The camera never leaves the frame. A cursor on the dock or a bottom input box cannot be centered vertically.

## Scale guide

| Moment | Scale |
|:--|:--|
| Typing in an input, clicking a small control | 2.2× |
| Selecting a word or a short phrase (drag) | 2.5× |
| Selecting a long sentence (over about 0.3 of screen width) | 2.2× |
| AI output, logs, streaming text | 1.8× |
| Dock, app switcher | 1.8× |
| Scene change: app opens, message sent, answer complete | Pull out to 1× (gap over 1.5 s) |

## Keyframe rules

Plan from the `scan_take.py` output: clicks, drags, flicks, idle spans and the `--track` 0.1 s bins.

1. **Still cursor.** One keyframe at its position, holding for the whole still span.
2. **Move or drag.** End the current hold at the exact time the cursor starts moving. Put the next keyframe at the destination, with `startSec` = that end + 0.7 s. The ease-out pan then tracks a 0.5–1 s move closely.
3. **Long drag (over about 1 s).** Add a midpoint keyframe targeted at where the cursor will be about 0.3 s into the pan. On a linear drag that is roughly the cursor position 0.7 s after the drag starts. Hold it 0.05 s, then continue to the end point.
4. **Tiny drag (under about 15% of the view width).** Set the focus at the drag's midpoint and do not pan.
5. **Flick.** End the previous hold 0.05–0.1 s before the flick. Expect the camera to lag about 0.3 s and accept it.
6. **Zoom-in timing.** Set `startSec` so the in-move (startSec minus the move time) begins when the cursor starts toward the target. If it starts earlier, the camera arrives first and the cursor leaves the frame.
7. **Spacing.** Keep gaps of 1.5 s or less inside one scene so the zooms chain. Use gaps over 1.5 s across a scene change so the camera pulls out.
8. **Hold length.** A hold can be as short as 0.05 s. Leave at least 0.6 s from one hold's end to the next hold's start. Otherwise the next pan starts before the last one arrives, and the camera jumps a little.

## Trims and speed regions

- **Out-move before a trim.** It must finish before the trim starts: hold end ≤ trim start − move time (1.04 s at 2.2×). The other option is to hold across the trim and zoom out after it.
- **Holds across trims.** A zoom's hold may span a trim.
- **Speed regions.** They stretch every move and pan on the ruler: 1 s of screen time becomes `speed` × 1 s of ruler. Chained keyframes inside a sped-up span overlap and jump. Merge them into one zoom whose focus is the median cursor position there; the cursor is usually still while an AI works.
- **Warnings.** Any `cutTransitions`, `cutByTrim` or `cutByJunction` in a result is a bug unless you wanted a hard cut.

## Typical arc: an app demo with an AI chat

| Beat | Camera |
|:--|:--|
| Open the app from the dock | Zoom in on the dock at 1.8×, follow the pointer along the icons, pull out as the app window opens |
| Click or double-click the input, type | Punch in to 2.2× on the input; pull out before sending so the message and the reply land in full view |
| Select text in the reply | 2.5×, tracking the drag |
| Move to the input, type the next prompt | Pan down along the chain at 2.2×; pull out at send |
| Expand the thinking or command rows | Punch in to 2.2× at the clicks |
| AI output streams | One 1.8× zoom inside a 3× speed region |
| Answer complete | Pull out to show the whole answer |
| Select key cells and sentences | 2.5× / 2.2× chain following each drag |
| Stop recording | Stay at full view |

## Checking

- **Frames.** Call `getFrames` with `projectId` at each hold, each drag midpoint, each trim junction and inside each speed region, at most 12 per call. Target: the cursor tip within about 10% of frame center, except at frame edges.
- **Measuring the camera.** Track a fixed UI landmark (a column header, a label) across closely spaced frames. The drawn cursor is smoothed (`cursor.smoothing`) and lags its true position.
- **Timeline.** `getCurrentDocument` lists `zoomInFromSec`, `zoomOutUntilSec`, `panUntilSec`, `panFromZoomId` and `panToZoomId`. Confirm the chains are the ones you meant.
