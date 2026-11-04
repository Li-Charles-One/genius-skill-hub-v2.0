#!/usr/bin/env python3
"""Genius Subtitle: subtitles for a finished video, driven by one file, subs.json.

  subs.py init <video> [--dir DIR] [--title T] [--layout zh,en]
  subs.py from-sound|from-asr|from-srt <dir> ...    fill events
  subs.py check <dir>                                 line length, reading speed, duration, gaps, missing text
  subs.py render <dir> [--no-burn] [--png]            SRT, ASS and a burned-in video
  subs.py --check

ASR goes through the genius-voice skill; shots come from genius-footage (or ffmpeg scene cuts). Stdlib only, plus
ffmpeg/ffprobe; Pillow is needed only to burn in when ffmpeg has no `subtitles` filter.
Failures print `Error [CODE]: ...` to stderr and exit with EXIT_CODES[CODE].
"""
from __future__ import annotations

import argparse, json, math, os, platform, re, shutil, subprocess, sys
from collections import Counter
from pathlib import Path

EXIT_CODES = {"INPUT_NOT_FOUND": 3, "UNSUPPORTED_FORMAT": 4, "DEPENDENCY_MISSING": 5,
              "PROVIDER_ERROR": 6, "TIMEOUT": 7}
CJK = ("zh", "ja", "ko")
LIMITS = {  # characters per line, characters per second (adult); Netflix Timed Text Style Guides
    "zh": {"line": 16, "cps": 9},
    "en": {"line": 42, "cps": 20},
}
MIN_DUR, MAX_DUR, GAP = 5 / 6, 7.0, 2  # seconds, seconds, empty frames between events
FONTS = {  # (family for ASS/libass, candidate files for Pillow)
    "zh": [("Source Han Sans SC Medium", ["~/Library/Fonts/SourceHanSansSC-Medium-2.otf", "/Library/Fonts/SourceHanSansSC-Medium-2.otf",
                                          "~/Library/Fonts/SourceHanSansSC-Medium.otf", "/Library/Fonts/SourceHanSansSC-Medium.otf"]),
           ("PingFang SC", ["/System/Library/Fonts/PingFang.ttc"]),
           ("Microsoft YaHei", ["C:/Windows/Fonts/msyh.ttc"]),
           ("Noto Sans CJK SC", ["/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                                 "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"])],
    "latin": [("Helvetica Neue", ["/System/Library/Fonts/HelveticaNeue.ttc"]),
              ("Arial", ["C:/Windows/Fonts/arial.ttf", "/Library/Fonts/Arial.ttf"]),
              ("DejaVu Sans", ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"])],
}


class SubsError(Exception):
    def __init__(self, code: str, msg: str):
        super().__init__(msg); self.code = code


def log(msg: str) -> None:
    print(f"[genius-subtitle] {msg}", file=sys.stderr, flush=True)


def run(cmd: list, timeout: int = 900, check: bool = True) -> subprocess.CompletedProcess:
    try:
        p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise SubsError("DEPENDENCY_MISSING", f"{cmd[0]} not found on PATH")
    except subprocess.TimeoutExpired:
        raise SubsError("TIMEOUT", f"{Path(str(cmd[0])).name} timed out after {timeout}s")
    if check and p.returncode != 0:
        raise SubsError("UNSUPPORTED_FORMAT", (p.stderr or p.stdout).strip()[-600:])
    return p


def ffmpeg(*args, timeout: int = 3600) -> subprocess.CompletedProcess:
    return run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], timeout)


def sibling(name: str, rel: str) -> Path | None:
    env = os.environ.get(f"GENIUS_{name.split('-')[-1].upper()}_DIR")
    here = Path(__file__).resolve().parents[1]
    cands = [Path(env)] if env else []
    cands += [here.parent / name, Path(__file__).parents[1].parent / name,
              Path.home() / ".claude/skills" / name, Path.home() / ".agents/skills" / name,
              Path.home() / ".config/opencode/skills" / name]
    for c in cands:
        if (c / rel).exists():
            return c / rel
    return None


# ---------- document ----------
def load(dir_: str) -> dict:
    f = Path(dir_) / "subs.json"
    if not f.exists():
        raise SubsError("INPUT_NOT_FOUND", f"{f} not found (run `subs.py init <video>` first)")
    d = json.loads(f.read_text(encoding="utf-8")); d["_dir"] = str(Path(dir_).resolve())
    return d


def save(d: dict) -> None:
    out = {k: v for k, v in d.items() if not k.startswith("_")}
    (Path(d["_dir"]) / "subs.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


def P(d: dict, rel: str) -> Path:
    return Path(d["_dir"]) / rel


def sound_project(dir_: Path) -> Path | None:
    for name in ("sound.json", "dub.json"):  # genius-sound, genius-dub 1.x
        if (dir_ / name).exists():
            return dir_ / name
    return None


def probe(video: Path) -> dict:
    p = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate,nb_frames,start_time:format=duration", "-of", "json", video])
    j = json.loads(p.stdout)
    if not j.get("streams"):
        raise SubsError("UNSUPPORTED_FORMAT", f"{video} has no video stream")
    s = j["streams"][0]; num, den = s["r_frame_rate"].split("/")
    fps = float(num) / float(den); dur = float(j["format"]["duration"])
    frames = int(s.get("nb_frames") or round(dur * fps))
    # frame n shows at n / fps + start: subtitle times carry the start, frame numbers do not
    return {"width": s["width"], "height": s["height"], "fps": round(fps, 3), "frames": frames,
            "duration": round(frames / fps, 3), "start": round(float(s.get("start_time") or 0), 6)}


def letterbox(video: Path, dur: float, h: int) -> dict:
    seen = Counter()
    for k in range(1, 6):
        p = run(["ffmpeg", "-hide_banner", "-ss", f"{dur * k / 6:.2f}", "-i", video, "-t", "1",
                 "-vf", "cropdetect=24:2:0", "-f", "null", "-"], check=False)
        for m in re.findall(r"crop=\d+:(\d+):\d+:(\d+)", p.stderr):
            seen[(int(m[0]), int(m[1]))] += 1
    if not seen:
        return {"top": 0, "bottom": h - 1}
    ch, y = seen.most_common(1)[0][0]
    return {"top": y, "bottom": y + ch - 1}


def video_of(d: dict) -> Path:
    return P(d, d["video"])


def cuts(d: dict) -> list[int]:
    """Shot starts: a footage brief next to the video or in a sound project, else genius-footage, else ffmpeg."""
    v = video_of(d)
    for fj in (v.with_suffix(".footage.json"), P(d, "src/clip.footage.json")):
        if fj.exists():
            return sorted({s["first"] for s in json.loads(fj.read_text())["shots"]} - {0})
    cache = P(d, "work/cuts.json")
    if cache.exists():
        return json.loads(cache.read_text())
    m = sibling("genius-footage", "scripts/measure.py")
    if m:
        res = json.loads(run([sys.executable, m, v, "--output", "json"], 1800).stdout)["shots"]
        out = sorted({s["first"] for s in res} - {0})
    else:
        p = run(["ffmpeg", "-hide_banner", "-i", v, "-vf", "select='gt(scene,0.25)',showinfo", "-f", "null", "-"], check=False)
        out = sorted({round(float(t) * d["info"]["fps"]) for t in re.findall(r"pts_time:([\d.]+)", p.stderr)} - {0})
    cache.parent.mkdir(parents=True, exist_ok=True); cache.write_text(json.dumps(out))
    return out


def slug(d: dict) -> str:
    return re.sub(r"[^\w\-]+", "_", d["title"]).strip("_") or "subs"


# ---------- text ----------
def toks(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+|[\u4e00-\u9fff]", s.lower())


def zh_norm(s: str) -> str:
    """Simplified Chinese subtitle rules: no commas or full stops (one space instead), enumeration commas only
    inside a line, ellipsis as U+2026; keep ？ ！."""
    s = s.strip().replace("...", "…")
    s = re.sub(r"[，,；;]\s*", " ", s)
    s = re.sub(r"[。．]+(?=.)\s*", " ", s)
    s = re.sub(r"[。．.、\s]+$", "", s)
    return re.sub(r" {2,}", " ", s).strip()


def norm(lang: str, s: str) -> str:
    return zh_norm(s) if lang == "zh" else s.strip()


def length(lang: str, s: str) -> int:
    return len(s.replace(" ", "")) if lang in CJK else len(s)


def lang_of(text: str) -> str:
    return "zh" if re.search(r"[\u4e00-\u9fff]", text) else "en"


# ---------- timing ----------
def fit(raw: list[dict], cut_list: list[int], fps: float) -> list[dict]:
    """In on the speech start, out 0.3s after it ends (at least 5/6s); both snap to a nearby shot change."""
    near, far, short = round(0.27 * fps), round(0.4 * fps), math.ceil(MIN_DUR * fps)
    out = []
    for e in raw:
        f0 = e["in"]
        for k in cut_list:  # start on a shot change a few frames away
            if 0 < k - f0 <= near or 0 < f0 - k <= near:
                f0 = k; break
        f1 = max(f0 + short, e["end"] + round(0.3 * fps))
        for k in cut_list:  # end on the frame before a nearby cut, never below the minimum duration
            if (0 < f1 - k <= far or 0 < k - f1 <= near) and k - 1 - f0 >= short:
                f1 = k - 1; break
        out.append({"id": e["id"], "in": int(f0), "out": int(f1), "text": e["text"]})
    return out


def settle(d: dict, ev: list[dict]) -> list[dict]:
    """Sort, keep GAP empty frames between events, stay inside the picture."""
    ev.sort(key=lambda e: e["in"]); last = d["info"]["frames"] - 1
    for e, n in zip(ev, ev[1:]):
        if e["out"] > n["in"] - GAP - 1:
            e["out"] = max(e["in"], n["in"] - GAP - 1)
    for e in ev:
        e["out"] = min(e["out"], last)
    return ev


# ---------- commands ----------
def cmd_init(a) -> None:
    video = Path(a.video).expanduser().resolve()
    if not video.exists():
        raise SubsError("INPUT_NOT_FOUND", f"{video} not found")
    dir_ = Path(a.dir).expanduser().resolve() if a.dir else video.parent / f"{video.stem}-subs"
    if (dir_ / "subs.json").exists() and not a.force:
        raise SubsError("UNSUPPORTED_FORMAT", f"{dir_ / 'subs.json'} exists (use --force to overwrite)")
    dir_.mkdir(parents=True, exist_ok=True)
    info = probe(video); sp = sound_project(dir_)
    title = a.title or (json.loads(sp.read_text(encoding="utf-8"))["title"] if sp else video.stem)
    rel = os.path.relpath(video, dir_) if video.is_relative_to(dir_) else str(video)
    d = {"title": title, "video": rel, "info": info, "picture": letterbox(video, info["duration"], info["height"]),
         "layout": a.layout.split(","), "source": None, "events": [], "notes": [], "_dir": str(dir_)}
    save(d)
    print(json.dumps({"dir": str(dir_), "video": rel, "info": info, "picture": d["picture"], "layout": d["layout"],
                      "sound_project": sp.name if sp else None}, ensure_ascii=False, indent=1))


def cmd_from_sound(a) -> None:
    d = load(a.dir); fps = d["info"]["fps"]
    sp = sound_project(Path(a.project).expanduser() if a.project else Path(d["_dir"]))
    if not sp:
        raise SubsError("INPUT_NOT_FOUND", "no sound.json / dub.json here (pass --project <genius-sound project>)")
    s = json.loads(sp.read_text(encoding="utf-8"))
    if abs(s["video"]["fps"] - fps) > 0.01:
        raise SubsError("UNSUPPORTED_FORMAT", f"frame rates differ: project {s['video']['fps']} vs video {fps}")
    fixed, raw = [], []
    for c in s["cues"]:
        if not c.get("line") or c.get("no_sub") or c.get("kind", "voice") not in ("voice", "narration"):
            continue
        if c.get("split_subs"):  # one take, several subtitle events
            fixed += [{"id": f"{c['id']}.{k + 1}", "in": int(x["sub"][0]), "out": int(x["sub"][1]), "text": x["text"]}
                      for k, x in enumerate(c["split_subs"])]
            continue
        text = {c.get("lang") or s["language"]: c["line"], **c.get("sub_text", {})}
        if c.get("sub"):
            fixed.append({"id": c["id"], "in": int(c["sub"][0]), "out": int(c["sub"][1]), "text": text})
            continue
        f0 = c["window"][0] if c.get("window") else round(float(c["at"]) * fps)
        end = c["window"][1] if c.get("window") else f0 + round(0.35 * len(toks(c["line"])) * fps)
        raw.append({"id": c["id"], "in": f0, "end": end, "text": text})
    d["events"] = settle(d, fixed + fit(raw, cuts(d), fps)); d["source"] = f"sound:{sp.name}"; save(d)
    print(json.dumps({"events": len(d["events"]), "from": str(sp)}, ensure_ascii=False))


def halve(lang: str, s: str, maxc: int) -> list[str]:
    """Split a clause that is still too long at the space (or character) nearest its middle."""
    if length(lang, s) <= maxc:
        return [s]
    mid = len(s) // 2
    spaces = [i for i, ch in enumerate(s) if ch == " "]
    i = min(spaces, key=lambda k: abs(k - mid)) if spaces else mid
    return halve(lang, s[:i].strip(), maxc) + halve(lang, s[i:].strip(), maxc)


def chunk(seg: dict, lang: str, maxc: int) -> list[tuple[str, float, float]]:
    """One ASR utterance → subtitle-sized pieces, timed from the word timestamps (or proportionally)."""
    text = seg["text"].strip()
    clauses = [c for c in re.split(r"(?<=[，。！？；、,.!?;…])\s*", text) if c.strip()]
    pieces, cur = [], ""
    for c in clauses:
        cand = (cur + ("" if lang in CJK else " ") + c).strip() if cur else c
        if cur and length(lang, norm(lang, cand)) > maxc:
            pieces.append(cur); cur = c
        else:
            cur = cand
    if cur:
        pieces.append(cur)
    pieces = [x for p in pieces for x in halve(lang, p, maxc)]
    counts = [max(len(toks(p)), 1) for p in pieces]
    words = seg.get("words") or []
    flat = [w for w in words for _ in range(max(len(toks(w["text"])), 1))]
    out, k = [], 0
    if words and len(flat) == sum(counts):
        for p, n in zip(pieces, counts):
            out.append((p, flat[k]["start"], flat[k + n - 1]["end"])); k += n
    else:  # tokenisation differs from the words: spread by token count
        t0, span, total = seg["start"], seg["end"] - seg["start"], sum(counts)
        for p, n in zip(pieces, counts):
            out.append((p, t0 + span * k / total, t0 + span * (k + n) / total)); k += n
    return out


def cmd_from_asr(a) -> None:
    d = load(a.dir); fps = d["info"]["fps"]
    vp = sibling("genius-voice", "scripts/voice.py")
    if not vp:
        raise SubsError("DEPENDENCY_MISSING", "genius-voice skill not found (set GENIUS_VOICE_DIR)")
    out = P(d, "work/asr.json"); out.parent.mkdir(parents=True, exist_ok=True)
    p = run([sys.executable, vp, "asr", video_of(d), "--language", a.language, "--output", "json", "--out", out], 1800, check=False)
    if p.returncode != 0 or not out.exists():
        raise SubsError("PROVIDER_ERROR", (p.stderr.strip().splitlines() or ["asr failed"])[-1])
    segs = json.loads(out.read_text(encoding="utf-8"))["segments"]
    raw = []
    for i, seg in enumerate(segs, 1):
        lang = a.language if a.language in LIMITS else lang_of(seg["text"])
        maxc = LIMITS.get(lang, LIMITS["en"])["line"]
        for j, (t, s0, s1) in enumerate(chunk(seg, lang, maxc), 1):
            raw.append({"id": f"{i:03d}.{j}", "in": round(s0 * fps), "end": round(s1 * fps), "text": {lang: t}})
    d["events"] = settle(d, fit(raw, cuts(d), fps)); d["source"] = "asr"; save(d)
    print(json.dumps({"events": len(d["events"]), "segments": len(segs), "asr": str(out)}, ensure_ascii=False))


def cmd_from_srt(a) -> None:
    d = load(a.dir); fps = d["info"]["fps"]; f = Path(a.srt).expanduser()
    if not f.exists():
        raise SubsError("INPUT_NOT_FOUND", f"{f} not found")
    raw = f.read_text(encoding="utf-8-sig").replace("\r\n", "\n")
    ev = []
    for block in re.split(r"\n\s*\n", raw.strip()):
        m = re.search(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)", block)
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = (int(x) for x in m.groups())
        t0 = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000; t1 = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
        lines = [ln.strip() for ln in block[m.end():].strip().splitlines() if ln.strip()]
        if not lines:
            continue
        if a.lang:
            text = {a.lang: ("" if a.lang in CJK else " ").join(lines)}
        else:  # a bilingual SRT carries one language per line
            text = {}
            for ln in lines:
                lg = lang_of(ln); text[lg] = (text[lg] + ("" if lg in CJK else " ") + ln) if lg in text else ln
        t0, t1 = t0 - d["info"].get("start", 0), t1 - d["info"].get("start", 0)
        ev.append({"id": f"{len(ev) + 1:03d}", "in": round(t0 * fps), "out": max(round(t1 * fps) - 1, round(t0 * fps)),
                   "text": text})
    if not ev:
        raise SubsError("UNSUPPORTED_FORMAT", f"no subtitle blocks in {f}")
    d["events"] = settle(d, ev); d["source"] = f"srt:{f.name}"; save(d)
    print(json.dumps({"events": len(ev)}, ensure_ascii=False))


def cmd_check(a) -> None:
    d = load(a.dir); fps = d["info"]["fps"]; bad = 0
    if not d["events"]:
        raise SubsError("INPUT_NOT_FOUND", "no events (run from-sound / from-asr / from-srt first)")
    for e, n in zip(d["events"], d["events"][1:] + [None]):
        dur = (e["out"] - e["in"] + 1) / fps; flags = []
        if dur < MIN_DUR - 1e-6:
            flags.append(f"SHORT {dur:.2f}s")
        if dur > MAX_DUR:
            flags.append(f"LONG {dur:.1f}s")
        if n and n["in"] - e["out"] - 1 < GAP:
            flags.append(f"GAP {n['in'] - e['out'] - 1}f")
        for lang in d["layout"]:
            t = e["text"].get(lang)
            if not t:
                flags.append(f"MISSING {lang}"); continue
            lim = LIMITS.get(lang); t = norm(lang, t); n_ch = length(lang, t)
            if lim and n_ch > lim["line"]:
                flags.append(f"LINE {lang} {n_ch}>{lim['line']}")
            if lim and n_ch / dur > lim["cps"]:
                flags.append(f"FAST {lang} {n_ch / dur:.1f}cps>{lim['cps']}")
        bad += bool(flags)
        shown = " / ".join(norm(l, e["text"][l]) for l in d["layout"] if e["text"].get(l))
        print(f"{'CHECK' if flags else 'OK   '} {e['id']:7s} f{e['in']}–f{e['out']} {dur:4.2f}s  {shown}"
              + (f"  [{'; '.join(flags)}]" if flags else ""))
    print(f"{bad} of {len(d['events'])} events flagged. LINE/FAST: shorten, split the event or condense the "
          "translation; SHORT: extend into the gap; MISSING: write the translation into events[].text.")


def pick_font(kind: str) -> tuple[str, str | None]:
    for fam, files in FONTS[kind]:
        for f in files:
            if Path(f).expanduser().exists():
                return fam, str(Path(f).expanduser())
    return FONTS[kind][0][0], None


def has_filter(name: str) -> bool:
    return bool(re.search(rf"^\s*\S+\s+{name}\s", run(["ffmpeg", "-hide_banner", "-filters"], check=False).stdout, re.M))


def cmd_render(a) -> None:
    d = load(a.dir); info, lay = d["info"], d["layout"]; fps, H, W = info["fps"], info["height"], info["width"]
    ev = [{"in": e["in"], "out": e["out"], "lines": [norm(l, e["text"][l]) for l in lay if e["text"].get(l)]}
          for e in d["events"]]
    ev = [e for e in ev if e["lines"]]
    if not ev:
        raise SubsError("INPUT_NOT_FOUND", "no event has text in the layout languages")
    big = round(H * 0.0426); small = round(H * 0.0278)
    sizes = [big] + [small] * (len(lay) - 1)
    fonts = [pick_font("zh" if l in CJK else "latin") for l in lay]
    bar = H - 1 - d["picture"]["bottom"]
    band_h = sum(s * 1.25 for s in sizes) + 10
    in_bar = bar >= band_h + 8
    bottom_margin = round((bar - band_h) / 2) if in_bar else round(H * 0.06)
    outdir = P(d, "out"); outdir.mkdir(parents=True, exist_ok=True); name = slug(d)

    t0 = info.get("start", 0)

    def ts(f, sep):  # SRT: hh:mm:ss,mmm
        ms = round((f / fps + t0) * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d}{sep}{ms % 1000:03d}"
    srt = outdir / f"{name}.srt"
    srt.write_text("".join(f"{i}\n{ts(e['in'], ',')} --> {ts(e['out'] + 1, ',')}\n" + "\n".join(e["lines"]) + "\n\n"
                           for i, e in enumerate(ev, 1)), encoding="utf-8")

    def at(f):  # ASS: h:mm:ss.cc
        cs = round((f / fps + t0) * 100)
        return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
            "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\n"
            f"Style: Sub,{fonts[0][0]},{sizes[0]},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,1.5,1,2,"
            f"60,60,{bottom_margin},1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    ass = outdir / f"{name}.ass"
    body = ""
    for e in ev:
        txt = e["lines"][0] + "".join(f"\\N{{\\fn{fonts[k][0]}\\fs{sizes[k]}}}{e['lines'][k]}" for k in range(1, len(e["lines"])))
        body += f"Dialogue: 0,{at(e['in'])},{at(e['out'] + 1)},Sub,,0,0,0,,{txt}\n"
    ass.write_text(head + body, encoding="utf-8")
    res = {"srt": str(srt), "ass": str(ass), "events": len(ev), "placement": "letterbox bar" if in_bar else "picture bottom",
           "fonts": [f[0] for f in fonts]}
    if not a.no_burn:
        src = video_of(d)
        if not src.exists():
            raise SubsError("INPUT_NOT_FOUND", f"{src} missing")
        out = outdir / f"{src.stem}_subs.mp4"
        enc = ["-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "copy"]
        if has_filter("subtitles") and not a.png:
            esc = str(ass).replace("\\", "/").replace(":", "\\:")
            ffmpeg("-i", src, "-vf", f"subtitles='{esc}'", *enc, out); res["burn"] = "libass"
        else:
            try:
                from PIL import Image, ImageDraw, ImageFont
            except ImportError:
                raise SubsError("DEPENDENCY_MISSING", "ffmpeg has no `subtitles` filter and Pillow is missing: "
                                "make a venv, `pip install Pillow`, and run subs.py with that python (SRT/ASS were written)")
            if any(f[1] is None for f in fonts):
                raise SubsError("DEPENDENCY_MISSING", f"font file not found for {[f[0] for f in fonts if f[1] is None]}")
            band = math.ceil(band_h); y0 = H - bottom_margin - band
            pngdir = P(d, "work/png"); pngdir.mkdir(parents=True, exist_ok=True)
            ft = [ImageFont.truetype(f[1], s, index=0) for f, s in zip(fonts, sizes)]
            args, chain, last = ["-i", src], [], "0:v"
            for i, e in enumerate(ev, 1):
                im = Image.new("RGBA", (W, band), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); y = 4
                for k, line in enumerate(e["lines"]):
                    hk = sizes[k] * 1.25
                    dr.text((W / 2, y + hk / 2), line, font=ft[k], fill="white", anchor="mm",
                            stroke_width=2, stroke_fill=(0, 0, 0, 200)); y += hk
                png = pngdir / f"sub_{i:03d}.png"; im.save(png); args += ["-i", png]
                chain.append(f"[{last}][{i}:v]overlay=0:{y0}:enable='between(n,{e['in']},{e['out']})'[v{i}]"); last = f"v{i}"
            ffmpeg(*args, "-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "0:a?", *enc, out)
            res["burn"] = "png overlay"
        res["video"] = str(out)
    print(json.dumps(res, ensure_ascii=False))


def selfcheck() -> None:
    res = {"ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe")}
    vp = sibling("genius-voice", "scripts/voice.py"); res["genius_voice"] = str(vp) if vp else None
    fp = sibling("genius-footage", "scripts/measure.py"); res["genius_footage"] = str(fp) if fp else None
    res["subtitles_filter"] = has_filter("subtitles") if res["ffmpeg"] else False
    try:
        import PIL  # noqa: F401
        res["pillow"] = True
    except ImportError:
        res["pillow"] = False
    res["fonts"] = {k: pick_font(k) for k in FONTS}
    res["burn_in"] = "libass" if res["subtitles_filter"] else ("png overlay" if res["pillow"] else "unavailable (SRT/ASS only)")
    res["ok"] = bool(res["ffmpeg"] and res["ffprobe"]); res["os"] = platform.system()
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if not res["ok"]:
        sys.exit(2)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="subs.py", description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="check ffmpeg, burn-in path, fonts, sibling skills")
    sp = ap.add_subparsers(dest="cmd")
    s = sp.add_parser("init"); s.add_argument("video"); s.add_argument("--dir"); s.add_argument("--title")
    s.add_argument("--layout", default="zh,en", help="languages top to bottom, e.g. zh,en or zh or en")
    s.add_argument("--force", action="store_true"); s.set_defaults(fn=cmd_init)
    s = sp.add_parser("from-sound"); s.add_argument("dir"); s.add_argument("--project", help="genius-sound project folder")
    s.set_defaults(fn=cmd_from_sound)
    s = sp.add_parser("from-asr"); s.add_argument("dir"); s.add_argument("--language", default="auto", help="auto|zh|en")
    s.set_defaults(fn=cmd_from_asr)
    s = sp.add_parser("from-srt"); s.add_argument("dir"); s.add_argument("srt"); s.add_argument("--lang", help="language of the SRT text")
    s.set_defaults(fn=cmd_from_srt)
    s = sp.add_parser("check"); s.add_argument("dir"); s.set_defaults(fn=cmd_check)
    s = sp.add_parser("render"); s.add_argument("dir"); s.add_argument("--no-burn", action="store_true")
    s.add_argument("--png", action="store_true", help="burn with PNG overlays even when libass is available")
    s.set_defaults(fn=cmd_render)
    a = ap.parse_args(argv)
    try:
        if a.check:
            selfcheck(); return 0
        if not hasattr(a, "fn"):
            ap.print_help(); return 1
        a.fn(a); return 0
    except SubsError as e:
        print(f"Error [{e.code}]: {e}", file=sys.stderr)
        return EXIT_CODES.get(e.code, 1)


if __name__ == "__main__":
    sys.exit(main())
