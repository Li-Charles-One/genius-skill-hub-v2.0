#!/usr/bin/env python3
"""Genius Dub: dub a silent (or to-be-redubbed) clip from one project file, dub.json.

Subcommands: --check, init, lipgrid, gen, check, place, mix, subs, pack, env.
Audio generation and ASR go through the genius-voice skill (scripts/voice.py); shots come from
genius-footage (<clip>.footage.json or measure.py). Stdlib only, plus ffmpeg/ffprobe; Pillow is
needed only to burn subtitles when ffmpeg has no `subtitles` filter.
Failures print `Error [CODE]: ...` to stderr and exit with EXIT_CODES[CODE].
"""
from __future__ import annotations

import argparse, json, math, os, platform, re, shutil, subprocess, sys, zipfile
from collections import Counter
from pathlib import Path

EXIT_CODES = {"INPUT_NOT_FOUND": 3, "UNSUPPORTED_FORMAT": 4, "DEPENDENCY_MISSING": 5,
              "PROVIDER_ERROR": 6, "TIMEOUT": 7}
SR = 48000
LANG_ZH = {"zh": "中文", "en": "英文", "ja": "日文", "ko": "韩文", "fr": "法文", "de": "德文", "es": "西班牙文"}
LANG_NAME = {"en": "English", "zh": "Mandarin Chinese", "ja": "Japanese", "ko": "Korean",
             "fr": "French", "de": "German", "es": "Spanish"}
FX = {  # dialogue colour presets; "giant" also pitches down (see place)
    "dry": "anull",
    "room": "aecho=0.8:0.6:45|90:0.18|0.10",
    "cave": "aecho=0.8:0.7:60|120:0.28|0.18",
    "giant": "bass=g=5:f=110,aecho=0.8:0.75:70|140:0.35|0.22",
}
DEFAULT_PITCH = {"giant": -3.0}
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


class DubError(Exception):
    def __init__(self, code: str, msg: str):
        super().__init__(msg); self.code = code


def log(msg: str) -> None:
    print(f"[genius-dub] {msg}", file=sys.stderr, flush=True)


def run(cmd: list, timeout: int = 900, check: bool = True) -> subprocess.CompletedProcess:
    try:
        p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise DubError("DEPENDENCY_MISSING", f"{cmd[0]} not found on PATH")
    except subprocess.TimeoutExpired:
        raise DubError("TIMEOUT", f"{Path(str(cmd[0])).name} timed out after {timeout}s")
    if check and p.returncode != 0:
        raise DubError("UNSUPPORTED_FORMAT", (p.stderr or p.stdout).strip()[-600:])
    return p


def ffmpeg(*args, timeout: int = 1800) -> subprocess.CompletedProcess:
    return run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", *args], timeout)


# ---------- sibling skills ----------
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


def voice_py() -> Path:
    p = sibling("genius-voice", "scripts/voice.py")
    if not p:
        raise DubError("DEPENDENCY_MISSING", "genius-voice skill not found (set GENIUS_VOICE_DIR)")
    return p


# ---------- project ----------
def load(project: Path) -> dict:
    f = Path(project) / "dub.json"
    if not f.exists():
        raise DubError("INPUT_NOT_FOUND", f"{f} not found (run `dub.py init <clip>` first)")
    d = json.loads(f.read_text(encoding="utf-8")); d["_dir"] = str(Path(project).resolve())
    return d


def save(d: dict) -> None:
    out = {k: v for k, v in d.items() if not k.startswith("_")}
    (Path(d["_dir"]) / "dub.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


def P(d: dict, rel: str) -> Path:
    return Path(d["_dir"]) / rel


def probe(clip: Path) -> dict:
    p = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", clip])
    j = json.loads(p.stdout); s = j["streams"][0]; num, den = s["r_frame_rate"].split("/")
    fps = float(num) / float(den); dur = float(j["format"]["duration"])
    frames = int(s.get("nb_frames") or round(dur * fps))
    # the picture sets the timeline: a silent track is often a few frames longer than the video
    return {"width": s["width"], "height": s["height"], "fps": round(fps, 3),
            "frames": frames, "duration": round(frames / fps, 3)}


def letterbox(clip: Path, dur: float, h: int) -> dict:
    seen = Counter()
    for k in range(1, 6):
        p = run(["ffmpeg", "-hide_banner", "-ss", f"{dur * k / 6:.2f}", "-i", clip, "-t", "1",
                 "-vf", "cropdetect=24:2:0", "-f", "null", "-"], check=False)
        for m in re.findall(r"crop=\d+:(\d+):\d+:(\d+)", p.stderr):
            seen[(int(m[0]), int(m[1]))] += 1
    if not seen:
        return {"top": 0, "bottom": h - 1}
    ch, y = seen.most_common(1)[0][0]
    return {"top": y, "bottom": y + ch - 1}


def shots(d: dict) -> list[dict]:
    """Shot list: footage brief first (model-checked cuts), then measure.py, then ffmpeg scene cuts."""
    clip = P(d, d["clip"])
    fj = clip.with_suffix(".footage.json")
    if fj.exists():
        return [{"id": s["id"], "first": s["first"], "last": s["last"]} for s in json.loads(fj.read_text())["shots"]]
    cache = P(d, "work/shots.json")
    if cache.exists():
        return json.loads(cache.read_text())
    m = sibling("genius-footage", "scripts/measure.py")
    if m:
        res = json.loads(run([sys.executable, m, clip, "--output", "json"], 1800).stdout)["shots"]
        out = [{"id": s["id"], "first": s["first"], "last": s["last"]} for s in res]
    else:
        p = run(["ffmpeg", "-hide_banner", "-i", clip, "-vf", "select='gt(scene,0.25)',showinfo",
                 "-vsync", "vfr", "-f", "null", "-"], check=False)
        cuts = [0] + [round(float(t) * d["video"]["fps"]) for t in re.findall(r"pts_time:([\d.]+)", p.stderr)]
        cuts = sorted(set(cuts)) + [d["video"]["frames"]]
        out = [{"id": f"S{i + 1:03d}", "first": a, "last": b - 1} for i, (a, b) in enumerate(zip(cuts, cuts[1:]))]
    cache.parent.mkdir(parents=True, exist_ok=True); cache.write_text(json.dumps(out))
    return out


def cmd_init(a) -> dict:
    clip = Path(a.clip).expanduser().resolve()
    if not clip.exists():
        raise DubError("INPUT_NOT_FOUND", f"{clip} not found")
    proj = Path(a.dir).expanduser().resolve() if a.dir else clip.parent / f"{clip.stem}-dub"
    if (proj / "dub.json").exists() and not a.force:
        raise DubError("UNSUPPORTED_FORMAT", f"{proj / 'dub.json'} exists (use --force to overwrite)")
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
         "subtitles": {"layout": ["zh", a.language] if a.language != "zh" else ["zh"]},
         "mix": {"lufs": -16, "tp": -1.5, "lra": 14, "vo_boost_db": 5}, "notes": [], "_dir": str(proj)}
    save(d)
    print(json.dumps({"project": str(proj), "video": v, "picture": pic,
                      "original_audio_max_db": d["original_audio_max_db"]}, ensure_ascii=False, indent=1))
    return d


