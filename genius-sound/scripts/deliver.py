"""Delivery: package the sound project (master, DME stems, M&E, source tracks, takes, project file) with a README.
Subtitles belong to genius-subtitle; the files it writes into out/ are carried along."""
from __future__ import annotations

import json, shutil, zipfile
from pathlib import Path

from core import SoundError, P, LANG_ZH, bed_file, bed_kind, cue_at, cue_kind, load, log, slug

KIND_ZH = {"music": "配乐", "amb": "环境", "sfx": "音效", "foley": "拟音", "dialogue": "对白（外部）"}


def cmd_pack(a) -> None:
    d = load(a.project); name = slug(d)
    dest = Path(a.dest).expanduser() if a.dest else P(d, "out")
    root = dest / f"{d['title']}_源文件"
    if root.exists():
        shutil.rmtree(root)

    def cp(src: Path, rel: str):
        if src.exists():
            t = root / rel; t.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src, t) if src.is_dir() else shutil.copy2(src, t)
    mixed = P(d, f"out/{name}_mix.mp4")
    cp(mixed, "01_成片/成片.mp4")
    for f in sorted(P(d, "out").glob("*_subs.mp4")):  # made by genius-subtitle on this project
        if mixed.exists() and f.stat().st_mtime < mixed.stat().st_mtime:
            log(f"skipped {f.name}: older than the current mix (burn the subtitles again)")
        else:
            cp(f, f"01_成片/{f.name}")
    cp(P(d, d["clip"]), f"02_原始素材/原始片段{Path(d['clip']).suffix}")
    for md in sorted(Path(d["_dir"]).glob("*.md")):
        cp(md, f"03_剧本与分析/{md.name}")
    clip = P(d, d["clip"])
    for ext in (".footage.md", ".footage.json"):
        cp(clip.with_suffix(ext), f"03_剧本与分析/{clip.stem}{ext}")
    cp(clip.with_suffix(".footage"), "03_剧本与分析/故事板")
    st = P(d, f"out/stems/{name}")
    for g, label in (("master", "母带_master"), ("D", "D_对白"), ("M", "M_音乐"), ("E", "E_效果"), ("ME", "ME_国际声轨")):
        cp(Path(f"{st}_{g}.wav"), f"04_分轨/DME/{label}.wav")
    cp(P(d, "work/stems/dialogue.wav"), "04_分轨/素材轨/对白轨_dialogue.wav")
    cp(P(d, "work/stems/foley.wav"), "04_分轨/素材轨/拟音轨_foley.wav")
    for b in d["beds"]:
        f = bed_file(d, b)
        cp(f, f"04_分轨/素材轨/{KIND_ZH.get(bed_kind(b), bed_kind(b))}_{b['id']}{f.suffix}")
    used = {c.get("take") or c["id"] for c in d["cues"]}
    for f in sorted(P(d, "takes").glob("*.wav")):
        cp(f, f"05_生成素材/{'已采用' if f.stem in used else '未采用'}/{f.name}")
    cp(Path(d["_dir"]) / d["_file"], f"06_工程文件/{d['_file']}")
    for f in sorted(Path(__file__).resolve().parent.glob("*.py")):
        cp(f, f"07_脚本工具/{f.name}")
    for f in sorted(P(d, "work/checks").glob("check_*.json")):
        cp(f, f"08_校验记录/{f.name}")
    for f in sorted(P(d, "work/stems").glob("*_events.tsv")):
        cp(f, f"08_校验记录/摆位表_{f.name}")
    for f in sorted(P(d, "out").glob("*.srt")) + sorted(P(d, "out").glob("*.ass")):
        cp(f, f"09_字幕/{f.name}")
    (root / "文件说明.md").write_text(readme(d, root), encoding="utf-8")
    z = root.with_suffix(".zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(root.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                zf.write(f, Path(root.name) / f.relative_to(root))
    with zipfile.ZipFile(z) as zf:
        bad = zf.testzip(); n = len(zf.namelist())
    if bad:
        raise SoundError("UNSUPPORTED_FORMAT", f"zip check failed at {bad}")
    print(json.dumps({"folder": str(root), "zip": str(z), "files": n, "mb": round(z.stat().st_size / 1e6, 1)}, ensure_ascii=False))


def readme(d: dict, root: Path) -> str:
    v, fps = d["video"], d["video"]["fps"]
    chars = "\n".join(f"| {k} | {c.get('name', k)} | {c.get('voice', '—')} | {c.get('fx', 'dry')} |" for k, c in d["characters"].items())
    kind_zh = {"voice": "对白", "narration": "旁白", "foley": "拟音"}
    rows = []
    for c in d["cues"]:
        at = cue_at(d, c)
        if at is None:
            continue
        rows.append(f"| {c['id']} | {kind_zh.get(cue_kind(c), cue_kind(c))} | {at:.2f}s | "
                    f"{d['characters'].get(c.get('char', ''), {}).get('name', c.get('char', '—'))} "
                    f"| {c.get('line') or c.get('label', '（声音）')} | {c.get('take') or c['id']} |")
    beds = "\n".join(f"| {b['id']} | {KIND_ZH.get(bed_kind(b), bed_kind(b))} | {b.get('at', 0)}s | {b.get('lufs', '默认')} | "
                     f"{'是' if b.get('duck') else '否'} | {b.get('trim') or '—'} | {b.get('mutes') or '—'} |" for b in d["beds"])
    meas = d["mix"].get("measured", {})
    notes = "\n".join(f"- {n}" for n in d.get("notes", [])) or "- 无"
    subs = "| 09_字幕 | 字幕文件（由 genius-subtitle 产出，原样附带） |\n" if (root / "09_字幕").exists() else ""
    return f"""# {d['title']} · 源文件包

{d.get('summary', '')}

- 片长 {v['duration']}s，{v['width']}×{v['height']}，{fps}fps；对白语言：{LANG_ZH.get(d['language'], d['language'])}
- 母带规格 {meas.get('spec', d['mix'].get('spec', 'web'))}：响度 {meas.get('lufs', '—')} LUFS{'（对白门限，近似）' if meas.get('dialogue_gated') else ''}，真峰值 {meas.get('true_peak', '—')} dBTP，{'达标' if meas.get('pass') else '未达标或未测'}
- 生成：豆包 Seed Audio 1.0 / 小米 MiMo TTS（genius-voice）；定点、摆位、混录、母带：genius-sound `sound.py`

## 目录

| 目录 | 内容 |
|---|---|
| 01_成片 | 换上新声音的成片（画面未重编码） |
| 02_原始素材 | 原片，未改动 |
| 03_剧本与分析 | 台词稿、定点表、genius-footage 素材说明书与故事板 |
| 04_分轨/DME | 母带与 D（对白）/ M（音乐）/ E（效果）三条分轨，三轨相加即母带（限幅前）；ME 为国际声轨（音乐 + 效果 + 非语言人声，不含台词），供外语版重配。48 kHz 24-bit WAV |
| 04_分轨/素材轨 | 对白轨、拟音轨与各音效 / 环境 / 配乐底床，未经混录处理 |
| 05_生成素材 | 每条生成素材；已采用 = 进了成片，未采用 = 被重生成替换 |
| 06_工程文件 | 工程文件：角色、台词、提示词、摆位与底床设置，改它再重跑即可 |
| 07_脚本工具 | genius-sound 脚本副本（sound.py 与各模块） |
| 08_校验记录 | 摆位表、ASR 摆位与可懂度校验 |
{subs}
## 角色

| 代号 | 名字 | 声音 | 后期 |
|---|---|---|---|
{chars}

## 对白、旁白与拟音摆位

| 编号 | 类型 | 时间线位置 | 角色 | 内容 | 素材 |
|---|---|---|---|---|---|
{chr(10).join(rows)}

## 底床

| 编号 | 类型 | 起点 | 目标响度 | 对白避让 | 裁剪 | 局部压低 [起, 止, 倍数] |
|---|---|---|---|---|---|---|
{beds}

## 如何重做

在原工程目录运行，需 ffmpeg；重新生成素材还需 genius-voice 技能：

```bash
python3 sound.py mix master <工程目录> [--spec web|stream|ebu|tv24|netflix]
```

Windows 用 `python`。改位置改 `cues[].at`，换说法改 `cues[].take` 后 `sound.py dialogue gen` 只补缺的素材。

## 备注与已知问题

{notes}
"""
