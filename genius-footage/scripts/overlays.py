#!/usr/bin/env python3
"""
Genius Footage — overlay text sheet (花字表) for one edited video: `<clip>.overlays.md` + `.overlays.json`
+ `.overlays/` (storyboards), next to the clip.

    python3 overlays.py <clip> [--fps 1] [--model M] [--workers 3] [--output text|json]

Steps: find — frames sampled at --fps on numbered storyboard sheets, the model names the cells each overlay
is on → read — one full-resolution frame per 花字 / 人名条, the model copies the text and boxes it → edges —
cells cropped around that box, first every few frames across the gap between two samples, then every frame,
the model picks the first / last cell where the overlay shows → measure.py cuts say how it enters and leaves.
The model only names cells; every frame number comes from the sampling grid, timecode from measure.py.
"""

from __future__ import annotations

import argparse
import difflib
import json
import math
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import client
import measure
import storyboard
from client import FootageError
from footage import VIDEO_EXTENSIONS, WORKERS, _ask, _json

FIND_FPS = 1             # 京东.mp4 2026-11-05: 1 fps and 2 fps both found 20/20 overlays (shortest 2.2 s)
FIND_CELL, FIND_COLS, FIND_PER_SHEET = (384, 216), 5, 40
EDGE_STEPS = 10          # the first edge pass splits the gap between two samples into this many steps
EDGE_WIDEN = 2           # sample gaps searched further out when an overlay already shows at the run's outer end
READ_PER_CALL = 20       # full-resolution frames per read request
READ_MAX_W = 1920        # read frames wider than this are scaled down (one request stays small)
READ_AT = 0.6            # read frame: this far into an overlay's samples, when multi-line ones show every line
MARGIN = 0.1             # crop margin around the read box, share of frame width (128 px at 1280)
TARGETS = ("花字", "人名条")

FIND_PROMPT = (
    "These images are storyboard sheets of one finished, edited video. Every cell is one exact frame. "
    "Cells are sampled at a fixed interval in time order and labelled at the top-left with their number; "
    "consecutive numbers are {gap:.2f}s apart. This sheet holds cells {first}–{last}.\n"
    "Find every piece of text that was added on top of the picture in editing, and list each one once.\n"
    "cat, pick one:\n"
    "- 花字: designed caption or callout added in post (key phrases, selling points, often with decorative "
    "lines, bars, boxes or sparkles), flat on the screen\n"
    "- 人名条: name and title lower third\n"
    "- 字牌: 3D text sign composited into the scene, in perspective and moving with the camera\n"
    "- 标题卡: full-screen title or end card\n"
    "- 图文: full-screen graphics or collage with text\n"
    "- 标签: labels on CG or comparison shots\n"
    "Do NOT list: dialogue subtitles (white lines at the bottom centre), watermarks (stock-footage or logo "
    "marks), or text that physically exists in the filmed scene (screens, certificates, boxes, clothing, signs).\n"
    "For each item: text = the exact text, lines separated by ' / '; cells = every cell where any part of it "
    "(text, lines, bars, sparkles) is visible, as ranges of cell numbers, e.g. [\"0012-0018\", \"0020\"].\n"
    'Return ONLY a JSON array: [{{"cat": "花字", "text": "…", "cells": ["0012-0018"]}}]. Return [] when the '
    "sheet has none."
)
READ_PROMPT = (
    "Each image is one full-resolution frame of an edited video, numbered at its top-left. Images in this "
    "request: {ids}. For each image, list every piece of text added on top of the picture in editing: 花字 "
    "(designed captions, flat on the screen), 人名条 (name lower thirds), 字牌 (3D text signs in the scene), "
    "标题卡, 图文, 标签. Skip dialogue subtitles (white lines at the bottom centre), watermarks and text that "
    "physically exists in the filmed scene.\n"
    "text: copy it character by character exactly as it appears: keep letter case, keep or omit dots and "
    "punctuation exactly as shown, and do not correct, complete or normalise brand names to a spelling you "
    "know. Separate lines with ' / '. Write … for an unreadable character.\n"
    "box: [ymin, xmin, ymax, xmax] on a 0–1000 scale over the image, tight around every element of that "
    "overlay (text, lines, bars, sparkles, panels).\n"
    'Return ONLY a JSON array, one object per image: [{"image": 1, "items": [{"cat": "花字", "text": "…", '
    '"box": [ymin, xmin, ymax, xmax]}]}].'
)
EDGE_PROMPT = (
    "These images are storyboard cells cropped around overlay text (花字 / 人名条) in one edited video. Every "
    "cell is one exact frame. Each group is a run of frames in time order, labelled at the top-left: "
    "NNa-1 … NNa-K runs across where overlay NN appears, NNb-1 … NNb-K across where it disappears, "
    "NNm-1 … NNm-K across where its text becomes readable. {spacing}\n"
    "Overlays: {texts}\n"
    "a group: first = the first cell where any part of that overlay is visible (text, line, bar, dot, sparkle "
    "or panel, even faint or partly drawn); readable = the first cell where its first line of text is complete "
    "and legible, null if none; how = how it enters, under 12 Chinese characters (e.g. 淡入, 弹出, 逐字出现, "
    "划入, 随镜头切入, 从字牌变形出字).\n"
    "b group: last = the last cell where any part of it is still visible; how = how it leaves, under 12 "
    "Chinese characters (e.g. 随镜头切走, 淡出, 划出, 直接消失).\n"
    "m group: readable = the first cell where its first line of text is complete and legible.\n"
    "Dialogue subtitles, watermarks, text in the scene and other overlays do not count. Use null when the "
    "overlay shows in no cell of the run.\n"
    'Return ONLY a JSON array, one object per group: [{"id": "03a", "first": "03a-4", "readable": "03a-6", '
    '"how": "淡入"}, {"id": "03b", "last": "03b-7", "how": "随镜头切走"}, {"id": "03m", "readable": "03m-2"}].'
)


