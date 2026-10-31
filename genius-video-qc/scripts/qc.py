#!/usr/bin/env python3
"""
Genius Video QC — measure a finished video file and collect evidence for a human-grade QC report.

    python3 qc.py --check
    python3 qc.py run <video> [--out DIR] [--lang zh] [--band 0.80:0.94] [--sub-step 0.5]
                      [--scan-step 2] [--skip asr,ocr,scan,sheets] [--ocr-cmd CMD] [--asr-cmd CMD]
    python3 qc.py zoom <video> --at SEC [--span 0.4] [--step 0.02] [--band 0.80:0.94 | --full] [--out FILE]
    python3 qc.py recheck <video> --from SEC --to SEC [--lang zh] [--asr-cmd CMD]

Python 3.9+ standard library only; needs ffmpeg/ffprobe. OCR and ASR are pluggable command
backends (references/backends.md). Failures print `Error [CODE]: ...` and exit non-zero.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import platform
import re
import shlex
import shutil
import statistics
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
VISION_SWIFT = HERE / "ocr_vision.swift"
DEFAULT_VOICE = HERE.parent.parent / "genius-voice" / "scripts" / "voice.py"

# Words that mark unfinished packaging or stock-footage watermarks when they appear on screen.
SCREEN_KEYWORDS = ["花字", "落版", "包装", "占位", "待替换", "TODO", "PLACEHOLDER", "【", "】",
                   "光厂", "新片场", "视觉中国", "摄图", "包图", "千图", "图虫", "Shutterstock",
                   "Getty", "iStock", "Pond5", "Envato", "Storyblocks", "VJshi", "VJ师", "素材", "样片", "水印",
                   "SAMPLE", "PREVIEW"]

EXIT_CODES = {"INPUT_NOT_FOUND": 3, "DEPENDENCY_MISSING": 5, "BACKEND_FAILED": 6, "BAD_ARGUMENT": 2}


class QCError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def log(msg: str) -> None:
    print(f"[genius-video-qc] {msg}", file=sys.stderr, flush=True)


def tc(sec: float) -> str:
    sec = max(0.0, sec)
    m, s = divmod(sec, 60)
    return f"{int(m)}:{s:05.2f}"


def run(cmd: list, check: bool = True) -> subprocess.CompletedProcess:
    p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and p.returncode != 0:
        raise QCError("BACKEND_FAILED", f"{Path(cmd[0]).name} failed: {p.stderr.strip()[-400:]}")
    return p


def need(tool: str) -> str:
    path = shutil.which(tool)
    if not path:
        raise QCError("DEPENDENCY_MISSING", f"{tool} not found on PATH")
    return path


# ── Backends ─────────────────────────────────────────────────────────────

def vision_available() -> bool:
    return platform.system() == "Darwin" and shutil.which("swift") is not None


def ocr_command(arg: str | None) -> str | None:
    """Command template with {dir} and {lang}; None means no OCR backend."""
    cmd = arg or os.environ.get("QC_OCR_CMD")
    if cmd:
        return None if cmd.strip().lower() == "none" else cmd
    if vision_available():
        return f"swift {shlex.quote(str(VISION_SWIFT))} {{dir}} {{lang}}"
    return None


def asr_command(arg: str | None) -> str | None:
    """Command template with {input} and {lang}; None means no ASR backend."""
    cmd = arg or os.environ.get("QC_ASR_CMD")
    if cmd:
        return None if cmd.strip().lower() == "none" else cmd
    voice = Path(os.environ.get("QC_VOICE_SCRIPT", str(DEFAULT_VOICE)))
    if voice.exists():
        return f"{shlex.quote(sys.executable)} {shlex.quote(str(voice))} asr {{input}} --language {{lang}} --output json"
    return None


def vision_langs(lang: str) -> str:
    return {"zh": "zh-Hans,en-US", "en": "en-US", "ja": "ja-JP,en-US", "ko": "ko-KR,en-US"}.get(lang, "zh-Hans,en-US")


def split_cmd(template: str) -> list:
    return shlex.split(template, posix=os.name != "nt")


def run_ocr(template: str, image_dir: Path, lang: str) -> dict:
    cmd = [part.format(dir=str(image_dir), lang=vision_langs(lang) if "ocr_vision" in template else lang)
           for part in split_cmd(template)]
    p = run(cmd, check=False)
    if p.returncode != 0:
        raise QCError("BACKEND_FAILED", f"OCR backend failed: {p.stderr.strip()[-400:]}")
    out = {}
    for line in p.stdout.splitlines():
        line = line.strip()
        if line.startswith("{"):
            obj = json.loads(line)
            out[obj["file"]] = obj.get("lines", [])
    return out


def run_asr(template: str, audio: Path, lang: str) -> dict:
    cmd = [part.format(input=str(audio), lang=lang) for part in split_cmd(template)]
    p = run(cmd, check=False)
    if p.returncode != 0:
        raise QCError("BACKEND_FAILED", f"ASR backend failed: {p.stderr.strip()[-400:]}")
    text = p.stdout.strip()
    if text.startswith("{"):
        data = json.loads(text)
        segs = data.get("segments") or [{"start": 0, "end": 0, "text": data.get("text", "")}]
        return {"segments": segs, "text": "".join(s["text"] for s in segs)}
    return {"segments": [{"start": 0, "end": 0, "text": text}], "text": text}


# ── Probe & audio ────────────────────────────────────────────────────────

def probe(video: Path) -> dict:
    p = run([need("ffprobe"), "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)])
    data = json.loads(p.stdout)
    v = next((s for s in data["streams"] if s["codec_type"] == "video" and s.get("disposition", {}).get("attached_pic") != 1), {})
    a = next((s for s in data["streams"] if s["codec_type"] == "audio"), {})
    num, den = (v.get("avg_frame_rate") or "0/1").split("/")
    return {
        "file": str(video), "size_mb": round(int(data["format"].get("size", 0)) / 1e6, 1),
        "duration": float(data["format"]["duration"]),
        "width": v.get("width"), "height": v.get("height"),
        "fps": round(float(num) / float(den), 3) if float(den) else None,
        "vcodec": v.get("codec_name"), "acodec": a.get("codec_name"),
        "sample_rate": int(a["sample_rate"]) if a.get("sample_rate") else None,
        "channels": a.get("channels"),
        "bitrate_kbps": round(int(data["format"].get("bit_rate", 0)) / 1000),
    }


def merge_seconds(secs: list, gap: int = 1) -> list:
    ranges = []
    for s in sorted(secs):
        if ranges and s - ranges[-1][1] <= gap:
            ranges[-1][1] = s
        else:
            ranges.append([s, s])
    return [[a, b + 1] for a, b in ranges]


def audio_checks(video: Path, info: dict) -> dict:
    ff = need("ffmpeg")
    if not info.get("acodec"):
        return {"has_audio": False}
    # Integrated loudness, LRA and true peak (EBU R128).
    p = run([ff, "-nostats", "-i", str(video), "-vn", "-af", "ebur128=peak=true", "-f", "null", "-"], check=False)
    summary = p.stderr[p.stderr.rfind("Summary:"):]

    def grab(pattern):
        m = re.search(pattern, summary)
        return float(m.group(1)) if m else None

    res = {"has_audio": True, "integrated_lufs": grab(r"I:\s+(-?[\d.]+) LUFS"),
           "lra_lu": grab(r"LRA:\s+(-?[\d.]+) LU"), "true_peak_dbtp": grab(r"Peak:\s+(-?[\d.]+) dBFS")}

    # Per-second peak / RMS: where it hits full scale and where it jumps far above the rest.
    sr = info.get("sample_rate") or 48000
    p = run([ff, "-v", "error", "-i", str(video), "-vn", "-af",
             f"asetnsamples=n={sr},astats=metadata=1:reset=1,ametadata=print:file=-", "-f", "null", "-"])
    per_sec, cur = [], {}
    for line in p.stdout.splitlines():
        if line.startswith("frame:"):
            if cur:
                per_sec.append(cur)
            cur = {"t": float(line.split("pts_time:")[1])}
        elif "Overall.Peak_level=" in line:
            cur["peak"] = float(line.split("=")[1])
        elif "Overall.RMS_level=" in line:
            cur["rms"] = float(line.split("=")[1])
    if cur:
        per_sec.append(cur)
    res["sample_peak_dbfs"] = round(max((d.get("peak", -200) for d in per_sec), default=-200), 2)
    res["clipped_seconds"] = merge_seconds([int(d["t"]) for d in per_sec if d.get("peak", -200) >= -0.1])
    rms = [d["rms"] for d in per_sec if d.get("rms", -200) > -70]
    if rms:
        med = statistics.median(rms)
        res["rms_median_db"] = round(med, 1)
        res["loud_seconds"] = merge_seconds([int(d["t"]) for d in per_sec if d.get("rms", -200) > med + 8])

    # Dead air.
    p = run([ff, "-nostats", "-i", str(video), "-vn", "-af", "silencedetect=noise=-50dB:d=2", "-f", "null", "-"], check=False)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", p.stderr)]
    ends = [float(x) for x in re.findall(r"silence_end: (-?[\d.]+)", p.stderr)]
    res["silences"] = [[round(s, 2), round(e, 2)] for s, e in zip(starts, ends + [info["duration"]] * (len(starts) - len(ends)))]
    return res


# ── Picture ──────────────────────────────────────────────────────────────

def find_flashes(frames: list, fps: float) -> list:
    """A flash is a run of ≤0.12s that jumps away from a stable stretch and then jumps again into
    another stable stretch (stray frames at a cut, a mis-graded frame). Fades and flicker are not."""
    bounds = [0] + [i for i in range(1, len(frames)) if frames[i]["scd"] >= 10
                    or abs(frames[i]["y"] - frames[i - 1]["y"]) > 4
                    or abs(frames[i]["sat"] - frames[i - 1]["sat"]) > 3] + [len(frames)]
    runs = []
    for a, b in zip(bounds, bounds[1:]):
        seg = frames[a:b]
        runs.append({"a": a, "n": b - a, "y": statistics.mean(f["y"] for f in seg),
                     "sat": statistics.mean(f["sat"] for f in seg)})
    short, stable = max(1, round(0.12 * fps)), max(2, round(0.3 * fps))
    out = []
    for prev, cur, nxt in zip(runs, runs[1:], runs[2:]):
        if cur["n"] > short or prev["n"] < stable or nxt["n"] < stable:
            continue
        jump_in = max(abs(cur["y"] - prev["y"]) / 4, abs(cur["sat"] - prev["sat"]) / 3)
        jump_out = max(abs(nxt["y"] - cur["y"]) / 4, abs(nxt["sat"] - cur["sat"]) / 3)
        if jump_in >= 1 and jump_out >= 1:
            out.append({"start": round(frames[cur["a"]]["t"], 3), "frames": cur["n"],
                        "y_jump": round(cur["y"] - prev["y"], 1), "sat_jump": round(cur["sat"] - prev["sat"], 1)})
    return out


def picture_checks(video: Path, info: dict) -> dict:
    """One decode pass: black, freeze, scene cuts, and per-frame Y/SAT for flash detection."""
    ff = need("ffmpeg")
    chain = ("scale=320:-2,blackdetect=d=0.1:pix_th=0.10,freezedetect=n=-60dB:d=2,"
             "signalstats,scdet=threshold=10,metadata=print:file=-")
    p = run([ff, "-nostats", "-i", str(video), "-an", "-vf", chain, "-f", "null", "-"], check=False)
    frames, cur = [], None
    for line in p.stdout.splitlines():
        if line.startswith("frame:"):
            cur = {"t": float(line.split("pts_time:")[1]), "y": 0.0, "sat": 0.0, "scd": 0.0}
            frames.append(cur)
        elif cur is not None:
            if line.startswith("lavfi.signalstats.YAVG="):
                cur["y"] = float(line.split("=")[1])
            elif line.startswith("lavfi.signalstats.SATAVG="):
                cur["sat"] = float(line.split("=")[1])
            elif line.startswith("lavfi.scd.score="):
                cur["scd"] = float(line.split("=")[1])
    if not frames:
        raise QCError("BACKEND_FAILED", f"video decode produced no frames: {p.stderr.strip()[-300:]}")

    black = [[round(float(a), 2), round(float(b), 2)] for a, b in
             re.findall(r"black_start:(-?[\d.]+) black_end:(-?[\d.]+)", p.stderr)]
    fs = [float(x) for x in re.findall(r"freeze_start: (-?[\d.]+)", p.stderr)]
    fe = [float(x) for x in re.findall(r"freeze_end: (-?[\d.]+)", p.stderr)]
    freezes = [[round(s, 2), round(e, 2)] for s, e in zip(fs, fe + [info["duration"]] * (len(fs) - len(fe)))]

    cuts = [f["t"] for f in frames if f["scd"] >= 10]
    flashes = find_flashes(frames, info.get("fps") or 25)
    shots = [b - a for a, b in zip([0.0] + cuts, cuts + [info["duration"]])]
    return {"black": black, "freezes": freezes, "cut_count": len(cuts), "cuts": [round(c, 2) for c in cuts],
            "avg_shot_sec": round(statistics.mean(shots), 2) if shots else None,
            "shortest_shots": sorted([[round(a, 2), round(b - a, 2)] for a, b in zip([0.0] + cuts, cuts + [info["duration"]])],
                                     key=lambda x: x[1])[:8],
            "flash_candidates": flashes[:40], "flash_total": len(flashes)}


def extract(video: Path, out_pattern: Path, vf: str, start: float | None = None, dur: float | None = None) -> None:
    cmd = [need("ffmpeg"), "-v", "error", "-y"]
    if start is not None:
        cmd += ["-ss", f"{start:.3f}"]
    cmd += ["-i", str(video)]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    run(cmd + ["-an", "-vf", vf, str(out_pattern)])


def contact_sheets(video: Path, info: dict, out: Path) -> dict:
    step = max(1.0, round(info["duration"] / 96, 1))
    sheets = out / "sheets"
    sheets.mkdir(exist_ok=True)
    extract(video, sheets / "overview_%02d.png", f"fps=1/{step},scale=320:-2,tile=4x4:padding=4:color=0x00aa00")
    files = sorted(p.name for p in sheets.glob("overview_*.png"))
    return {"step": step, "cols": 4, "per_sheet": 16, "files": files,
            "rule": f"sheet N (1-based), cell k (0-15, row-major) → time ≈ ((N-1)*16 + k) * {step}s"}


def screen_scan(video: Path, info: dict, ocr_tmpl: str, lang: str, step: float) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        extract(video, Path(tmp) / "f_%05d.png", f"fps=1/{step},scale='min(1280,iw)':-2")
        ocr = run_ocr(ocr_tmpl, Path(tmp), lang)
    hits = []
    for name, lines in sorted(ocr.items()):
        t = (int(re.search(r"(\d+)", name).group(1)) - 1) * step
        text = " ".join(l["t"] for l in lines)
        found = [k for k in SCREEN_KEYWORDS if k.lower() in text.lower()]
        if found:
            hits.append({"t": round(t, 1), "keywords": found, "text": text[:160]})
    return {"step": step, "frames": len(ocr), "hits": hits}


# ── Subtitles ────────────────────────────────────────────────────────────

PUNCT = re.compile(r"[\s\W_]+", re.UNICODE)


def norm(s: str) -> str:
    return PUNCT.sub("", s)


def parse_band(band: str) -> tuple:
    try:
        a, b = (float(x) for x in band.split(":"))
        assert 0 <= a < b <= 1
        return a, b
    except Exception:
        raise QCError("BAD_ARGUMENT", f"--band must look like 0.80:0.94, got {band!r}")


def read_subtitles(video: Path, info: dict, ocr_tmpl: str, lang: str, band: tuple, step: float) -> dict:
    a, b = band
    vf = f"fps=1/{step},crop=iw:ih*{b - a:.4f}:0:ih*{a:.4f}"
    with tempfile.TemporaryDirectory() as tmp:
        extract(video, Path(tmp) / "s_%05d.png", vf)
        ocr = run_ocr(ocr_tmpl, Path(tmp), lang)
    # Subtitle lines are centred, confidently read, and share one font size; vest logos,
    # infographics and background posts in the band are not.
    raw = []
    for name, lines in sorted(ocr.items()):
        t = (int(re.search(r"(\d+)", name).group(1)) - 1) * step
        raw.append((t, [l for l in lines if abs(l["cx"] - 0.5) <= 0.3 and l.get("c", 1) >= 0.5]))
    heights = [l["h"] for _, ls in raw for l in ls]
    med_h = statistics.median(heights) if heights else 0
    samples = []
    for t, lines in raw:
        keep = sorted((l for l in lines if 0.7 * med_h <= l["h"] <= 1.4 * med_h), key=lambda l: l["cy"])
        samples.append((t, " / ".join(l["t"].strip() for l in keep)))
    cues = []
    for t, text in samples:
        key = norm(text)
        last = cues[-1] if cues else None
        # A sample or two lost to OCR inside one subtitle must not split it into two cues.
        if key and last and last["end"] >= t - 2 * step - 1e-6 \
                and difflib.SequenceMatcher(None, last["key"], key).ratio() >= 0.8:
            last["end"] = t + step
            last["variants"][text] += 1
        elif key:
            cues.append({"start": t, "end": t + step, "key": key, "variants": Counter({text: 1})})
    out = []
    for c in cues:
        cue = {"start": round(c["start"], 2), "end": round(c["end"], 2), "text": c["variants"].most_common(1)[0][0],
               "samples": sum(c["variants"].values())}
        if len({norm(v) for v in c["variants"]}) > 1:
            cue["variants"] = [v for v, _ in c["variants"].most_common()]
        out.append(cue)
    return {"band": list(band), "step": step, "cues": out}


def write_srt(cues: list, path: Path) -> None:
    def srt_t(s):
        ms = int(round(s * 1000))
        h, ms = divmod(ms, 3600000)
        m, ms = divmod(ms, 60000)
        sec, ms = divmod(ms, 1000)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"
    path.write_text("".join(f"{i}\n{srt_t(c['start'])} --> {srt_t(c['end'])}\n{c['text']}\n\n"
                            for i, c in enumerate(cues, 1)), encoding="utf-8")


def lint_subtitles(cues: list) -> list:
    issues = []
    rules = [
        (r"\s{2,}", "连续空格"),
        (r"\S\s+[的了吗呢吧啊着过]", "助词前多余空格"),
        (r"\d,\d{3}", "数字用了千分位逗号"),
    ]
    for c in cues:
        for pat, label in rules:
            if re.search(pat, c["text"]):
                issues.append({"t": c["start"], "type": label, "text": c["text"]})
    spaced = [c for c in cues if re.search(r"[\u4e00-\u9fff] [A-Za-z0-9]|[A-Za-z0-9] [\u4e00-\u9fff]", c["text"])]
    tight = [c for c in cues if re.search(r"[\u4e00-\u9fff][A-Za-z0-9]|[A-Za-z0-9][\u4e00-\u9fff]", c["text"])]
    if spaced and tight:
        for c in spaced[:5]:
            issues.append({"t": c["start"], "type": "中英文/数字间空格不统一（多数不加空格）" if len(tight) > len(spaced)
                           else "中英文/数字间空格不统一", "text": c["text"]})
    punct = [c for c in cues if re.search(r"[，。！？；：]", c["text"])]
    if punct and len(punct) < 0.2 * len(cues):
        for c in punct[:5]:
            issues.append({"t": c["start"], "type": "个别字幕带标点（多数不带）", "text": c["text"]})
    return issues


NUMERALS = set("0123456789零一二三四五六七八九十百千万亿两")


def _concat(texts: list) -> tuple:
    keys = [norm(t) for t in texts]
    owner = [i for i, k in enumerate(keys) for _ in k]
    return "".join(keys), owner


def compare_subs_asr(cues: list, asr_text: str) -> list:
    """Character diff of all subtitles against the transcript, ranked by how likely it is a typo.

    A real typo reads the same in every OCR sample of its cue; OCR misreads over busy backgrounds
    vary between samples. So each cue first takes the OCR variant closest to what was heard, and
    differences inside cues whose samples disagree are capped at medium.
    """
    A = norm(asr_text)
    texts = [c["text"] for c in cues]
    S, owner = _concat(texts)
    if not S or not A:
        return []
    span = {}
    for a, b, size in difflib.SequenceMatcher(None, S, A, autojunk=False).get_matching_blocks():
        for k in range(size):
            lo, hi = span.get(owner[a + k], (b + k, b + k))
            span[owner[a + k]] = (min(lo, b + k), max(hi, b + k))
    for i, c in enumerate(cues):
        if c.get("variants") and i in span:
            window = A[max(0, span[i][0] - 4):span[i][1] + 5]
            texts[i] = max(c["variants"], key=lambda v: difflib.SequenceMatcher(None, norm(v), window).ratio())
    S, owner = _concat(texts)

    items = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, S, A, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        sub, heard = S[i1:i2], A[j1:j2]
        idx = owner[min(i1, len(owner) - 1)]
        if (set(sub) & NUMERALS) and (set(heard) & NUMERALS):
            level = "low"     # 2,600 vs 两千六百
        elif op == "replace" and len(sub) == len(heard) and len(sub) <= 4:
            level = "high"    # same-length swap: homophone, wrong term, wrong character
        elif op == "insert" and len(heard) <= 2:
            level = "low"     # subtitle trimmed a filler word
        else:
            level = "medium"
        unstable = bool(cues[idx].get("variants"))
        if unstable and level == "high":
            level = "medium"
        items.append({"level": level, "op": op, "t": cues[idx]["start"], "cue": texts[idx], "subtitle": sub,
                      "heard": heard, "heard_context": A[max(0, j1 - 8):j2 + 8], "ocr_unstable": unstable})

    # The same swap three or more times is a pattern (an ASR mishearing of a product name, or a
    # term written the same wrong way throughout) — report it once.
    pairs = Counter((d["subtitle"], d["heard"]) for d in items if d["op"] == "replace")
    out, seen = [], set()
    for d in items:
        key = (d["subtitle"], d["heard"])
        if d["op"] == "replace" and pairs[key] >= 3:
            if key in seen:
                continue
            seen.add(key)
            d = dict(d, level="pattern", count=pairs[key],
                     times=[x["t"] for x in items if (x["subtitle"], x["heard"]) == key])
        out.append(d)
    order = {"high": 0, "pattern": 1, "medium": 2, "low": 3}
    return sorted(out, key=lambda d: (order[d["level"]], d["t"]))


def strip_sheets(video: Path, out: Path, band: tuple) -> dict:
    """Fallback when no OCR backend: 1 strip per second, 25 per sheet, for reading by eye."""
    a, b = band
    sheets = out / "sheets"
    sheets.mkdir(exist_ok=True)
    extract(video, sheets / "subs_%02d.png",
            f"fps=1,crop=iw*0.8:ih*{b - a:.4f}:iw*0.1:ih*{a:.4f},tile=1x25:padding=4:color=0x00aa00")
    return {"files": sorted(p.name for p in sheets.glob("subs_*.png")),
            "rule": "sheet N (1-based), row k (0-24) → second (N-1)*25 + k"}


# ── Report ───────────────────────────────────────────────────────────────

def ranges_tc(rs: list) -> str:
    return "、".join(f"{tc(a)}–{tc(b)}" for a, b in rs) or "无"


def write_report(r: dict, path: Path) -> None:
    i, au, pic = r["probe"], r.get("audio", {}), r.get("picture", {})
    L = [f"# 成片质检数据：{Path(i['file']).name}", "",
         "> 由 genius-video-qc 自动测量。结论需按 SKILL.md 流程人工复核后再交付。", "",
         "## 基本信息", "",
         f"- 时长 {tc(i['duration'])}（{i['duration']:.2f}s），{i['width']}×{i['height']}，{i['fps']} fps，"
         f"{i['vcodec']}/{i['acodec']}，{i['bitrate_kbps']} kbps，{i['size_mb']} MB"]
    if pic:
        L += ["", "## 画面", "",
              f"- 切点 {pic['cut_count']} 个，平均镜头 {pic['avg_shot_sec']}s",
              f"- 黑场（≥0.1s）：{ranges_tc(pic['black'])}",
              f"- 定格（≥2s 完全静止）：{ranges_tc(pic['freezes'])}",
              f"- 疑似闪帧 / 夹帧：{pic['flash_total']} 处" + ("（只列前 40）" if pic["flash_total"] > 40 else "")]
        L += [f"  - {tc(f['start'])} 起 {f['frames']} 帧（亮度 {f['y_jump']:+}，饱和度 {f['sat_jump']:+}）"
              for f in pic["flash_candidates"]]
    if "screen_scan" in r:
        s = r["screen_scan"]
        L += ["", f"## 屏幕文字扫描（每 {s['step']}s 一帧，共 {s['frames']} 帧）", "",
              "命中占位或水印关键词的画面：" + ("无" if not s["hits"] else "")]
        L += [f"- {tc(h['t'])}：{'、'.join(h['keywords'])} ｜ {h['text']}" for h in s["hits"]]
    if "sheets" in r:
        L += ["", "## 概览拼图（必须逐张看）", "", f"- 规则：{r['sheets']['rule']}"]
        L += [f"- sheets/{f}" for f in r["sheets"]["files"]]
    if "subtitles" in r:
        sub = r["subtitles"]
        L += ["", "## 字幕", "", f"- OCR 读出 {len(sub['cues'])} 条，见 subs.srt（band {sub['band']}，每 {sub['step']}s 取样）"]
        short = [c for c in sub["cues"] if c["end"] - c["start"] < 1.0]
        L += [f"- 短于 1 秒的字幕 {len(short)} 条（取样精度 ±{sub['step']}s）："]
        L += [f"  - {tc(c['start'])} {c['text']}" for c in short[:15]]
        L += ["", "### 格式问题", ""] + ([f"- {tc(x['t'])} {x['type']}：{x['text']}" for x in r["lint"]] or ["- 无"])
    if "strip_sheets" in r:
        L += ["", "## 字幕条拼图（无 OCR 后端，需看图读）", "", f"- 规则：{r['strip_sheets']['rule']}"]
        L += [f"- sheets/{f}" for f in r["strip_sheets"]["files"]]
    if "diff" in r:
        L += ["", "## 字幕 ↔ 原声差异", "",
              "high = 等长替换（最像错字）；pattern = 同一替换反复出现（多为 ASR 固定误听型号/术语，也可能是全片统一写错）；"
              "medium = 增删较多或 OCR 读数不稳；low = 数字写法或省略语气词。ASR 也会出错，high/pattern/medium 都要复核。", ""]
        for d in r["diff"]:
            if d["level"] == "low":
                continue
            where = (f"{d['count']} 处：" + "、".join(tc(t) for t in d["times"][:6])) if d["level"] == "pattern" else tc(d["t"])
            note = "；OCR 各次读数不一致" if d.get("ocr_unstable") else ""
            L.append(f"- [{d['level']}] {where} 字幕「{d['cue']}」：字幕 `{d['subtitle'] or '∅'}` ↔ 原声 `{d['heard'] or '∅'}`"
                     f"（原声上下文：{d['heard_context']}{note}）")
        low = sum(1 for d in r["diff"] if d["level"] == "low")
        L.append(f"- 另有 low 级差异 {low} 处，见 report.json")
    if au.get("has_audio"):
        L += ["", "## 音频", "",
              f"- 积分响度 {au['integrated_lufs']} LUFS，响度范围 {au['lra_lu']} LU，真峰值 {au['true_peak_dbtp']} dBTP",
              f"- 最大采样峰值 {au['sample_peak_dbfs']} dBFS；贴满刻度（峰值 ≥ -0.1 dBFS）的秒段：{ranges_tc(au['clipped_seconds'])}",
              f"- 明显偏响（比中位 RMS {au.get('rms_median_db')} dB 高 8 dB 以上）：{ranges_tc(au.get('loud_seconds', []))}",
              f"- 静音 ≥2s：{ranges_tc(au['silences'])}"]
    elif au:
        L += ["", "## 音频", "", "- 无音轨"]
    for k, v in r.get("skipped", {}).items():
        L += ["", f"> 跳过 {k}：{v}"]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")


def cmd_run(args) -> None:
    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        raise QCError("INPUT_NOT_FOUND", f"{video} does not exist")
    out = Path(args.out).expanduser().resolve() if args.out else Path.cwd() / f"{video.stem}-qc"
    out.mkdir(parents=True, exist_ok=True)
    skip = {s.strip() for s in (args.skip or "").split(",") if s.strip()}
    band = parse_band(args.band)
    r = {"probe": probe(video), "skipped": {}}
    log(f"probe ok: {r['probe']['duration']:.1f}s → {out}")

    log("audio checks…")
    r["audio"] = audio_checks(video, r["probe"])
    log("picture checks (one decode pass)…")
    r["picture"] = picture_checks(video, r["probe"])
    if "sheets" not in skip:
        r["sheets"] = contact_sheets(video, r["probe"], out)

    ocr_tmpl = None if "ocr" in skip else ocr_command(args.ocr_cmd)
    if ocr_tmpl:
        if "scan" not in skip:
            log("screen text scan…")
            r["screen_scan"] = screen_scan(video, r["probe"], ocr_tmpl, args.lang, args.scan_step)
        log("reading subtitles…")
        r["subtitles"] = read_subtitles(video, r["probe"], ocr_tmpl, args.lang, band, args.sub_step)
        write_srt(r["subtitles"]["cues"], out / "subs.srt")
        r["lint"] = lint_subtitles(r["subtitles"]["cues"])
    else:
        r["skipped"]["ocr"] = "no OCR backend (not macOS, or --ocr-cmd none); built subtitle strip sheets instead"
        r["strip_sheets"] = strip_sheets(video, out, band)

    asr_tmpl = None if "asr" in skip else asr_command(args.asr_cmd)
    cached = out / "asr.json"
    if asr_tmpl and r["probe"].get("acodec"):
        if cached.exists():
            log(f"reusing {cached.name} (delete it to transcribe again)")
            r["asr"] = json.loads(cached.read_text(encoding="utf-8"))
        else:
            log("transcribing (ASR backend)…")
            audio = out / "audio.mp3"
            run([need("ffmpeg"), "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(audio)])
            r["asr"] = run_asr(asr_tmpl, audio, args.lang)
            cached.write_text(json.dumps(r["asr"], ensure_ascii=False, indent=1), encoding="utf-8")
        (out / "transcript.txt").write_text(r["asr"]["text"], encoding="utf-8")
        if "subtitles" in r:
            r["diff"] = compare_subs_asr(r["subtitles"]["cues"], r["asr"]["text"])
    elif "asr" not in skip:
        r["skipped"]["asr"] = "no ASR backend (disabled with none, or genius-voice not found and QC_ASR_CMD unset)"

    (out / "report.json").write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    write_report(r, out / "report.md")
    print(json.dumps({"out": str(out), "report": str(out / "report.md"),
                      "flash_candidates": r["picture"]["flash_total"],
                      "subtitle_cues": len(r.get("subtitles", {}).get("cues", [])),
                      "diff_high": sum(1 for d in r.get("diff", []) if d["level"] == "high"),
                      "skipped": r["skipped"]}, ensure_ascii=False))


def cmd_zoom(args) -> None:
    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        raise QCError("INPUT_NOT_FOUND", f"{video} does not exist")
    start = max(0.0, args.at - args.span / 2)
    n = max(1, round(args.span / args.step))
    cols = 1 if not args.full else 4
    rows = n if not args.full else -(-n // 4)
    if args.full:
        crop = "scale=320:-2"
    else:
        a, b = parse_band(args.band)
        crop = f"crop=iw*0.8:ih*{b - a:.4f}:iw*0.1:ih*{a:.4f}"
    out = Path(args.out).expanduser().resolve() if args.out else Path.cwd() / f"zoom_{args.at:.2f}.png"
    extract(video, out, f"fps=1/{args.step},{crop},tile={cols}x{rows}:padding=4:color=0x00aa00",
            start=start, dur=args.span)
    print(json.dumps({"out": str(out), "times": [round(start + k * args.step, 3) for k in range(n)],
                      "layout": f"{cols} col × {rows} row, row-major"}, ensure_ascii=False))


def cmd_recheck(args) -> None:
    video = Path(args.video).expanduser().resolve()
    if not video.exists():
        raise QCError("INPUT_NOT_FOUND", f"{video} does not exist")
    tmpl = asr_command(args.asr_cmd)
    if not tmpl:
        raise QCError("DEPENDENCY_MISSING", "no ASR backend (install genius-voice or set QC_ASR_CMD)")
    with tempfile.TemporaryDirectory() as tmp:
        clip = Path(tmp) / "clip.mp3"
        run([need("ffmpeg"), "-v", "error", "-y", "-ss", f"{args.start:.3f}", "-to", f"{args.end:.3f}", "-i", str(video),
             "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(clip)])
        res = run_asr(tmpl, clip, args.lang)
    print(json.dumps({"from": args.start, "to": args.end, "text": res["text"]}, ensure_ascii=False))


def cmd_check() -> None:
    ocr, asr = ocr_command(None), asr_command(None)
    info = {"ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe"),
            "ocr_backend": ("custom" if os.environ.get("QC_OCR_CMD") else "apple-vision") if ocr else None,
            "asr_backend": ("custom" if os.environ.get("QC_ASR_CMD") else "genius-voice") if asr else None}
    info["ok"] = bool(info["ffmpeg"] and info["ffprobe"])
    print(json.dumps(info, ensure_ascii=False, indent=2))
    if not info["ok"]:
        sys.exit(EXIT_CODES["DEPENDENCY_MISSING"])


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "--check":
        return cmd_check()
    ap = argparse.ArgumentParser(description="Genius Video QC")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("video")
    r.add_argument("--out")
    r.add_argument("--lang", default="zh")
    r.add_argument("--band", default="0.80:0.94", help="subtitle band as top:bottom fractions of height")
    r.add_argument("--sub-step", type=float, default=0.5)
    r.add_argument("--scan-step", type=float, default=2.0)
    r.add_argument("--skip", help="comma list of asr,ocr,scan,sheets")
    r.add_argument("--ocr-cmd", help="OCR command template with {dir} and {lang}; 'none' disables OCR")
    r.add_argument("--asr-cmd", help="ASR command template with {input} and {lang}; 'none' disables ASR")
    z = sub.add_parser("zoom")
    z.add_argument("video")
    z.add_argument("--at", type=float, required=True)
    z.add_argument("--span", type=float, default=0.4)
    z.add_argument("--step", type=float, default=0.02)
    z.add_argument("--band", default="0.80:0.94")
    z.add_argument("--full", action="store_true", help="whole frames instead of the subtitle band")
    z.add_argument("--out")
    c = sub.add_parser("recheck")
    c.add_argument("video")
    c.add_argument("--from", dest="start", type=float, required=True)
    c.add_argument("--to", dest="end", type=float, required=True)
    c.add_argument("--lang", default="zh")
    c.add_argument("--asr-cmd")
    args = ap.parse_args()
    {"run": cmd_run, "zoom": cmd_zoom, "recheck": cmd_recheck}[args.cmd](args)


if __name__ == "__main__":
    try:
        main()
    except QCError as e:
        print(f"Error [{e.code}]: {e}", file=sys.stderr)
        sys.exit(EXIT_CODES.get(e.code, 1))
