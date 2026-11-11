# Field notes

Dated measurements behind the rules in SKILL.md and the constants in the scripts. Add a line here when a run teaches something; change SKILL.md only when it changes what the agent should do.

## Cut check and shot descriptions

- The model has the final say on doubtful cuts; the timeline stays measured. A one-frame jump starts on the frame the model points to; a sustained change starts on its measured first frame. 2.1.0 re-run (2026-11-03): on emsmart (35 suspects, CG + live) one suspected cut differed between three runs (X35 f4335 flips new shot ↔ unsure); on baiting 0 of 28 differed. No temperature is pinned, so an unsure-versus-cut boundary can flip between runs; a flipped unsure goes to review, never into the timeline silently. CG content swaps and picture-in-picture go to review as unsure.
- One model answer can omit the first groups of a sheet: a baiting run lost X01–X03, and the same page returned all three on three re-calls. Those suspects stay unchecked and land in review, so re-call a page whose answer came back short. (2.9.0: `client.ask` does this re-call itself, once.)
- Do not feed the lexicon to the cut check: its near-pairs (遮挡转场 / 遮挡穿过, 黑场 / 闪白, 叠化 / CG 内容替换) made verdicts flip (5–8 of 35 between runs).
- Two suspects close together on one transition (f4056 / f4062) can place the same cut a few frames apart between runs.
- Once in two runs the single shot-description request got no reply within 300 s (`TIMEOUT`, exit 7); the rerun passed in about a minute. Timeouts are not retried, so rerun the clip. (2.9.0: a failed or timed-out storyboard request is asked once more; a second failure leaves a hole in 待确认 instead of failing the clip.)

## Talking head

- Talking head on a hand-held 口播 (IMG_7724, 6:32, one take, 2026-11-10): the default mode flagged 381 weak suspects (90 sheets, about 20 min) and the cut check turned the one take into 12 shots (IMG_7722, 3:57: 6). `--talking-head` (2.6.0): 1 shot, 3 min 16 s. Its keep[] gave 20 pieces, 209 s; against a hand-made edit of the same clip (208 s) 187 s overlap (90%). It kept two messy restart passages the hand edit dropped (~8 s) and moved the hook to the front on its own. ASR line numbering differs between runs (63 vs 66 lines), so compare edits by frames, not U IDs.

## Speed

- Measured single-clip: an 8-min clip with 217 shots took 7.2 min at 3 workers (17 min one sheet at a time), with no 502. (2.8.0 and earlier: three storyboard requests per clip.)
- 2.9.0 against 2.8.0 (2026-11-11, same machine, whole-clip proxies already cached): default mode on emsmart.mp4 (2:59, AV1, 83 shots, 35 suspects) 295 s → 155 s, with up to 8 requests in flight from the one clip and no 502; overlay sheet on the same film 248 s → 95 s; talking head on IMG_7722 (3:57) 111 s → 106 s, and 73 s when rerun on the cached cuts and transcript. Every storyboard that depends only on measurement came out byte-identical in both versions (5 find sheets, 12 suspect sheets, the first shot sheet); the others differ because the model's answers did (one confirmed cut each way, f1797 / f2680).
- Storyboard grabs (IMG_7722, 60 fps HEVC): 130 frames in 10 runs of 13 took 21.8 s with one ffmpeg per frame and 2.5 s with one per run, pixel-identical. One process costs about 0.7 s (seek to the keyframe, decode up to the frame); each further frame in a run about 0.03 s, hence `RUN_GAP`.
- Cuts and the whole-clip proxy from one decode: four 口播 clips at once took 140–169 s of decoding as two passes each and 81–90 s as one; the measured result is identical (IMG_7722, and `selftest.py`).
- Not worth doing: the per-frame comparison in Python is about 4 s of `measure.py`'s 32 s on IMG_7722 (the rest is decoding), and hardware decoding (`-hwaccel videotoolbox`) was slower than software, 35 s against 27 s.