def _norm(s: str) -> str:
    return re.sub(r"[\s/·•,，.。!！:：;；、…\-—\"'“”‘’()（）+]", "", s).lower()


def _similar(a: str, b: str) -> float:
    """Share of the shorter text found, in order, in the longer one."""
    a, b = sorted((_norm(a), _norm(b)), key=len)
    if not a:
        return 0.0
    return sum(m.size for m in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks()) / len(a)


def _cell_size(w: int, h: int, cols: int = FIND_COLS, per_sheet: int = FIND_PER_SHEET) -> None:
    storyboard.CELL_W, storyboard.CELL_H, storyboard.COLS, storyboard.MAX_CELLS = w, h, cols, per_sheet


def _ask_twice(c: dict, jobs: list, workers: int) -> list:
    """_ask, then once more for sheets whose answer was not a JSON array."""
    answers = _ask(c, jobs, workers)
    again = [k for k, a in enumerate(answers) if not isinstance(a, list)]
    for k, a in zip(again, _ask(c, [jobs[k] for k in again], workers) if again else []):
        answers[k] = a
    return answers


# ── 1. Find: which sampled cells show which overlay ─────────────────────

def _cells(ranges, lo: int, hi: int) -> list[int]:
    out = set()
    for r in ranges if isinstance(ranges, list) else [ranges]:
        nums = re.findall(r"\d+", str(r))
        if nums:
            out.update(k for k in range(int(nums[0]), int(nums[-1]) + 1) if lo <= k <= hi)
    return sorted(out)


def _runs(cells: list[int]) -> list[list[int]]:
    """Consecutive cells as [first, last]; one missed cell inside a run is bridged."""
    runs = []
    for k in cells:
        if runs and k - runs[-1][1] <= 2:
            runs[-1][1] = k
        else:
            runs.append([k, k])
    return runs


