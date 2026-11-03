---
name: genius-video-qc
description: "成片质检：对一条已经剪好的视频文件做交付前检查，给出带时间码的问题清单。查画面（黑场、定格、闪帧/夹帧、素材水印、【花字】/落版等未完成占位）、字幕（读出烧录字幕，与原声转写逐句比对找错字、同音字、术语错误和格式不统一）、音频（响度、真峰值、削波、偏响段、静音）、结构与时长。用户说「检查一遍成片」「交付前质检」「看看片子有没有问题」「字幕有没有错字」「有没有水印」「声音会不会爆」时使用。不要用于剪辑或修改视频本身（用剪辑软件），不要用于单纯语音转文字或配音（用 genius-voice），不要用于视频内容总结（用 genius-omni）或带说话人的时间轴转写（用 genius-voice），不要用于生成视频或加字幕。"
metadata:
  version: "1.0.0"
---

# Genius Video QC（成片质检）

Measure a finished video with deterministic tools, then confirm every finding by eye or ear before reporting it. The script collects evidence; the agent decides what is a real problem.

## Non-Negotiables

- Read-only: never modify, re-encode or overwrite the source video.
- A typo is reported only after checking it two ways: `zoom` on the subtitle band shows the text really says that, and `recheck` (or the full transcript) shows what was said. OCR misreads busy backgrounds; ASR mishears names, models and homophones.
- Report numbers as measured. Say what was not covered (sampling gaps, no OCR backend, no ASR backend).
- The run sends audio to the ASR backend (genius-voice by default, a paid API). It runs once per output folder; `asr.json` is reused afterwards.

## Workflow

1. `python3 scripts/qc.py --check` (Windows: `python scripts\qc.py --check`). Confirms ffmpeg/ffprobe and which OCR and ASR backends are active.
2. Check the subtitle band: `zoom <video> --at <a second with a subtitle> --full --span 0.1` and look. If subtitles are not inside the default band (80–94 % of the height from the top), pass `--band top:bottom`.
3. `python3 scripts/qc.py run <video> --out <dir>` (about 3 minutes for 8 minutes of 720p50). It writes `report.md`, `report.json`, `subs.srt`, `transcript.txt` and `sheets/`.
4. Review, following `references/review-guide.md`:
   - look at every `sheets/overview_*.png` (watermarks, placeholders, wrong shots); the screen-text scan in the report lists keyword hits but misses faint marks;
   - `zoom` each flash candidate;
   - work through the subtitle ↔ speech differences: high and pattern first, then medium; confirm with `zoom` and `recheck --from --to`;
   - read `subs.srt` end to end for problems the diff cannot see (的/地/得, 他/它, terms the ASR also got wrong, spacing, punctuation);
   - judge the audio numbers against the delivery target.
5. Write the final report in the format of `references/review-guide.md`: must fix / should fix / needs confirmation / checked and fine, each item with timecode, evidence and suggested fix.

Swap OCR or ASR engines with `--ocr-cmd` / `--asr-cmd` or `QC_OCR_CMD` / `QC_ASR_CMD`; the contract is in `references/backends.md`.

## Gotchas

- Apple Vision drops some spaces, so a stray space such as 「最好 的」 can be missed by the format lint; skim `subs.srt` for spacing yourself.
- White subtitles over bright or busy shots get misread (「真金白银」 read as 「真金自银」); these land in high or medium. Always `zoom` before reporting.
- ASR hears product codes consistently wrong (G2 → J2). Such repeats collapse into one `pattern` item; they are usually ASR errors, but check one instance.
- The freeze check also flags intentional static shots (title card, still collage, end card).
- Flash detection looks for runs of ≤0.12 s between stable stretches; fast flicker and fades are ignored on purpose, so a flicker problem must be spotted on the sheets.
- Homebrew ffmpeg has no `drawtext`, so sheets carry no burnt-in timestamps; use the mapping rule printed in `report.md` and the `times` list from `zoom`.
- Without macOS (or with `--ocr-cmd none`) there is no OCR: the run builds `sheets/subs_*.png` strips, one per second, for reading by eye.

## Resource Map

- `scripts/qc.py`: `--check`, `run`, `zoom`, `recheck`.
- `scripts/ocr_vision.swift`: default OCR backend (macOS Vision, no download).
- `references/backends.md`: OCR/ASR backend contract, custom engines, environment variables, prerequisites.
- `references/review-guide.md`: what each check means, thresholds, severity rules, final report template.
- `evals/evals.json`: trigger and behavior prompts.
- `agents/openai.yaml`: Codex/UI metadata.

## Final Response

Lead with the must-fix items. For each item give timecode, what is wrong, the evidence (image or recheck), and the fix. End with coverage and limits, and the output folder path.