# ---------- lip reading grids ----------
def cmd_lipgrid(a) -> None:
    d = load(a.project); fps = d["video"]["fps"]
    if a.shot:
        s = next((s for s in shots(d) if s["id"] == a.shot), None)
        if not s:
            raise DubError("INPUT_NOT_FOUND", f"shot {a.shot} not in shot list")
        f0, f1 = s["first"], s["last"]
    else:
        f0, f1 = (int(x) for x in a.frames.split("-"))
    crop = f"crop={a.crop}," if a.crop else ""
    n = len(range(f0, f1 + 1, a.step)); rows = math.ceil(n / a.cols)
    out = P(d, f"work/lip/{a.name or f'f{f0}-{f1}'}.jpg"); out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg("-i", P(d, d["clip"]), "-vf",
           f"select='between(n,{f0},{f1})*not(mod(n-{f0},{a.step}))',{crop}scale={a.width}:-1,"
           f"tile={a.cols}x{rows}:padding=2:color=white", "-vsync", "vfr", "-frames:v", "1", out)
    print(out)
    for r in range(rows):
        fr = [f0 + (r * a.cols + c) * a.step for c in range(a.cols) if r * a.cols + c < n]
        print(f"row {r + 1}: f{fr[0]}–f{fr[-1]}  ({fr[0] / fps:.2f}s–{fr[-1] / fps:.2f}s)")


# ---------- generation ----------
def gen_len(c: dict, fps: float) -> float:
    if c.get("gen_len"):
        return float(c["gen_len"])
    if c.get("window"):
        return max(0.8, round(1.5 * (c["window"][1] - c["window"][0] + 1) / fps + 0.1, 1))
    return round(0.6 + 0.35 * len(str(c.get("line", "")).split()), 1)


def build_prompt(d: dict, c: dict) -> tuple[str, list[str]]:
    ch = d["characters"].get(c.get("char", ""), {})
    refs = [str(P(d, ch["ref"]))] if ch.get("ref") and c.get("kind", "voice") == "voice" else []
    if c.get("prompt"):
        p = c["prompt"]
        if not re.match(r"\s*\[\s*\d", p):
            p = f"[0s:{gen_len(c, d['video']['fps'])}s] {p}"
        return p, refs if "@音频1" in p else []
    lang = LANG_NAME.get(c.get("lang") or d["language"], d["language"])
    who = f"In the exact voice of @音频1, {ch.get('name', 'the speaker')}" if refs else ch.get("voice", "A speaker")
    direction = c.get("direction", "speaks")
    return (f"[0.1s:{gen_len(c, d['video']['fps'])}s] {who} {direction} in {lang}: \"{c['line']}\" "
            "Only the clean dry voice, close microphone, no music, no ambience, no reverb."), refs


def seed_gen(prompt: str, refs: list[str], out: Path) -> dict:
    cmd = [sys.executable, voice_py(), "gen", prompt, "--out", out]
    for r in refs:
        cmd += ["--ref", r]
    p = run(cmd, 900, check=False)
    if p.returncode != 0:
        raise DubError("PROVIDER_ERROR", (p.stderr.strip().splitlines() or ["gen failed"])[-1])
    return json.loads(p.stdout.strip().splitlines()[-1])