def find(src: str, c: dict, v: dict, seek: list, out_dir: Path, workers: int) -> list[dict]:
    _cell_size(*FIND_CELL)
    groups = [(f"{k:04d}", [(f"{k:04d}", f)]) for k, f in v["grid"].items()]
    pages = storyboard.sheets(src, seek, v["fps"], groups, out_dir, "find")
    v["storyboards"] += [str(p) for p, _ in pages]
    print(f"[genius-footage] finding overlays on {len(groups)} cells, {len(pages)} sheets…", file=sys.stderr)
    jobs = [(p, FIND_PROMPT.format(gap=v["step"] / v["fps"], first=g[0], last=g[-1])) for p, g in pages]
    found = []
    for (p, g), ans in zip(pages, _ask_twice(c, jobs, workers)):
        if not isinstance(ans, list):
            v["warnings"].append(f"no answer for {p.name}: overlays on cells {g[0]}–{g[-1]} may be missing")
            continue
        for it in ans:
            if isinstance(it, dict) and str(it.get("text", "")).strip():
                for run in _runs(_cells(it.get("cells"), int(g[0]), int(g[-1]))):
                    found.append({"cat": str(it.get("cat", "")).strip(), "text": str(it["text"]).strip(), "cells": run})
    found.sort(key=lambda o: o["cells"][0])
    merged = []  # the same overlay across a sheet edge, or listed twice
    for o in found:
        m = next((x for x in merged if (x["cat"] in TARGETS) == (o["cat"] in TARGETS)
                  and o["cells"][0] <= x["cells"][1] + 2 and _similar(x["text"], o["text"]) >= 0.5), None)
        if m:
            m["cells"][1] = max(m["cells"][1], o["cells"][1])
            m["text"] = max(m["text"], o["text"], key=len)
        else:
            merged.append(o)
    return merged


# ── 2. Read: exact text and box from one full-resolution frame ──────────

def read(src: str, c: dict, v: dict, seek: list, out_dir: Path, targets: list, workers: int) -> None:
    w = min(v["width"], READ_MAX_W)
    _cell_size(w, round(v["height"] * w / v["width"] / 2) * 2)
    for t in targets:
        a, b = t["cells"]
        t["read_frame"] = v["grid"][a + int((b - a + 1) * READ_AT)]
    pix = storyboard.grab(src, seek, v["fps"], [t["read_frame"] for t in targets])
    files = []
    for k, t in enumerate(targets, 1):
        cell = bytearray(pix[t["read_frame"]])
        storyboard._label(cell, str(k))
        path = out_dir / f"read_{k:02d}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s",
                        f"{storyboard.CELL_W}x{storyboard.CELL_H}", "-i", "-", "-q:v", "2", str(path)],
                       input=bytes(cell), check=True)
        files.append(str(path))
    batches = [list(range(i, min(i + READ_PER_CALL, len(files)))) for i in range(0, len(files), READ_PER_CALL)]
    print(f"[genius-footage] reading {len(files)} overlays at full resolution…", file=sys.stderr)

    def ask(batch: list) -> list | None:
        prompt = READ_PROMPT.replace("{ids}", f"{batch[0] + 1}–{batch[-1] + 1}")
        for _ in range(2):
            ans = _json(client.call(c, [files[i] for i in batch], prompt, 300), "[", "]")
            if isinstance(ans, list):
                return ans
        return None

    by_img = {}
    with ThreadPoolExecutor(max(1, workers)) as ex:
        for ans in ex.map(ask, batches):
            for r in ans or []:
                if isinstance(r, dict) and str(r.get("image", "")).isdigit():
                    by_img[int(r["image"])] = [x for x in r.get("items") or [] if isinstance(x, dict)]
    for k, t in enumerate(targets, 1):
        t["read_image"] = files[k - 1]
        if k not in by_img:
            t["review"].append("原尺寸画面没有返回结果，文字用的是抽样故事板上的")
            continue
        items = [x for x in by_img[k] if str(x.get("text", "")).strip()]
        if not items:  # looked and saw no added text: a 3D sign or scene text taken for a 花字 on the sheet
            t["unread"] = True
            continue
        best = max(items, key=lambda x: _similar(str(x["text"]), t["text"]))
        if _similar(str(best["text"]), t["text"]) < 0.5:
            t["review"].append(f"原尺寸读到的文字和故事板上差别大（故事板上是「{t['text']}」）")
        t["text"] = str(best["text"]).strip()
        cat = str(best.get("cat", "")).strip()
        t["cat"] = cat if cat in TARGETS or cat == "字牌" else t["cat"]
        box = best.get("box")
        if isinstance(box, list) and len(box) == 4 and all(isinstance(x, (int, float)) for x in box) \
                and box[2] > box[0] and box[3] > box[1]:
            t["box"] = [max(0, min(1000, x)) for x in box]


