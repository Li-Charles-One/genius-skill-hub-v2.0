---
name: genius-openscreen
description: "Genius OpenScreen 录屏剪辑：通过 OpenScreen MCP 把一条录屏剪成节奏紧凑、有动感的演示片：剪掉画面静止的停顿（没有人声时按画面静止加光标静止来判定）、点击和打字时推近并让光标居中、划词拖选时用一个固定镜头框住整段选区、场景切换时拉远再推近、给 AI 输出等待段加速、截帧验收，按需导出。用户说「把这条录屏剪紧凑点」「去掉录屏里的停顿」「缩放不够动感」「要跟着鼠标走、鼠标居中」「划词的时候也要放大跟踪」「AI 输出那段太慢，加速一下」「OpenScreen 里这条 take 帮我剪一下」时使用。不要用于字幕或花字（用 genius-subtitle），不要用于镜头表或素材说明书（用 genius-footage），不要用于配音、音效、配乐（用 genius-sound），不要用于用 Remotion 做产品宣传片（用 video-shotcraft），不要用于视频内容总结（用 genius-omni），也不要用于只录屏不剪辑。"
metadata:
  version: "1.1.0"
---

# Genius OpenScreen（录屏剪辑）

This skill edits one OpenScreen take into a tight, dynamic demo through the OpenScreen MCP tools. It cuts dead pauses, punches in on clicks and typing with cursor-centered zooms, frames each text selection with one steady zoom, pulls out at scene changes, speeds up AI waits, checks frames, then exports when asked.

The deliverable is the OpenScreen project. Every edit lands in the open editor, where the user can undo it.

The default style is punchy, not gentle: 2.0–2.5× on actions, 1.8× on streaming text, cursor centered on clicks. Do not use OpenScreen's automatic zooms (`addAutoZooms`, `focusMode: "auto"`). They are too weak and do not center the cursor.

## Start Here

Classify the request:

- **Full edit**: pauses, speed, zooms, check. Export only on request.
- **Pauses only**: scan, then trim.
- **Zooms only**: scan, then plan keyframes.
- **Speed only**: add a speed region and merge the keyframes inside it.
- **Check / export**: check frames, then `exportVideo`, then `getFrames` on the export.

Read first:

1. `listProjects`, to see which project is open.
2. `getCurrentDocument`, for the clips, trims, zooms, speed regions and settings the user already set.
3. The scan.

## Non-Negotiables

- **Checkpoint first.** Call `createCheckpoint` before each batch of edits and report the checkpoint id. Checkpoints are lost when OpenScreen quits.
- **Leave the user's own choices alone.** That means padding, cursor theme, wallpaper and placed clips, unless the user asks you to change them.
- **Positions come from cursor telemetry**, either `scan_take.py` or `getCursorTrack`. Never read a position off a frame. When the action has no pointer (typing with the mouse parked, AI output), aim at the telemetry of the click that focused the input, or frame the output area; see `references/zoom-keyframes.md`.
- **Time bases.** Trims and clips are in source seconds. Zooms and speed regions are in ruler seconds. The two coincide when there is one clip starting at 0.
- **No move may cross a trim.** Zoom in/out moves and chain pans must stay clear of trims. Fix every `cutTransitions` warning.
- **Check before reporting.** Call `getFrames` at every zoom hold, every drag midpoint, every trim junction and inside every speed region. Say what you did not check.

## Workflow

1. **Scan.** Run `python3 "<skill_dir>/scripts/scan_take.py" <take.mp4> --track`, or use `--latest`. On Windows, use `python`. It lists the audio level, frozen spans, clicks, drags, flicks, idle spans and pause candidates. Rules are in `references/pauses-and-speed.md`.
2. **Understand the take.** Call `getFrames` with `path` set to the raw take, at the scan's events and frozen spans. Learn what happens and when: an app opens, a message is sent, the AI streams output, the user selects text.
3. **Trim.** Apply the pause candidates you agree with in one `addTrims` call. Leave streaming waits for the speed step. Where a typing zoom will pull out at a send, start the following trim late enough for the out-move (`references/zoom-keyframes.md`).
4. **Speed.** Call `addSpeed` on each AI-output wait (3× is a good default). Add speed regions before zooms, so the move and pan bounds that `addZooms` and `getCurrentDocument` return already include the stretch.
5. **Zoom.** Re-read `getCurrentDocument`, then remove any automatic zooms still listed with `removeModifier`; they can be gone after `addTrims`, and ids read earlier then fail. Plan manual keyframes per `references/zoom-keyframes.md`, with one zoom per speed region. Add them all in one `addZooms` call.
6. **Check.** In `getCurrentDocument`, confirm there is no `cutByTrim` and the chains are the ones you meant. Then call `getFrames` with `projectId`. Fix what is off and check again.
7. **Export**, only when the user asks. Call `exportVideo`, then `getFrames` on the exported file.

## Gotchas

- **Auto focus.** `focusMode: "auto"` has a dead zone that leaves the cursor off center. Use `manual` with `focus` set to the cursor position.
- **Pans ease out.** A pan between chained zooms covers about 40% of the way at 0.2 s, 72% at 0.4 s and 89% at 0.6 s. If a keyframe's hold ends before the cursor moves, the camera runs ahead of a slow move. A chain of short holds along a drag lurches in steps, so give each text selection one steady zoom.
- **Speed regions stretch moves.** One second of screen time becomes `speed` × 1 s on the ruler. Chained keyframes inside a sped-up span overlap and jump.
- **Frame edges.** The camera cannot leave the frame. At padding 0, a cursor on the dock or a bottom input box cannot be centered vertically.
- **Freeze threshold.** At −50 dB, `freezedetect` counts typing and streaming text as frozen. At −80 dB, ticking counters split every freeze. −70 dB at about half resolution works, and `scan_take.py` uses it.
- **Silent takes.** When no mic was recorded, OpenScreen's transcript is empty, and pauses have to come from the picture and the cursor.
- **The cursor lags in frames.** It is drawn smoothed. Measure camera motion against a fixed UI landmark, not the drawn cursor.

## Resource Map

- `scripts/scan_take.py`: scans a take for audio level, frozen spans, clicks, drags, flicks, idle spans, pause candidates and the 0.1 s cursor track (`--track`, `--output json`, `--latest`).
- `references/zoom-keyframes.md`: measured zoom and pan mechanics, the scale guide, keyframe rules, how zooms interact with trims and speed regions, a typical demo arc, and how to check.
- `references/pauses-and-speed.md`: the scan's inputs and outputs, what counts as a pause, and the speed-region rules.
- `evals/evals.json`: trigger and behavior prompts.
- `agents/openai.yaml`: Codex and UI metadata.

## Report

Report:

- **Changes.** The trims with the total time cut; the zoom count and scales; the speed regions with the time saved; the estimated final duration.
- **Checkpoint ids** for undo.
- **Checks.** Which frames you checked, and what still deviates: frame edges, flicks.
- **Export.** Whether the edit was exported, and the file path if it was.