def cmd_gen(a) -> None:
    d = load(a.project); only = set(a.only.split(",")) if a.only else None
    failed = []
    if a.beds:
        for b in d["beds"]:
            out = P(d, f"beds/{b['id']}.wav")
            if (only and b["id"] not in only) or (out.exists() and not a.force) or not b.get("prompt"):
                continue
            if a.dry_run:
                print(f"{b['id']}: {b['prompt']}\n"); continue
            try:
                print(b["id"], json.dumps(seed_gen(b["prompt"], [], out)), flush=True)
            except DubError as e:
                failed.append(b["id"]); print(b["id"], "FAILED", e, flush=True)
    else:
        groups: dict[str, dict] = {}  # one generation per take; later cues may reuse slices of it
        for c in d["cues"]:
            if c.get("line") or c.get("prompt"):
                groups.setdefault(c.get("take") or c["id"], c)
        # anchors first, so every later line of that character can use it as --ref
        order = sorted(groups.items(), key=lambda kv: (not kv[1].get("anchor"), d["cues"].index(kv[1])))
        for take, c in order:
            out = P(d, f"takes/{take}.wav")
            if (only and c["id"] not in only and take not in only) or (out.exists() and not a.force):
                continue
            ch = d["characters"].get(c.get("char", ""))
            if c.get("kind", "voice") == "voice" and ch is not None and not ch.get("ref") and not c.get("anchor"):
                log(f"{take}: {c.get('char')} has no ref yet; generating without one (mark an anchor cue)")
            prompt, refs = build_prompt(d, c)
            if a.dry_run:
                print(f"{take}  refs={[Path(r).name for r in refs]}\n  {prompt}\n"); continue
            try:
                res = seed_gen(prompt, refs, out); print(take, json.dumps(res), flush=True)
                if c.get("anchor") and ch is not None:
                    ch["ref"] = f"takes/{take}.wav"; save(d)
            except DubError as e:
                failed.append(take); print(take, "FAILED", e, flush=True)
    if failed:
        raise DubError("PROVIDER_ERROR", f"failed: {', '.join(failed)}")


# ---------- ASR checks ----------
def asr(d: dict, media: Path, tag: str) -> dict:
    out = P(d, f"work/checks/asr_{tag}.json"); out.parent.mkdir(parents=True, exist_ok=True)
    lang = d["language"] if d["language"] in ("en", "zh") else "auto"
    p = run([sys.executable, voice_py(), "asr", media, "--language", lang, "--output", "json", "--out", out], 900, check=False)
    if p.returncode != 0 or not out.exists():
        msg = (p.stderr.strip().splitlines() or ["asr failed"])[-1]
        if "NO_SPEECH" in msg:
            return {"segments": []}
        raise DubError("PROVIDER_ERROR", msg)
    return json.loads(out.read_text(encoding="utf-8"))


def toks(s: str) -> list[str]:
    s = s.lower()
    return re.findall(r"[a-z0-9']+|[\u4e00-\u9fff]", s)


def cue_start(d: dict, c: dict) -> float:
    return c["window"][0] / d["video"]["fps"] if c.get("window") else float(c.get("at", 0))


def cmd_check(a) -> None:
    d = load(a.project); spoken = [c for c in d["cues"] if c.get("line")]
    report = []
    if a.what == "takes":
        seen = set()
        for c in spoken:
            take = c.get("take") or c["id"]; f = P(d, f"takes/{take}.wav")
            if take in seen or not f.exists():
                continue
            seen.add(take)
            got = " ".join(s["text"] for s in asr(d, f, f"take_{take}")["segments"])
            want, have = set(toks(c["line"])), set(toks(got))
            score = len(want & have) / max(len(want), 1)
            report.append({"take": take, "want": c["line"], "asr": got, "match": round(score, 2)})
            print(f"{'OK   ' if score >= 0.6 else 'CHECK'} {take:12s} want: {c['line']}  |  asr: {got or '(no speech)'}")
        print("note: whispers and pitched voices are often misheard (wool→wall); listen before regenerating a CHECK")
    else:
        media = P(d, "work/stems/vo.wav") if a.what == "stem" else P(d, f"out/{slug(d)}_dub.mp4")
        if not media.exists():
            raise DubError("INPUT_NOT_FOUND", f"{media} not found (run place / mix first)")
        words = [w for s in asr(d, media, a.what)["segments"] for w in s.get("words", [])]
        for c in spoken:
            exp = cue_start(d, c); want = toks(c["line"])
            near = [w for w in words if exp - 1.0 <= w["start"] <= exp + 1.5 + 0.3 * len(want)]
            have = [t for w in near for t in toks(w["text"])]
            hit = [w for w in near if toks(w["text"])[:1] == want[:1]] or near[:1]
            got = hit[0]["start"] if hit else None
            cover = len(set(want) & set(have)) / max(len(set(want)), 1)
            delta = None if got is None else round(got - exp, 2)
            heard = " ".join(w["text"] for w in near)
            if a.what == "stem":
                lo, hi = (-0.5, 0.5) if c.get("offscreen") else (-0.12, 0.18)  # lips visible: audio early hurts more
                bad = delta is None or delta < lo or delta > hi
                tag = "CHECK" if bad else ("OK/OS" if c.get("offscreen") else "OK   ")
                print(f"{tag} {c['id']:5s} expect {exp:6.2f}s  asr {got if got is not None else '—':>6}  "
                      f"Δ {delta if delta is not None else '—':>5}  {c['line']}")
            else:
                bad = cover < 0.5
                tag = "OK   " if not bad else ("MISHEARD" if near else "MASKED")
                print(f"{tag:8s} {c['id']:5s} {exp:6.2f}s  heard {cover:4.0%}  want: {c['line']}  |  asr: {heard or '—'}")
            report.append({"id": c["id"], "expect": exp, "asr_start": got, "delta": delta, "coverage": round(cover, 2),
                           "asr": heard, "flag": bad})
        if a.what == "stem":
            print("ASR word starts run ~0.05–0.1s late; nudge `at` by -Δ only for CHECK lines (OS = offscreen, ±0.5s)")
        else:
            print("MASKED = nothing heard: raise the line or lower/mute the bed under it (beds[].mutes). "
                  "MISHEARD = speech heard but other words: usually a whisper or pitched voice; compare with `check stem`")
    P(d, f"work/checks/check_{a.what}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


# ---------- placement ----------
def max_db(f: Path, a: float | None = None, b: float | None = None) -> float:
    cut = (["-ss", str(a)] if a is not None else []) + (["-to", str(b)] if b is not None else [])
    p = run(["ffmpeg", "-hide_banner", *cut, "-i", f, "-af", "volumedetect", "-f", "null", "-"], check=False)
    m = re.search(r"max_volume: (-?[\d.]+) dB", p.stderr)
    return float(m.group(1)) if m else -91.0


def dur_of(f: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).stdout.strip())


