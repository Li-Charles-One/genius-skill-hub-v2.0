# Review Guide

`report.md` holds measurements. This guide turns them into findings.

## Picture

| Check | How it is measured | Read it as |
|---|---|---|
| Black | `blackdetect`, ≥0.1 s, pixel threshold 0.10 | Unintended unless at the very start/end or a deliberate dip |
| Freeze | `freezedetect`, ≥2 s with no change | Usually a title card, still image or end card; a problem only inside live footage |
| Flash / stray frames | per-frame brightness and saturation; a run of ≤0.12 s that jumps away from one stable stretch and into another | Leftover frames at a cut or a mis-graded frame. Confirm with `zoom --full --span 0.2` |
| Cuts | `scdet`, threshold 10 | Context only: count and shortest shots |
| Screen-text scan | OCR on a frame every 2 s, keyword list in `scripts/qc.py` | Hits for 花字/落版/【】 are unfinished packaging; 光厂/VJshi/素材 etc. are stock watermarks. Misses faint marks: view the sheets |

On the overview sheets look for: watermarks (often a pale logo top-left or centre), placeholder text, notes for the designer, wrong or repeated shots, colour jumps between neighbouring cells of the same scene.

## Subtitles

Cues come from OCR on the subtitle band every 0.5 s; samples that read alike are merged.

Differences against the transcript:

- **high**: a same-length swap of ≤4 characters (PVC/PTC, 他/它, 功率/工艺). Most likely a typo, but OCR misreads land here too.
- **pattern**: the same swap three or more times. Usually the ASR mishearing a product name (G2 heard as J2); can also be a term misspelt the same way throughout.
- **medium**: longer insertions or deletions, or any difference in a cue whose OCR samples disagree. Mostly subtitle condensation or OCR noise; a missing or extra subtitle line also shows up here.
- **low**: number formats (2,600 vs 两千六百) and dropped filler words. In `report.json` only.

To confirm one item:

1. `zoom <video> --at <cue start + 0.3> --span 0.2` (subtitle band) to read the burnt-in text.
2. `recheck <video> --from <t-2> --to <t+4>` for a second listening. Two ASR passes agreeing with each other and not with the subtitle is strong evidence.
3. Decide with domain sense: PTC is a heater element, PVC a plastic.

The diff cannot see errors the ASR shares (a brand written the way it sounds, such as 「服务加」 for 「服务+」; personal names) or pure grammar (真正的走进 → 真正地走进 shows only when the ASR wrote 地). Read `subs.srt` once for: 的/地/得, 他/她/它, names and brand terms (ask the client when unsure), number style consistency, stray spaces, mixed punctuation, a key number shown for under a second.

## Audio

| Measure | Target |
|---|---|
| Integrated loudness | Web video around -14 LUFS (platforms normalize); podcast/voice -16; broadcast EBU R128 -23 |
| True peak | ≤ -1 dBTP; above that, lossy encoding can distort |
| Seconds at full scale (sample peak ≥ -0.1 dBFS) | Possible clipping; listen to the listed seconds |
| Loud stretches (RMS 8 dB over the median) | Music swells or effects that jump out |
| Silence ≥2 s at -50 dB | Dead air unless intended |

## Final report template

```markdown
## 必须修
| 时间 | 问题 | 证据 | 建议 |
## 建议改
| 时间 | 问题 | 证据 | 建议 |
## 需确认
| 时间 | 内容 | 为什么要确认 |
## 已检查无问题
- 黑场、定格、……
## 覆盖范围与局限
- 抽样间隔、OCR/ASR 后端、未覆盖的内容
```

Severity: anything that breaks delivery (watermark, placeholder, wrong fact or term, flash frame, clipping) is must-fix; style consistency is should-fix; names, brand terms and anything only the client can know go to needs-confirmation.
