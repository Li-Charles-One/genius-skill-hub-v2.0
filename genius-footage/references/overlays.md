# Overlay sheet (花字表, `overlays.py`)

Read this before running `overlays.py`: the definitions the sheet uses, and the agent check that is required before delivering.

For a finished edit whose 花字 (designed captions) and 人名条 (name lower thirds) are to be redesigned or covered. Not part of the brief, and it leaves the AG_FOOTAGE format alone.

- Steps: find (one frame per second, `--fps`, on numbered 384×216 storyboard sheets, 40 cells each; the model names the cells each overlay is on) → read (one full-resolution frame per overlay, 60% of the way through its cells; the model copies the text and boxes it) → edges (cells cropped around that box, about every 0.1 s across the gap between two samples; the model picks the first / last cell where any part shows, searching up to two more seconds out when it already shows at a run's outer end) → `measure.py` cuts say how each one enters and leaves (with a cut, a few frames before or after one, or inside a shot).
- In and out are a reference for the editor, who sets the exact frames: about 0.1 s precision (one edge cell, 5 frames at 50 fps), no every-frame pass. Definitions in the sheet: 入点 = first cell where any element shows (lines, bars and sparkles that lead the text included); 出点 = last cell where any shows, inclusive (an editor enters 出点 + 1); 可读 = first cell where its first line is complete. The box is the model's, on the full-resolution frame: approximate, widen it before covering an old overlay.
- Listed with sampled times only (± one sample): 3D text signs (字牌), title cards, full-screen graphics, labels. Not listed: dialogue subtitles, watermarks, text filmed in the scene. Not provided: the frame each further line of a multi-line overlay appears.
- `--fps 2` doubles the find sheets; use it when overlays may be shorter than about one second.

## Agent check, before delivering

The model's sheet is checked by the agent, roughly, and the agent corrects the final output. Every frame the agent writes comes from a labelled frame it looked at, never from playback or estimation.

1. Open every `<clip>.overlays/check_*.jpg`: one row per overlay, cropped to its box. `ID-1` is one cell before 入点 and should not show it, `ID-2` 入点 and `ID-3` 出点 should, `ID-4` one cell after 出点 should not. Compare the table text with `read_NN.jpg` when in doubt.
2. Roughly right passes: up to about 0.2 s off is fine, so a faint first frame of a fade showing in `ID-1` is not a fault, nor an empty `ID-2` on a cut frame or an empty `ID-3` at the tail of a fade-out (edges are snapped to cuts and the last faint frames count). Fix what is clearly wrong: the overlay plainly in `ID-1` or `ID-4`, missing from `ID-2` or `ID-3`, wrong text, not a 花字 / 人名条 at all, or a review line that does not hold (先在上一个镜头出现 is right only if it already shows before that cut).
3. To find the right frame: `--look ID FIRST-LAST[:STEP]` writes a strip cropped to that overlay (`full` instead of an ID for the whole frame), each cell labelled with its frame number, at most 40 cells.
4. Apply: `--fix "N1 in=1149" "H06 text=…" "H12 drop"`, or `--fix` alone when nothing needs changing. Timecode, duration and the enter / leave wording are recomputed; the sheet's status becomes ok and its last section lists what the check changed.

## Field notes

- Overlay text must be read on the full-resolution frame: on 384-px cells the model misread brand names differently every run and once invented text (「拿捏Midea！」 for 「京东JWELL」). The read pass got 20/20 on 京东.mp4 (7:10, 17 花字 + 3 人名条, hand-checked baseline, 2026-11-05).
- Overlay edges on that clip (2.4.1: 0.1 s cells, edges snapped to a measured cut inside their cell): out-points 20/20 within 5 frames; in-points 17/20, late on faint fade-ins (H07 +10, H11 +6) because the model picks the first cell it can clearly see. Exit wording matched the hand check on 18/20; a cut `measure.py` misses (weak suspects stay unchecked here) turns 随镜头切走 into 在镜头内消失. 4 min, about 29 requests at 3 workers. 2.4.0's extra every-frame pass took 7 min and still left fade-ins 3–6 frames late.
- Agent check on 京东.mp4 (2.5.0): 4 check sheets and 2 `--look` strips, one fix (人名条 text 「韩 耘」 → 「韩耘」, letter spacing read as a space); after it count and text 20/20, out-points 20/20 and in-points 18/20 within 5 frames, the other two faint fade-in starts within 0.2 s, passed as roughly right.
- A run widened into the previous shot can take other text there for the overlay: N1 came out 14 and 24 frames early on two runs (a 3D sign in the crop). True early entries (H16, H17) look the same, so every 先在上一个镜头出现 goes to review.
- 3D text signs get listed as 花字 on the find sheets; the read pass sees no overlay text on them and moves them to other packaging as 字牌或实拍文字, with a warning. A caption that grows out of a 3D sign can carry the sign's text in its read (H06 once read 爆款 / 的诞生 / …).
- Boxes drawn on storyboard sheets are unreliable; on the full-resolution frame they were right on 22 of 23, the miss a half-drawn name bar.
