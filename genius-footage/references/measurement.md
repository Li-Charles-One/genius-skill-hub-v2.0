# Shot measurement (`measure.py`)

Every frame is decoded at 32×18 and compared with the previous frame and with the frame half a second back; brightness tracks black. Frame numbers are decode order, times come from each frame's pts (variable frame rate is handled and warned), and timecode starts from the camera tag (drop-frame aware) or 00:00:00:00.

| Boundary | Rule | Result |
|---|---|---|
| `cut` | change ≥6 and ≥3× the local motion level (repeated frames ignored), and ≥60% of pixels changed | confirmed |
| `black` | frames at mean RGB ≤3 inside the clip; the fade in and out (≤1s each side) is one transition, the next shot starts after the black | confirmed |
| `weak-cut` | a spike that misses the cut rule (part of the picture, dark or blended frames) | suspect |
| `gradual` | ≥3 frames of sustained change adding up to a different picture within 2s | suspect |
| `storyboard` | a suspect the model judged a new shot: a `weak-cut` from six frames each side (starts on the frame the model points to), a `gradual` from nine frames per second across it (starts on its measured first frame); `unsure` adds no cut and stays in review | confirmed |

Not detected: a whip-pan transition between two scenes. The blur is almost pure local motion, so the `cut` rule (change ≥3× local motion) fails and no suspect is raised; the model can only mention the change inside the shot description, and two scenes stay in one shot (京东.mp4, S065 f1607–f1651: factory → whip blur → aerial highway).

Measured: on a built test clip (hard cut, punch-in, 2-frame flash, dissolve, fade through black, jump cut, a hand crossing) all boundaries landed on the exact frame after the storyboard check (`scripts/selftest.py` builds a smaller such clip and checks the measured cuts and the storyboard grabs offline). On real edits, 19/19, 40/40 sampled and 72/73 confirmed cuts were real (the miss: 7.5 fps webcam footage upconverted to 30 fps). Storyboard frames are grabbed by pts relative to the container start and matched decode order pixel for pixel on five clips, including B-frame and non-zero start files. Labels are drawn with a built-in 5×7 font, so no ffmpeg `drawtext` or fonts are needed. Sheets are written to `<clip>.footage/`.