# ── 3. Edges: first / last frame from cropped runs of frames ────────────

def _crop(box: list | None, w: int, h: int) -> tuple | None:
    if not box:
        return None
    m = MARGIN * w
    x0, x1 = max(0.0, box[1] * w / 1000 - m), min(float(w), box[3] * w / 1000 + m)
    y0, y1 = max(0.0, box[0] * h / 1000 - m), min(float(h), box[2] * h / 1000 + m)
    x, y = int(x0) // 2 * 2, int(y0) // 2 * 2
    return x, y, max(16, int(x1 - x) // 2 * 2), max(16, int(y1 - y) // 2 * 2)


def _strip(lo: int, hi: int, every: int) -> list[int]:
    return sorted(set(range(lo, hi, every)) | {hi})


def _edge_pass(src: str, c: dict, v: dict, seek: list, out_dir: Path, strips: dict, targets: list,
               spacing: str, prefix: str, workers: int) -> dict:
    """strips: {group id like '03a': [frames]} → {group id: answer}. A sheet that comes back short is asked again once."""
    if not strips:
        return {}
    _cell_size(*FIND_CELL)
    crops = {g: _crop(targets[int(g[:-1]) - 1].get("box"), v["width"], v["height"]) for g in strips}
    groups = [(g, [(f"{g}-{k}", f) for k, f in enumerate(fr, 1)]) for g, fr in strips.items()]
    pages = storyboard.sheets(src, seek, v["fps"], groups, out_dir, prefix, crops)
    v["storyboards"] += [str(p) for p, _ in pages]
    jobs = []
    for p, gids in pages:
        nums = dict.fromkeys(g[:-1] for g in gids)
        texts = "; ".join(f"{n} = 「{targets[int(n) - 1]['text']}」" for n in nums)
        jobs.append((p, EDGE_PROMPT.replace("{spacing}", spacing).replace("{texts}", texts)))
    print(f"[genius-footage] edges ({prefix}): {len(strips)} runs on {len(pages)} sheets…", file=sys.stderr)
    got = {}

    def collect(answers: list, which: list) -> None:
        for k, ans in zip(which, answers):
            for it in ans if isinstance(ans, list) else []:
                if isinstance(it, dict) and str(it.get("id")) in pages[k][1]:
                    got[str(it["id"])] = it

    collect(_ask(c, jobs, workers), list(range(len(pages))))
    short = [k for k, (_, gids) in enumerate(pages) if any(g not in got for g in gids)]
    if short:
        collect(_ask(c, [jobs[k] for k in short], workers), short)
    return got


def _index(label, gid: str, n: int) -> int | None:
    """'03a-4' → 4 when it names a cell of group gid."""
    m = re.fullmatch(r"\s*(\d+[abm])-(\d+)\s*", str(label or ""))
    return int(m[2]) if m and m[1].lstrip("0") == gid.lstrip("0") and 1 <= int(m[2]) <= n else None


def edges(src: str, c: dict, v: dict, seek: list, out_dir: Path, targets: list, workers: int) -> None:
    last, step = v["frames"] - 1, v["step"]
    every = max(1, math.ceil(step / EDGE_STEPS))
    pending = {}
    for n, t in enumerate(targets, 1):
        a, b = t["cells"]
        p0, p1 = v["grid"][a], v["grid"][b]
        t["in"], t["out"] = p0, p1          # fallbacks: the first / last sample that shows it
        if p0 > 0:
            pending[f"{n:02d}a"] = _strip(p0 - step, p0, every)
        if p1 < last:
            pending[f"{n:02d}b"] = _strip(p1, min(last, p1 + step), every)
    fine = {}
    for rnd in range(1, EDGE_WIDEN + 2):
        ans = _edge_pass(src, c, v, seek, out_dir, pending, targets,
                         f"Cells in a run are {every} frames apart.", f"edges{rnd}", workers)
        wider = {}
        for g, fr in pending.items():
            t, kind, it = targets[int(g[:-1]) - 1], g[-1], ans.get(g, {})
            if g not in ans:
                t["review"].append(f"{'入点' if kind == 'a' else '出点'}没有返回判断，用的是抽样帧")
                continue
            if it.get("how") and (rnd == 1 or not t.get("how_in" if kind == "a" else "how_out")):
                t["how_in" if kind == "a" else "how_out"] = str(it["how"]).strip()
            if kind == "a":
                r = _index(it.get("readable"), g, len(fr))
                if r is not None:  # a wider run is earlier in time, so a hit there wins
                    t["readable"] = fr[r - 1]
                    fine.pop(g[:-1] + "m", None)
                    if r > 1 and fr[r - 1] - fr[r - 2] > 1:
                        fine[g[:-1] + "m"] = list(range(fr[r - 2], fr[r - 1] + 1))
            k = _index(it.get("first" if kind == "a" else "last"), g, len(fr))
            edge = "入点" if kind == "a" else "出点"
            if k is None:
                t["review"].append(f"裁切画面里没认出{'入场' if kind == 'a' else '出场'}，{edge}用的是抽样帧")
            elif kind == "a" and k == 1:   # already showing where the samples said it was not: look earlier
                t["in"] = fr[0]
                if fr[0] > 0 and rnd <= EDGE_WIDEN:
                    wider[g] = _strip(max(0, fr[0] - step), fr[0], every)
                elif fr[0] > 0:
                    t["review"].append(f"入点可能早于 f{fr[0]}")
            elif kind == "b" and k == len(fr):
                t["out"] = fr[-1]
                if fr[-1] < last and rnd <= EDGE_WIDEN:
                    wider[g] = _strip(fr[-1], min(last, fr[-1] + step), every)
                elif fr[-1] < last:
                    t["review"].append(f"出点可能晚于 f{fr[-1]}")
            elif kind == "a":
                t["in"] = fr[k - 1]
                if fr[k - 1] - fr[k - 2] > 1:
                    fine[g] = list(range(fr[k - 2], fr[k - 1] + 1))
            else:
                t["out"] = fr[k - 1]
                if fr[k] - fr[k - 1] > 1:
                    fine[g] = list(range(fr[k - 1], fr[k] + 1))
        pending = wider
        if not pending:
            break
    ans2 = _edge_pass(src, c, v, seek, out_dir, fine, targets, "Cells in a run are consecutive frames.",
                      "frames", workers)
    for g, fr in fine.items():
        t, kind, it = targets[int(g[:-1]) - 1], g[-1], ans2.get(g, {})
        k = _index(it.get({"a": "first", "b": "last", "m": "readable"}[kind]), g, len(fr))
        if k is None:
            what = {"a": "入点", "b": "出点", "m": "可读帧"}[kind]
            t["review"].append(f"逐帧复核没有给出{what}，误差在 {every} 帧以内")
            continue
        t[{"a": "in", "b": "out", "m": "readable"}[kind]] = fr[k - 1]
    for t in targets:
        if t.get("readable") is not None and t["readable"] < t["in"]:
            t["readable"] = t["in"]


# ── 4. How it enters and leaves, from measured cuts ─────────────────────

def relations(t: dict, shots: list, fps: float, last: int) -> None:
    cuts, half = [s["first"] for s in shots[1:]], round(fps / 2)
    i, o = t["in"], t["out"]
    inside = [x for x in cuts if i < x <= o]
    head = inside[0] if inside and inside[0] - i <= half else None      # shows up just before a cut
    tail = inside[-1] if inside and o - inside[-1] < half and o + 1 not in cuts else None  # lingers past one
    if i in cuts:
        enter = "跟切点同帧出现"
    elif head is not None:
        enter = f"切点 f{head} 前 {head - i} 帧，先在上一个镜头出现"
    else:
        near = [x for x in cuts if 0 < i - x <= half]
        enter = f"切点 f{near[-1]} 后 {i - near[-1]} 帧出现" if near else "在镜头内出现"
    if o == last:
        leave = "持续到片尾"
    elif o + 1 in cuts:
        leave = "随镜头切走"
    elif tail is not None:
        leave = f"切点 f{tail} 后又留 {o - tail + 1} 帧"
    else:
        shot = next(s for s in shots if s["first"] <= o <= s["last"])
        leave = f"在镜头内消失（这个镜头到 f{shot['last']}）"
    t["enter"], t["leave"] = enter, leave
    t["crosses_cuts"] = [x for x in inside if x not in (head, tail)]


def _position(box: list | None) -> str:
    if not box:
        return "—"
    cx, cy = (box[1] + box[3]) / 2000, (box[0] + box[2]) / 2000
    col, row = "左中右"[min(2, int(cx * 3))], "上中下"[min(2, int(cy * 3))]
    return "居中" if col == row == "中" else f"{col}{row}"


# ── Run and render ───────────────────────────────────────────────────────

def run(src: str, c: dict, fps_find: float = FIND_FPS, workers: int = WORKERS) -> dict:
    clip = Path(src)
    base = clip.with_suffix("")
    if not os.access(clip.parent, os.W_OK):
        raise FootageError("UNSUPPORTED_FORMAT", f"cannot write the overlay sheet next to the clip: {clip.parent}")
    out_dir = Path(f"{base}.overlays")
    out_dir.mkdir(parents=True, exist_ok=True)
    for old in out_dir.glob("*.jpg"):  # storyboards of an earlier run would mix with this one's
        old.unlink()
    try:
        info = measure.probe(src)
        seek = measure.frame_times(src, for_seek=True)
    except measure.MeasureError as e:
        raise FootageError("DEPENDENCY_MISSING" if "not found on PATH" in str(e) else "UNSUPPORTED_FORMAT", str(e))
    fps = float(info["fps"])
    step = max(1, round(fps / fps_find))
    v = {"fps": fps, "width": info["width"], "height": info["height"], "frames": len(seek), "step": step,
         "grid": {k + 1: f for k, f in enumerate(range(0, len(seek), step))}, "storyboards": [], "warnings": []}
    bg = ThreadPoolExecutor(1)
    cuts_job = bg.submit(measure.measure, src)  # cuts are only needed at the end

    found = find(src, c, v, seek, out_dir, workers)
    targets = [dict(o, review=[]) for o in found if o["cat"] in TARGETS]
    others = [o for o in found if o["cat"] not in TARGETS]
    if targets:
        read(src, c, v, seek, out_dir, targets, workers)
        for t in targets:
            if t.get("unread"):
                v["warnings"].append(f"「{t['text']}」原尺寸画面上没认出叠加文字（多半是 3D 字牌或实拍文字），已归入其他包装")
        others += [t for t in targets if t["cat"] == "字牌" or t.get("unread")]
        targets = [t for t in targets if t["cat"] != "字牌" and not t.get("unread")]
    if targets:
        edges(src, c, v, seek, out_dir, targets, workers)
    try:
        r = cuts_job.result()
    except measure.MeasureError as e:
        raise FootageError("UNSUPPORTED_FORMAT", str(e))
    bg.shutdown()
    _, tc, _, times = measure._clock(src, str(info["fps"]), info["timecode"])
    last = r["frames"] - 1
    t_of = lambda f: times[f] if f < len(times) else f / fps  # noqa: E731
    counter = {"花字": 0, "人名条": 0}
    for t in sorted(targets, key=lambda x: x["in"]):
        t["out"] = min(t["out"], last)
        relations(t, r["shots"], fps, last)
        counter[t["cat"]] += 1
        t["id"] = f"H{counter['花字']:02d}" if t["cat"] == "花字" else f"N{counter['人名条']}"
        t.update(tc_in=tc(t["in"]), tc_out=tc(t["out"]), frames=t["out"] - t["in"] + 1,
                 seconds=round(t_of(t["out"]) - t_of(t["in"]) + 1 / fps, 2), position=_position(t.get("box")),
                 box_px=[round(t["box"][1] * v["width"] / 1000), round(t["box"][0] * v["height"] / 1000),
                         round((t["box"][3] - t["box"][1]) * v["width"] / 1000),
                         round((t["box"][2] - t["box"][0]) * v["height"] / 1000)] if t.get("box") else None)
    targets.sort(key=lambda x: (x["cat"] != "花字", x["in"]))
    for o in others:
        a, b = (v["grid"][k] for k in o["cells"])
        o.update(first=a, last=b, start=round(t_of(a), 1), end=round(t_of(b), 1))
    review = [f"{t['id']}：{x}" for t in targets for x in t["review"]]
    doc = {"tool": "genius-footage overlays.py", "file": clip.name, "generated":
           datetime.now().astimezone().isoformat(timespec="seconds"), "model": c["model"],
           "width": v["width"], "height": v["height"], "fps": round(fps, 3), "frames": r["frames"],
           "duration": r["duration"], "timecode_start": info["timecode"], "sample_every_frames": step,
           "edge_every_frames": max(1, math.ceil(step / EDGE_STEPS)),
           "status": "needs_review" if review or v["warnings"] else "ok",
           "counts": {"花字": counter["花字"], "人名条": counter["人名条"], "其他包装": len(others)},
           "overlays": [{k: t.get(k) for k in ("id", "cat", "text", "in", "out", "tc_in", "tc_out", "frames",
                                               "seconds", "readable", "position", "box", "box_px", "enter",
                                               "how_in", "crosses_cuts", "leave", "how_out", "cells",
                                               "read_frame", "read_image", "review")} for t in targets],
           "others": [{k: o[k] for k in ("cat", "text", "first", "last", "start", "end")} for o in others],
           "review": review, "warnings": v["warnings"] + r["warnings"], "storyboards": v["storyboards"]}
    md_path, json_path = Path(f"{base}.overlays.md"), Path(f"{base}.overlays.json")
    md_path.write_text(render_md(doc), encoding="utf-8")
    json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"overlays_md": str(md_path), "overlays_json": str(json_path), "status": doc["status"],
            "counts": doc["counts"], "review": review, "warnings": doc["warnings"]}