def fx_chain(d: dict, c: dict) -> str:
    ch = d["characters"].get(c.get("char", ""), {})
    fx = c.get("fx") or ch.get("fx") or "dry"
    parts = []
    if c.get("tempo"):
        parts.append(f"atempo={float(c['tempo'])}")
    pitch = c.get("pitch", ch.get("pitch", DEFAULT_PITCH.get(fx)))
    if pitch:
        r = 2 ** (float(pitch) / 12)
        parts += [f"asetrate={SR}*{r:.4f}", f"aresample={SR}", f"atempo={1 / r:.4f}"]
    parts.append(FX.get(fx, fx))
    return ",".join(parts)


def cmd_place(a) -> None:
    d = load(a.project); fps, DUR = d["video"]["fps"], d["video"]["duration"]
    ev = [c for c in d["cues"] if "at" in c or "at_frame" in c]
    if not ev:
        raise DubError("INPUT_NOT_FOUND", "no cue has `at` / `at_frame` yet")
    inputs, parts, labels, rows = [], [f"anullsrc=r={SR}:cl=stereo:d={DUR}[base]"], ["[base]"], []
    for i, c in enumerate(ev):
        take = c.get("take") or c["id"]; f = P(d, f"takes/{take}.wav")
        if not f.exists():
            raise DubError("INPUT_NOT_FOUND", f"{f} missing (cue {c['id']})")
        a0 = float(c.get("in", 0)); b0 = float(c.get("out", dur_of(f)))
        at = float(c["at"]) if "at" in c else c["at_frame"] / fps
        default_peak = -6 if c.get("kind", "voice") == "voice" else -8
        g = float(c.get("peak", d["characters"].get(c.get("char", ""), {}).get("peak", default_peak))) - max_db(f, a0, b0)
        ms = int(round(at * 1000)); inputs += ["-i", f]
        parts.append(f"[{i}:a]atrim={a0}:{b0},asetpts=PTS-STARTPTS,aformat=sample_rates={SR}:channel_layouts=stereo,"
                     f"afade=t=in:d=0.01,afade=t=out:st={max(b0 - a0 - 0.03, 0):.3f}:d=0.03,volume={g:.2f}dB,"
                     f"{fx_chain(d, c)},apad=pad_dur=0.8,adelay={ms}|{ms}[e{i}]")
        labels.append(f"[e{i}]"); rows.append(f"{at:.3f}\t{at + b0 - a0:.3f}\t{c['id']}\t{take}\t{c.get('line', c.get('label', ''))}")
    fc = ";".join(parts) + ";" + "".join(labels) + \
        f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,atrim=0:{DUR}[out]"
    out = P(d, "work/stems/vo.wav"); out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(*inputs, "-filter_complex", fc, "-map", "[out]", "-ar", SR, "-ac", 2, out)
    P(d, "work/stems/vo_events.tsv").write_text("start\tend\tcue\ttake\tline\n" + "\n".join(rows) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(out), "events": len(ev), "seconds": round(dur_of(out), 2)}))


# ---------- mix ----------
def lufs(f: Path, a: float | None = None, b: float | None = None) -> float:
    af = (f"atrim={a or 0}:{b}," if b is not None else "") + "ebur128"
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", f, "-af", af, "-f", "null", "-"], check=False)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    return float(m[-1]) if m else -70.0


def loudness(f: Path) -> dict:
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", f, "-af", "ebur128=peak=true", "-f", "null", "-"], check=False)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr); tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)
    return {"lufs": float(i[-1]) if i else None, "true_peak": float(tp[-1]) if tp else None}


def slug(d: dict) -> str:
    return re.sub(r"[^\w\-]+", "_", d["title"]).strip("_") or "dub"


