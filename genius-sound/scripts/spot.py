"""Spotting: start a project, read frames (mouths, feet, hands) and print the cue sheet every module shares."""
from __future__ import annotations

import json, math, re, shutil
from pathlib import Path

from core import (SoundError, P, bed_file, bed_kind, cue_at, cue_kind, ffmpeg, letterbox, load, probe, run,
                  save, shots, DIALOGUE_KINDS)


def cmd_init(a) -> None:
    clip = Path(a.clip).expanduser().resolve()
    if not clip.exists():
        raise SoundError("INPUT_NOT_FOUND", f"{clip} not found")
    proj = Path(a.dir).expanduser().resolve() if a.dir else clip.parent / f"{clip.stem}-sound"
    if ((proj / "sound.json").exists() or (proj / "dub.json").exists()) and not a.force:
        raise SoundError("UNSUPPORTED_FORMAT", f"{proj} already has a project file (use --force to overwrite)")
    for sub in ("src", "takes", "beds", "work", "out"):
        (proj / sub).mkdir(parents=True, exist_ok=True)
    dst = proj / "src" / f"clip{clip.suffix.lower()}"
    if not dst.exists():
        shutil.copy2(clip, dst)
    v = probe(dst)
    pic = letterbox(dst, v["duration"], v["height"])
    vol = run(["ffmpeg", "-hide_banner", "-i", dst, "-af", "volumedetect", "-vn", "-f", "null", "-"], check=False).stderr
    mx = re.search(r"max_volume: (-?[\d.]+) dB", vol)
    d = {"title": a.title or clip.stem, "summary": "", "clip": f"src/{dst.name}", "source": str(clip),
         "video": v, "picture": pic, "original_audio_max_db": float(mx.group(1)) if mx else None,
         "language": a.language, "characters": {}, "cues": [], "beds": [],
         "mix": {"spec": "web", "vo_boost_db": 5}, "notes": [], "_dir": str(proj), "_file": "sound.json"}
    save(d)
    has_sound = d["original_audio_max_db"] is not None and d["original_audio_max_db"] > -60
    print(json.dumps({"project": str(proj), "video": v, "picture": pic,
                      "original_audio_max_db": d["original_audio_max_db"],
                      "original_sound": "present: keep it with a dialogue bed on src/" + dst.name if has_sound else "none"},
                     ensure_ascii=False, indent=1))


DUP = 0.5  # YDIF below this: a repeated frame (frame-rate conversion), not a stop in the action


def motion(d: dict, f0: int, f1: int, crop: str) -> dict[int, float]:
    """Mean luma change per frame inside the crop (signalstats YDIF), keyed by frame number.
    Frames are counted from the selection, not from pts: streams can start a few frames after zero."""
    p = run(["ffmpeg", "-hide_banner", "-i", P(d, d["clip"]), "-vf",
             f"select='between(n,{f0},{f1})',{crop}signalstats,metadata=print:key=lavfi.signalstats.YDIF:file=-",
             "-an", "-f", "null", "-"], 900)
    out, n = {}, None
    for line in p.stdout.splitlines():
        m = re.match(r"frame:(\d+)", line)
        if m:
            n = f0 + int(m.group(1))
        m = re.search(r"YDIF=([\d.]+)", line)
        if m and n is not None:
            out[n] = float(m.group(1))
    out.pop(f0, None)  # the first selected frame is compared with nothing
    return out


def cmd_grid(a) -> None:
    d = load(a.project); fps = d["video"]["fps"]
    if a.shot:
        s = next((s for s in shots(d) if s["id"] == a.shot), None)
        if not s:
            raise SoundError("INPUT_NOT_FOUND", f"shot {a.shot} not in shot list")
        f0, f1 = s["first"], s["last"]
    else:
        f0, f1 = (int(x) for x in a.frames.split("-"))
    crop = f"crop={a.crop}," if a.crop else ""
    n = len(range(f0, f1 + 1, a.step)); rows = math.ceil(n / a.cols)
    out = P(d, f"work/grid/{a.name or f'f{f0}-{f1}'}.jpg"); out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg("-i", P(d, d["clip"]), "-vf",
           f"select='between(n,{f0},{f1})*not(mod(n-{f0},{a.step}))',{crop}scale={a.width}:-1,"
           f"tile={a.cols}x{rows}:padding=2:color=white", "-vsync", "vfr", "-frames:v", "1", out)
    print(out)
    mo = motion(d, f0, f1, crop) if a.motion else {}
    for r in range(rows):
        fr = [f0 + (r * a.cols + c) * a.step for c in range(a.cols) if r * a.cols + c < n]
        line = f"row {r + 1}: f{fr[0]}–f{fr[-1]}  ({fr[0] / fps:.2f}s–{fr[-1] / fps:.2f}s)"
        if mo:
            line += "  motion " + " ".join(("=" if mo[f] < DUP else f"{mo[f]:.0f}") if f in mo else "·" for f in fr)
        print(line)
    if a.motion:
        dups = sum(v < DUP for v in mo.values())
        print("motion = mean luma change from the previous frame inside the crop; a sharp drop after a busy run "
              "is a candidate contact, confirm on the grid" + (f"; {dups} repeated frames (=), e.g. 24→30 fps pulldown"
                                                               if dups else ""))


def cmd_sheet(a) -> None:
    """Cue sheet: what each module has on every shot, plus the beds. Written to 定点表.md."""
    d = load(a.project); fps = d["video"]["fps"]

    def when(c):
        at = cue_at(d, c)
        return at if at is not None else (c["window"][0] / fps if c.get("window") else None)
    groups = {"dialogue": DIALOGUE_KINDS, "foley": {"foley"}}
    lines = [f"# 定点表 · {d['title']}", "", f"{d['video']['duration']}s · {fps}fps · 对白语言 {d['language']}", "",
             "| 镜头 | 帧 | 时间 | 对白&旁白 | 拟音 |", "|---|---|---|---|---|"]
    for s in shots(d):
        t0, t1 = s["first"] / fps, (s["last"] + 1) / fps
        cells = []
        for kinds in groups.values():
            hit = [c for c in d["cues"] if cue_kind(c) in kinds and when(c) is not None and t0 <= when(c) < t1]
            cells.append("<br>".join(f"{c['id']} {d['characters'].get(c.get('char', ''), {}).get('name', c.get('char', ''))}："
                                     f"{c.get('line') or c.get('label') or '（声音）'}" for c in hit) or "")
        lines.append(f"| {s['id']} | {s['first']}–{s['last']} | {t0:.2f}–{t1:.2f}s | {cells[0]} | {cells[1]} |")
    unplaced = [c["id"] for c in d["cues"] if when(c) is None]
    if unplaced:
        lines += ["", f"未定位的 cue：{', '.join(unplaced)}"]
    names = {"sfx": "音效", "amb": "环境", "music": "配乐", "foley": "拟音", "dialogue": "对白"}
    lines += ["", "## 底床（音效 / 环境 / 配乐 / 外部分轨）", "", "| 编号 | 类型 | 起点 | 目标响度 | 避让 | 文件 |", "|---|---|---|---|---|---|"]
    for b in d["beds"]:
        lines.append(f"| {b['id']} | {names.get(bed_kind(b), bed_kind(b))} | {b.get('at', 0)}s | {b.get('lufs', '默认')} | "
                     f"{'是' if b.get('duck') else '否'} | {'已有' if bed_file(d, b).exists() else '未生成'} |")
    text = "\n".join(lines) + "\n"
    P(d, "定点表.md").write_text(text, encoding="utf-8")
    print(text)