def _note(t: dict) -> str:
    parts = [t["enter"] + (f"，{t['how_in']}" if t.get("how_in") else "")]
    if t["crosses_cuts"]:
        parts.append("跨切点 " + " / ".join(f"f{x}" for x in t["crosses_cuts"]))
    parts.append(t["leave"] + (f"，{t['how_out']}" if t.get("how_out") else ""))
    return "；".join(parts)


def render_md(doc: dict) -> str:
    fps, dur = doc["fps"], doc["duration"]
    lines = [f"# {doc['file']} 花字表", "",
             f"- 源文件：`{doc['file']}`，{doc['width']}×{doc['height']}，{fps:g}fps，{doc['frames']} 帧，"
             f"{int(dur // 60)}:{dur % 60:05.2f}",
             f"- 生成：{doc['generated']}，genius-footage overlays.py，模型 {doc['model']}。每 {doc['sample_every_frames']} "
             f"帧抽一帧找花字，原尺寸画面认字，再裁出花字区域看连续帧定入点和出点（先每 {doc['edge_every_frames']} 帧一格，再逐帧）",
             f"- 帧号从 0 开始；时间码格式为 `时:分:秒:帧`，每秒 {round(fps)} 帧",
             "- **入点** = 第一帧能看到任何元素（包括先出的线条、底条、闪光）；**出点** = 最后一帧还能看到（含这一帧）。"
             "剪辑软件里出点通常要填「出点帧 + 1」",
             "- **可读** = 第一行文字完整可读的第一帧",
             "- **框** = 模型在原尺寸画面上框的大致范围（像素 x,y 宽×高），没有逐像素测量，盖旧花字前请外扩",
             "- 不算进来的：底部台词字幕、水印、画面里实拍到的文字",
             f"- 状态：**{doc['status']}**", ""]
    for n, cat in enumerate(TARGETS):
        rows = [t for t in doc["overlays"] if t["cat"] == cat]
        lines += [f"## {'一二'[n]}、{cat}：共 {len(rows)} 个", ""]
        if rows:
            lines += ["| 编号 | 文字（/ 表示换行） | 入点 帧 · 时间码 | 出点 帧 · 时间码 | 时长 | 可读 | 位置 · 框 | 入场 / 出场 |",
                      "|---|---|---|---|---|---|---|---|"]
            for t in rows:
                box = f" · {t['box_px'][0]},{t['box_px'][1]} {t['box_px'][2]}×{t['box_px'][3]}" if t["box_px"] else ""
                lines.append(f"| {t['id']} | {t['text']} | f{t['in']} · {t['tc_in']} | f{t['out']} · {t['tc_out']} "
                             f"| {t['frames']} 帧 · {t['seconds']:.2f}s | {'f' + str(t['readable']) if t['readable'] is not None else '—'} "
                             f"| {t['position']}{box} | {_note(t)} |")
            lines.append("")
    step_s = doc["sample_every_frames"] / fps
    lines += [f"## 三、其他包装文字（不算花字，只列抽样时间，误差约 ±{step_s:g} 秒）", ""]
    seen = {}
    for o in doc["others"]:
        key = next((k for k in seen if k[0] == o["cat"] and _similar(k[1], o["text"]) >= 0.8), (o["cat"], o["text"]))
        seen.setdefault(key, []).append(f"{o['start']:g}–{o['end']:g}s")
    lines += [f"- **{cat}**「{text}」：{'、'.join(spans)}" for (cat, text), spans in seen.items()] or ["- 无"]
    lines += ["", "## 待复核", ""] + ([f"- {x}" for x in doc["review"] + doc["warnings"]] or ["- 无"])
    return "\n".join(lines) + "\n"