def cmd_mix(a) -> None:
    d = load(a.project); DUR = d["video"]["duration"]; m = d["mix"]
    vo = P(d, "work/stems/vo.wav")
    if not vo.exists():
        raise DubError("INPUT_NOT_FOUND", f"{vo} missing (run place first)")
    beds = [b for b in d["beds"] if P(d, f"beds/{b['id']}.wav").exists()]
    missing = [b["id"] for b in d["beds"] if b not in beds]
    if missing:
        log(f"beds not generated, skipped: {', '.join(missing)}")
    args, fc, names, ducked = ["-i", vo], [], [], []
    for i, b in enumerate(beds, start=1):
        f = P(d, f"beds/{b['id']}.wav"); t0, t1 = (b.get("trim") or [0, None])
        g = float(b.get("lufs", -30)) - lufs(f, t0, t1)
        chain = f"[{i}:a]aformat=sample_rates={SR}:channel_layouts=stereo"
        if t1 is not None:
            chain += f",atrim={t0}:{t1},asetpts=PTS-STARTPTS,afade=t=out:st={max(t1 - t0 - 0.7, 0):.2f}:d=0.7"
        chain += f",volume={g:.2f}dB"
        for s0, s1, gain in b.get("mutes", []):
            chain += f",volume={gain}:enable='between(t,{s0},{s1})'"
        ms = int(round(float(b.get("at", 0)) * 1000))
        chain += f",adelay={ms}|{ms},apad=whole_dur={DUR},atrim=0:{DUR}[b{i}]"
        args += ["-i", f]; fc.append(chain); names.append(f"b{i}")
        if b.get("duck"):
            ducked.append(f"b{i}")
    fc.append(f"[0:a]acompressor=threshold=0.05:ratio=4:attack=5:release=120:makeup=2,"
              f"volume={m.get('vo_boost_db', 5)}dB,alimiter=limit=0.95,asplit={1 + len(ducked)}[vo]"
              + "".join(f"[k{j}]" for j in range(len(ducked))))
    for j, n in enumerate(ducked):
        fc.append(f"[{n}][k{j}]sidechaincompress=threshold=0.015:ratio=8:attack=15:release=350[{n}d]")
    ins = ["[vo]"] + [f"[{n}d]" if n in ducked else f"[{n}]" for n in names]
    fc.append(f"anullsrc=r={SR}:cl=stereo:d={DUR}[base]")
    fc.append("[base]" + "".join(ins) + f"amix=inputs={len(ins) + 1}:normalize=0,"
              f"loudnorm=I={m.get('lufs', -16)}:TP={m.get('tp', -1.5)}:LRA={m.get('lra', 14)},aresample={SR},atrim=0:{DUR}[mix]")
    mix = P(d, "work/stems/mix.wav")
    ffmpeg(*args, "-filter_complex", ";".join(fc), "-map", "[mix]", "-ar", SR, "-ac", 2, mix)
    out = P(d, f"out/{slug(d)}_dub.mp4")
    ffmpeg("-i", P(d, d["clip"]), "-i", mix, "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy",
           "-c:a", "aac", "-b:a", "256k", "-shortest", out)
    res = {"out": str(out), "beds": [b["id"] for b in beds], **loudness(out)}
    d["mix"]["measured"] = {k: res[k] for k in ("lufs", "true_peak")}; save(d)
    print(json.dumps(res, ensure_ascii=False))


# ---------- subtitles ----------
def zh_norm(s: str) -> str:
    """Chinese subtitle convention: no sentence-final full stop, commas become spaces; keep ？！……"""
    s = re.sub(r"[，,、；;]\s*", " ", s.strip())
    return re.sub(r"[。．.]+$", "", s).strip()


def sub_events(d: dict) -> list[dict]:
    fps, lay = d["video"]["fps"], d["subtitles"]["layout"]
    cuts = sorted({s["first"] for s in shots(d)} - {0})
    cand = [c for c in d["cues"] if c.get("line") and not c.get("no_sub")]
    ev = []
    for c in cand:
        if c.get("split_subs"):  # one take, several subtitle events: [{"sub": [f0, f1], "text": {...}}]
            for k, s in enumerate(c["split_subs"]):
                lines = [zh_norm(s["text"][l]) if l == "zh" else s["text"][l] for l in lay if s["text"].get(l)]
                ev.append({"id": f"{c['id']}.{k + 1}", "in": int(s["sub"][0]), "out": int(s["sub"][1]), "lines": lines})
            continue
        text = {d["language"]: c["line"], **c.get("sub_text", {})}
        lines = [zh_norm(text[l]) if l == "zh" else text[l] for l in lay if text.get(l)]
        if not lines:
            continue
        if c.get("sub"):
            f0, f1 = c["sub"]
        else:
            f0 = c["window"][0] if c.get("window") else round(float(c["at"]) * fps)
            end = c["window"][1] if c.get("window") else f0 + round(0.35 * len(toks(c["line"])) * fps)
            near, far, short = round(0.27 * fps), round(0.4 * fps), round(0.8 * fps)
            for k in cuts:  # start on a shot change a few frames away
                if 0 < k - f0 <= near or 0 < f0 - k <= near:
                    f0 = k; break
            f1 = max(f0 + short, end + round(0.3 * fps))
            for k in cuts:  # end on the frame before a nearby cut, never below the minimum duration
                if (0 < f1 - k <= far or 0 < k - f1 <= near) and k - 1 - f0 >= short:
                    f1 = k - 1; break
        ev.append({"id": c["id"], "in": int(f0), "out": int(f1), "lines": lines})
    ev.sort(key=lambda e: e["in"])
    for e, n in zip(ev, ev[1:]):
        if e["out"] >= n["in"] - 1:
            e["out"] = n["in"] - 2
    return ev


