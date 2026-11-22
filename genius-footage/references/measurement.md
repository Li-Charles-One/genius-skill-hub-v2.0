# Shot measurement (`measure.py`)

Every frame is decoded once. One output, 32×18, feeds the frame differences: each frame is compared with the previous frame and with the frame half a second back, and brightness tracks black. A second output, 48×27, feeds TransNetV2 (`transnet.py`), which gives every frame two probabilities: `single`, the last frame of an outgoing shot, and `many`, a frame inside a transition. Frame numbers are decode order (`-fps_mode passthrough`), times come from each frame's pts (variable frame rate is handled and warned), and timecode starts from the camera tag (drop-frame aware) or 00:00:00:00. Timecode counts `tc_fps`: the nominal rate, or the average rate when the nominal one is at least 1.5× higher (a 24p picture on a 60 timebase counts 24).

## Frame differences

| Boundary | Rule |
|---|---|
| `cut` | change ≥6 and ≥3× the local motion level (repeated frames ignored), and ≥60% of pixels changed |
| `black` | frames at mean RGB ≤3 inside the clip; the fade in and out (≤1s each side) is one transition, the next shot starts after the black |
| `weak-cut` | a spike that misses the cut rule (part of the picture, dark or blended frames) |
| `gradual` | ≥3 frames of sustained change adding up to a different picture within 2s |

## Combined with TransNetV2

A TransNetV2 transition is a run of frames with `single` or `many` ≥0.5; runs within 2 frames merge. The two detectors match when their spans come within 2 frames.

| Case | Result |
|---|---|
| a `cut`, or measured cuts ≤3 frames apart (a flash or blur frame next to a cut), that TransNetV2 also finds | confirmed: on the measured frame for one cut; for a cluster, on TransNetV2's frame when it falls inside it |
| a `cut` or cluster TransNetV2 does not find, or a cluster where its frame falls outside | `weak-cut` suspect, `by: frames`, measured frames kept in `cuts` |
| a TransNetV2 transition no measured boundary or suspect covers | suspect, `by: transnet`: `weak-cut` from a `single` run, `gradual` from a `many` run |
| a frame-difference `weak-cut` or `gradual` | suspect as before, `by: both` when TransNetV2 also has a transition there; skipped (`check: skipped`, not sent) when TransNetV2's highest score within 2 frames is below 0.1 |
| `black` | confirmed as measured |
| `storyboard` | a suspect the model judged a new shot: a `weak-cut` from six frames each side (starts on the frame the model points to), a `gradual` from nine frames per second across it (starts on its measured first frame); `unsure` adds no cut and stays in review |

Every suspect carries `by` and `tnv2` (TransNetV2's highest score around it). Talking-head mode and the overlay sheet do not check suspects, so they put the `cuts` of one-sided measured clusters back (`restore_measured_cuts`): every measured hard cut counts there, as before TransNetV2.

Whip pans are weak for both: on emsmart.mp4 (f3376–3385) frame differences raised a `gradual` suspect and TransNetV2 scored 0.35, so it reaches the storyboard check; on 京东.mp4 (S065 f1607–f1651: factory → whip blur → aerial highway) frame differences raised nothing, and TransNetV2 has not been run on it.

Measured, frame differences alone: on a built test clip (hard cut, punch-in, 2-frame flash, dissolve, fade through black, jump cut, a hand crossing) all boundaries landed on the exact frame after the storyboard check (`scripts/selftest.py` builds a smaller such clip and checks the measured cuts and the storyboard grabs offline). On real edits, 19/19, 40/40 sampled and 72/73 confirmed cuts were real (the miss: 7.5 fps webcam footage upconverted to 30 fps). Storyboard frames are grabbed by pts relative to the container start and matched decode order pixel for pixel on five clips, including B-frame and non-zero start files. Labels are drawn with a built-in 5×7 font, so no ffmpeg `drawtext` or fonts are needed. Sheets are written to `<clip>.footage/`.

Measured, combined (2.13.0, references frame-checked on 2026-11-22, `references/field-notes.md`): no checked real boundary was lost, no checked non-cut was confirmed.