def render_result(res: dict) -> str:
    c = res["counts"]
    lines = [f"状态：**{res['status']}** · 花字 {c['花字']} · 人名条 {c['人名条']} · 其他包装 {c['其他包装']}",
             f"花字表：`{res['overlays_md']}`", f"数据：`{res['overlays_json']}`"]
    return "\n".join(lines + [f"待复核：{x}" for x in res["review"]] + [f"⚠️ {w}" for w in res["warnings"]])


def main() -> None:
    parser = argparse.ArgumentParser(description="Overlay text sheet (花字 / 人名条, frame-accurate) for one video")
    parser.add_argument("file", help="Local video file")
    parser.add_argument("--fps", type=float, default=FIND_FPS,
                        help=f"Samples per second for finding overlays (default {FIND_FPS}; 2 for overlays under ~1 s)")
    parser.add_argument("--model", "-m", default=None, help="Model override (default FOOTAGE_MODEL or gemini-4-argon-high)")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--workers", type=int, default=WORKERS, help=f"Storyboard requests at once (default {WORKERS})")
    args = parser.parse_args()
    c = client.conf(args.model)
    try:
        if not Path(args.file).is_file():
            raise FootageError("INPUT_NOT_FOUND", f"File not found: {args.file}")
        if Path(args.file).suffix.lower() not in VIDEO_EXTENSIONS:
            raise FootageError("UNSUPPORTED_FORMAT", "overlays needs a local video file")
        if not c["api_key"]:
            raise FootageError("PROVIDER_ERROR", "API key not found: set FOOTAGE_API_KEY (or CPA_API_KEY) in scripts/.env")
        res = run(args.file, c, args.fps, args.workers)
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.output == "json"
              else f"## Overlays\n\n{render_result(res)}")
    except FootageError as e:
        print(f"Error [{e.code}]: {e}", file=sys.stderr)
        sys.exit(client.EXIT_CODES.get(e.code, 1))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