def pick_font(kind: str) -> tuple[str, str | None]:
    for fam, files in FONTS[kind]:
        for f in files:
            if Path(f).expanduser().exists():
                return fam, str(Path(f).expanduser())
    return FONTS[kind][0][0], None


def has_filter(name: str) -> bool:
    return bool(re.search(rf"^\s*\S+\s+{name}\s", run(["ffmpeg", "-hide_banner", "-filters"], check=False).stdout, re.M))


def cmd_subs(a) -> None:
    d = load(a.project); fps, H, W = d["video"]["fps"], d["video"]["height"], d["video"]["width"]
    ev = sub_events(d)
    if not ev:
        raise DubError("INPUT_NOT_FOUND", "no cue has subtitle text")
    lay = d["subtitles"]["layout"]
    big = round(H * 0.0426); small = round(H * 0.0278)
    sizes = [big, small] if len(lay) > 1 else [big]
    fonts = [pick_font("zh" if l in ("zh", "ja", "ko") else "latin") for l in lay]
    bar = H - 1 - d["picture"]["bottom"]
    band_h = sum(s * 1.25 for s in sizes) + 10
    in_bar = bar >= band_h + 8
    bottom_margin = round((bar - band_h) / 2) if in_bar else round(H * 0.06)

    def ts(f, sep):
        s = f / fps
        return f"{int(s // 3600):02d}:{int(s % 3600 // 60):02d}:{int(s % 60):02d}{sep}{round((s % 1) * 1000):03d}"
    name = slug(d)
    srt = P(d, f"out/{name}.srt")
    srt.write_text("".join(f"{i}\n{ts(e['in'], ',')} --> {ts(e['out'] + 1, ',')}\n" + "\n".join(e["lines"]) + "\n\n"
                           for i, e in enumerate(ev, 1)), encoding="utf-8")

    def at(f):
        s = f / fps
        return f"{int(s // 3600)}:{int(s % 3600 // 60):02d}:{s % 60:05.2f}"
    head = (f"[Script Info]\nScriptType: v4.00+\nPlayResX: {W}\nPlayResY: {H}\nWrapStyle: 2\nScaledBorderAndShadow: yes\n\n"
            "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, "
            "Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, "
            "MarginR, MarginV, Encoding\n"
            f"Style: Sub,{fonts[0][0]},{sizes[0]},&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,0,0,0,0,100,100,0,0,1,1.5,1,2,"
            f"60,60,{bottom_margin},1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    ass = P(d, f"out/{name}.ass")
    body = ""
    for e in ev:
        txt = e["lines"][0] + "".join(f"\\N{{\\fn{fonts[k][0]}\\fs{sizes[k]}}}{e['lines'][k]}" for k in range(1, len(e["lines"])))
        body += f"Dialogue: 0,{at(e['in'])},{at(e['out'] + 1)},Sub,,0,0,0,,{txt}\n"
    ass.write_text(head + body, encoding="utf-8")
    res = {"srt": str(srt), "ass": str(ass), "events": len(ev), "placement": "letterbox bar" if in_bar else "picture bottom",
           "fonts": [f[0] for f in fonts]}
    if not a.no_burn:
        src = P(d, f"out/{name}_dub.mp4")
        if not src.exists():
            raise DubError("INPUT_NOT_FOUND", f"{src} missing (run mix first)")
        out = P(d, f"out/{name}_dub_subs.mp4")
        enc = ["-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "copy"]
        if has_filter("subtitles") and not a.png:
            esc = str(ass).replace("\\", "/").replace(":", "\\:")
            ffmpeg("-i", src, "-vf", f"subtitles='{esc}'", *enc, out); res["burn"] = "libass"
        else:
            try:
                from PIL import Image, ImageDraw, ImageFont
            except ImportError:
                raise DubError("DEPENDENCY_MISSING", "ffmpeg has no `subtitles` filter and Pillow is missing: "
                               "make a venv, `pip install Pillow`, and run dub.py with that python (SRT/ASS were written)")
            if any(f[1] is None for f in fonts):
                raise DubError("DEPENDENCY_MISSING", f"font file not found for {[f[0] for f in fonts if f[1] is None]}")
            band = math.ceil(band_h); y0 = H - bottom_margin - band
            pngdir = P(d, "work/subs"); pngdir.mkdir(parents=True, exist_ok=True)
            ft = [ImageFont.truetype(f[1], s, index=0) for f, s in zip(fonts, sizes)]
            args, chain, last = ["-i", src], [], "0:v"
            for i, e in enumerate(ev, 1):
                im = Image.new("RGBA", (W, band), (0, 0, 0, 0)); dr = ImageDraw.Draw(im); y = 4
                for k, line in enumerate(e["lines"]):
                    hk = sizes[k] * 1.25
                    dr.text((W / 2, y + hk / 2), line, font=ft[k], fill="white", anchor="mm",
                            stroke_width=2, stroke_fill=(0, 0, 0, 200)); y += hk
                png = pngdir / f"sub_{i:02d}.png"; im.save(png); args += ["-i", png]
                chain.append(f"[{last}][{i}:v]overlay=0:{y0}:enable='between(n,{e['in']},{e['out']})'[v{i}]"); last = f"v{i}"
            ffmpeg(*args, "-filter_complex", ";".join(chain), "-map", f"[{last}]", "-map", "0:a", *enc, out)
            res["burn"] = "png overlay"
        res["video"] = str(out)
    d["subtitles"]["events"] = ev; save(d)
    print(json.dumps(res, ensure_ascii=False))


# ---------- envelope ----------
def cmd_env(a) -> None:
    if not Path(a.file).exists():
        raise DubError("INPUT_NOT_FOUND", f"{a.file} not found")
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", a.file, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                             capture_output=True, timeout=600).stdout
    except FileNotFoundError:
        raise DubError("DEPENDENCY_MISSING", "ffmpeg not found on PATH")
    import array
    x = array.array("h"); x.frombytes(raw[: len(raw) // 2 * 2])
    n = int(8000 * a.window); out = []
    for i in range(0, len(x), n):
        seg = x[i:i + n]; r = math.sqrt(sum(v * v for v in seg) / max(len(seg), 1))
        out.append(f"{i / 8000:.1f}:{20 * math.log10(r / 32768) if r else -99:.0f}")
    print(" ".join(out))


# ---------- package ----------
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
    cp(P(d, f"out/{name}_dub_subs.mp4"), "01_成片/成片_配音_字幕版.mp4")
    cp(P(d, f"out/{name}_dub.mp4"), "01_成片/成片_配音_无字幕.mp4")
    cp(P(d, d["clip"]), f"02_原始素材/原始片段{Path(d['clip']).suffix}")
    for md in sorted(Path(d["_dir"]).glob("*.md")):
        cp(md, f"03_剧本与分析/{md.name}")
    clip = P(d, d["clip"])
    for ext in (".footage.md", ".footage.json"):
        cp(clip.with_suffix(ext), f"03_剧本与分析/{clip.stem}{ext}")
    cp(clip.with_suffix(".footage"), "03_剧本与分析/故事板")
    cp(P(d, "work/stems/vo.wav"), "04_分轨/对白轨_vo.wav"); cp(P(d, "work/stems/mix.wav"), "04_分轨/最终混音_mix.wav")
    for b in d["beds"]:
        cp(P(d, f"beds/{b['id']}.wav"), f"04_分轨/{b['id']}.wav")
    used = {c.get("take") or c["id"] for c in d["cues"]}
    for f in sorted(P(d, "takes").glob("*.wav")):
        cp(f, f"05_配音素材/{'已采用' if f.stem in used else '未采用'}/{f.name}")
    cp(Path(d["_dir"]) / "dub.json", "06_工程文件/dub.json")
    cp(Path(__file__).resolve(), "07_脚本工具/dub.py")
    for f in sorted(P(d, "work/checks").glob("check_*.json")):
        cp(f, f"08_校验记录/{f.name}")
    cp(P(d, "work/stems/vo_events.tsv"), "08_校验记录/对白摆位表_vo_events.tsv")
    cp(P(d, f"out/{name}.srt"), "09_字幕/字幕.srt"); cp(P(d, f"out/{name}.ass"), "09_字幕/字幕.ass")
    (root / "文件说明.md").write_text(readme(d, root), encoding="utf-8")
    z = root.with_suffix(".zip")
    with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(root.rglob("*")):
            if f.is_file() and not f.name.startswith("."):
                zf.write(f, Path(root.name) / f.relative_to(root))
    with zipfile.ZipFile(z) as zf:
        bad = zf.testzip(); n = len(zf.namelist())
    if bad:
        raise DubError("UNSUPPORTED_FORMAT", f"zip check failed at {bad}")
    print(json.dumps({"folder": str(root), "zip": str(z), "files": n, "mb": round(z.stat().st_size / 1e6, 1)}, ensure_ascii=False))


def readme(d: dict, root: Path) -> str:
    v, fps = d["video"], d["video"]["fps"]
    t = lambda f: f"{int(f / fps // 60):02d}:{f / fps % 60:06.3f}"
    chars = "\n".join(f"| {k} | {c.get('name', k)} | {c.get('voice', '—')} | {c.get('fx', 'dry')} |" for k, c in d["characters"].items())
    rows = []
    for c in d["cues"]:
        if "at" not in c and "at_frame" not in c:
            continue
        at = float(c["at"]) if "at" in c else c["at_frame"] / fps
        rows.append(f"| {c['id']} | {at:.2f}s | {d['characters'].get(c.get('char', ''), {}).get('name', c.get('char', '—'))} "
                    f"| {c.get('line') or c.get('label', '（声音）')} | {c.get('take') or c['id']} |")
    subs = "\n".join(f"| {t(e['in'])}–{t(e['out'] + 1)} | " + " / ".join(e["lines"]) + " |"
                     for e in d["subtitles"].get("events", []))
    beds = "\n".join(f"| {b['id']} | {b.get('at', 0)}s | {b.get('lufs', -30)} LUFS | {'是' if b.get('duck') else '否'} | "
                     f"{b.get('trim') or '—'} | {b.get('mutes') or '—'} |" for b in d["beds"])
    meas = d["mix"].get("measured", {})
    notes = "\n".join(f"- {n}" for n in d.get("notes", [])) or "- 无"
    return f"""# {d['title']} · 源文件包

{d.get('summary', '')}

- 片长 {v['duration']}s，{v['width']}×{v['height']}，{fps}fps；画面区域第 {d['picture']['top']}–{d['picture']['bottom']} 行
- 对白语言：{LANG_ZH.get(d['language'], d['language'])}；字幕：{' 在上，'.join(LANG_ZH.get(l, l) for l in d['subtitles']['layout'])}{' 在下' if len(d['subtitles']['layout']) > 1 else ''}
- 成片响度 {meas.get('lufs', '—')} LUFS，真峰值 {meas.get('true_peak', '—')} dBFS
- 生成：豆包 Seed Audio 1.0（genius-voice）；摆位、混音、字幕：genius-dub `dub.py`

## 目录

| 目录 | 内容 |
|---|---|
| 01_成片 | 字幕版（字幕已烧录）与无字幕版 |
| 02_原始素材 | 原片，未改动 |
| 03_剧本与分析 | 台词稿、genius-footage 素材说明书与故事板 |
| 04_分轨 | 对白轨、各环境/音效/配乐分轨、最终混音（48 kHz 立体声 WAV） |
| 05_配音素材 | 每条生成素材；已采用 = 进了成片，未采用 = 被重生成替换 |
| 06_工程文件 | dub.json：角色、台词、提示词、摆位、分轨与字幕设置，改它再重跑即可 |
| 07_脚本工具 | dub.py（genius-dub 技能脚本的副本） |
| 08_校验记录 | 对白摆位表、ASR 摆位与可懂度校验 |
| 09_字幕 | SRT（通用，每条多语一行一种）与 ASS（带样式） |

## 角色

| 代号 | 名字 | 声音 | 后期 |
|---|---|---|---|
{chars}

## 对白与声音摆位

| 编号 | 时间线位置 | 角色 | 内容 | 素材 |
|---|---|---|---|---|
{chr(10).join(rows)}

## 字幕

| 时间 | 字幕 |
|---|---|
{subs}

## 分轨

| 分轨 | 起点 | 目标响度 | 对白避让 | 裁剪 | 局部压低 [起, 止, 倍数] |
|---|---|---|---|---|---|
{beds}

## 如何重做

在原工程目录（含 dub.json）运行，需 ffmpeg 与 genius-voice 技能：

```bash
python3 dub.py place <工程目录>
python3 dub.py mix <工程目录>
python3 dub.py subs <工程目录>
```

Windows 用 `python`。改台词位置改 `cues[].at`，换说法改 `cues[].take` 后 `dub.py gen` 只补缺的素材。

## 备注与已知问题

{notes}
"""


# ---------- check ----------
def cmd_selfcheck(_a) -> None:
    res = {"ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe")}
    vp = sibling("genius-voice", "scripts/voice.py"); res["genius_voice"] = str(vp) if vp else None
    fp = sibling("genius-footage", "scripts/footage.py"); res["genius_footage"] = str(fp) if fp else None
    res["subtitles_filter"] = has_filter("subtitles") if res["ffmpeg"] else False
    try:
        import PIL  # noqa: F401
        res["pillow"] = True
    except ImportError:
        res["pillow"] = False
    res["fonts"] = {k: pick_font(k) for k in FONTS}
    res["burn_in"] = "libass" if res["subtitles_filter"] else ("png overlay" if res["pillow"] else "unavailable (SRT/ASS only)")
    res["ok"] = bool(res["ffmpeg"] and res["ffprobe"] and vp)
    res["os"] = platform.system()
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if not res["ok"]:
        sys.exit(2)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="dub.py", description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="check ffmpeg, sibling skills, Pillow, fonts")
    sp = ap.add_subparsers(dest="cmd")
    s = sp.add_parser("init"); s.add_argument("clip"); s.add_argument("--dir"); s.add_argument("--title")
    s.add_argument("--language", default="en"); s.add_argument("--force", action="store_true")
    s = sp.add_parser("lipgrid"); s.add_argument("project"); g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--shot"); g.add_argument("--frames"); s.add_argument("--crop", help="W:H:X:Y")
    s.add_argument("--step", type=int, default=1); s.add_argument("--cols", type=int, default=10)
    s.add_argument("--width", type=int, default=192); s.add_argument("--name")
    s = sp.add_parser("gen"); s.add_argument("project"); s.add_argument("--only"); s.add_argument("--beds", action="store_true")
    s.add_argument("--force", action="store_true"); s.add_argument("--dry-run", action="store_true", help="print prompts, call nothing")
    s = sp.add_parser("check"); s.add_argument("project"); s.add_argument("what", choices=["takes", "stem", "final"])
    s = sp.add_parser("place"); s.add_argument("project")
    s = sp.add_parser("mix"); s.add_argument("project")
    s = sp.add_parser("subs"); s.add_argument("project"); s.add_argument("--no-burn", action="store_true")
    s.add_argument("--png", action="store_true", help="burn with PNG overlay even when libass is available")
    s = sp.add_parser("pack"); s.add_argument("project"); s.add_argument("--dest")
    s = sp.add_parser("env"); s.add_argument("file"); s.add_argument("--window", type=float, default=1.0)
    a = ap.parse_args(argv)
    try:
        if a.check:
            cmd_selfcheck(a); return 0
        fn = {"init": cmd_init, "lipgrid": cmd_lipgrid, "gen": cmd_gen, "check": cmd_check, "place": cmd_place,
              "mix": cmd_mix, "subs": cmd_subs, "pack": cmd_pack, "env": cmd_env}.get(a.cmd)
        if not fn:
            ap.print_help(); return 1
        fn(a); return 0
    except DubError as e:
        print(f"Error [{e.code}]: {e}", file=sys.stderr)
        return EXIT_CODES.get(e.code, 1)


if __name__ == "__main__":
    sys.exit(main())
