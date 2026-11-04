"""Shared engine for genius-sound: errors, ffmpeg, the project file, shots, generation, ASR and placement.

Every module (spot, dialogue, foley, sfx, music, mix, deliver) works on one project folder described by
`sound.json` (genius-dub 1.x `dub.json` is read too). Generation and ASR go through the genius-voice skill.
"""
from __future__ import annotations

import json, math, os, re, subprocess, sys
from collections import Counter
from pathlib import Path

EXIT_CODES = {"INPUT_NOT_FOUND": 3, "UNSUPPORTED_FORMAT": 4, "DEPENDENCY_MISSING": 5,
              "PROVIDER_ERROR": 6, "TIMEOUT": 7}
SR = 48000
PROJECT_FILES = ("sound.json", "dub.json")  # dub.json: projects made by genius-dub 1.x
LANG_ZH = {"zh": "中文", "en": "英文", "ja": "日文", "ko": "韩文", "fr": "法文", "de": "德文", "es": "西班牙文"}
LANG_NAME = {"en": "English", "zh": "Mandarin Chinese", "ja": "Japanese", "ko": "Korean",
             "fr": "French", "de": "German", "es": "Spanish"}
FX = {  # dialogue colour presets; "giant" also pitches down (see fx_chain)
    "dry": "anull",
    "room": "aecho=0.8:0.6:45|90:0.18|0.10",
    "cave": "aecho=0.8:0.7:60|120:0.28|0.18",
    "giant": "bass=g=5:f=110,aecho=0.8:0.75:70|140:0.35|0.22",
}
DEFAULT_PITCH = {"giant": -3.0}
BED_LUFS = {"music": -32, "amb": -39, "sfx": -30, "foley": -30, "dialogue": None}  # None = keep the file's level
DIALOGUE_KINDS = {"voice", "narration"}


class SoundError(Exception):
    def __init__(self, code: str, msg: str):
        super().__init__(msg); self.code = code


def log(msg: str) -> None:
    print(f"[genius-sound] {msg}", file=sys.stderr, flush=True)


def run(cmd: list, timeout: int = 900, check: bool = True) -> subprocess.CompletedProcess:
    try:
        p = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise SoundError("DEPENDENCY_MISSING", f"{cmd[0]} not found on PATH")
    except subprocess.TimeoutExpired:
        raise SoundError("TIMEOUT", f"{Path(str(cmd[0])).name} timed out after {timeout}s")
    if check and p.returncode != 0:
        raise SoundError("UNSUPPORTED_FORMAT", (p.stderr or p.stdout).strip()[-600:])
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
        raise SoundError("DEPENDENCY_MISSING", "genius-voice skill not found (set GENIUS_VOICE_DIR)")
    return p


# ---------- project ----------
def load(project) -> dict:
    for name in PROJECT_FILES:
        f = Path(project) / name
        if f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
            d["_dir"], d["_file"] = str(Path(project).resolve()), name
            return d
    raise SoundError("INPUT_NOT_FOUND", f"{Path(project) / 'sound.json'} not found (run `sound.py spot init <clip>` first)")


def save(d: dict) -> None:
    out = {k: v for k, v in d.items() if not k.startswith("_")}
    (Path(d["_dir"]) / d.get("_file", "sound.json")).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")


def P(d: dict, rel: str) -> Path:
    return Path(d["_dir"]) / rel


def probe(clip: Path) -> dict:
    p = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,r_frame_rate,nb_frames:format=duration", "-of", "json", clip])
    j = json.loads(p.stdout)
    if not j.get("streams"):
        raise SoundError("UNSUPPORTED_FORMAT", f"{clip} has no video stream (genius-sound works on picture)")
    s = j["streams"][0]; num, den = s["r_frame_rate"].split("/")
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


# ---------- kinds ----------
def cue_kind(c: dict) -> str:
    """voice (lines and non-verbal efforts), narration (TTS), foley ("sound" in genius-dub 1.x projects)."""
    k = c.get("kind", "voice")
    return "foley" if k == "sound" else k


def is_effort(c: dict) -> bool:
    """A non-verbal vocal (roar, gasp, laugh): voice cue without a line. Goes into the M&E too."""
    return cue_kind(c) == "voice" and not c.get("line")


def bed_kind(b: dict) -> str:
    if b.get("kind"):
        return b["kind"]
    i = b["id"].lower()  # genius-dub 1.x beds had no kind
    return "music" if i.startswith(("bgm", "music", "score")) else "amb" if i.startswith(("amb", "bg", "room")) else "sfx"


def bed_file(d: dict, b: dict) -> Path:
    return P(d, b["file"]) if b.get("file") else P(d, f"beds/{b['id']}.wav")


def cue_at(d: dict, c: dict) -> float | None:
    if "at" in c:
        return float(c["at"])
    if "at_frame" in c:
        return c["at_frame"] / d["video"]["fps"]
    return None


# ---------- generation ----------
def gen_len(c: dict, fps: float) -> float:
    if c.get("gen_len"):
        return float(c["gen_len"])
    if c.get("window"):
        return max(0.8, round(1.5 * (c["window"][1] - c["window"][0] + 1) / fps + 0.1, 1))
    return round(0.6 + 0.35 * len(str(c.get("line", "")).split()), 1)


def build_prompt(d: dict, c: dict) -> tuple[str, list[str]]:
    ch = d["characters"].get(c.get("char", ""), {})
    refs = [str(P(d, ch["ref"]))] if ch.get("ref") and cue_kind(c) == "voice" else []
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


def tts_args(d: dict, c: dict) -> list[str]:
    """Narration voice: a MiMo preset (`tts_voice`), else a clone of the anchor take, else designed from `voice`."""
    ch = d["characters"].get(c.get("char", ""), {})
    if ch.get("tts_voice"):
        opt = ["--voice", ch["tts_voice"]]
    elif ch.get("ref"):
        opt = ["--clone", str(P(d, ch["ref"]))]
    else:
        return ["--design", f"{ch.get('voice', 'A calm, warm narrator.')} {c.get('direction', '')}".strip()]
    return opt + (["--style", c["direction"]] if c.get("direction") else [])


def voice_call(args: list, out: Path) -> dict:
    p = run([sys.executable, voice_py(), *args, "--out", out], 900, check=False)
    if p.returncode != 0:
        raise SoundError("PROVIDER_ERROR", (p.stderr.strip().splitlines() or ["genius-voice failed"])[-1])
    return json.loads(p.stdout.strip().splitlines()[-1])


def gen_cues(d: dict, kinds: set, a) -> None:
    """One generation per take; anchors first so later lines of that character can use them as reference."""
    only = set(a.only.split(",")) if a.only else None
    groups: dict[str, dict] = {}
    for c in d["cues"]:
        if cue_kind(c) in kinds and (c.get("line") or c.get("prompt")):
            groups.setdefault(c.get("take") or c["id"], c)
    if not groups:
        raise SoundError("INPUT_NOT_FOUND", f"no {'/'.join(sorted(kinds))} cue with a line or prompt")
    order = sorted(groups.items(), key=lambda kv: (not kv[1].get("anchor"), d["cues"].index(kv[1])))
    failed = []
    for take, c in order:
        out = P(d, f"takes/{take}.wav"); out.parent.mkdir(parents=True, exist_ok=True)
        if (only and c["id"] not in only and take not in only) or (out.exists() and not a.force):
            continue
        ch = d["characters"].get(c.get("char", ""))
        if cue_kind(c) in DIALOGUE_KINDS and ch is not None and not (ch.get("ref") or ch.get("tts_voice") or c.get("anchor")):
            log(f"{take}: {c.get('char')} has no ref yet; generating without one (mark an anchor cue)")
        if cue_kind(c) == "narration":
            args = ["tts", c["line"], *tts_args(d, c)]
            label = " ".join(f'"{x}"' if " " in x else x for x in args[2:])
            if a.dry_run:
                print(f"{take}  tts {label}\n  {c['line']}\n"); continue
        else:
            prompt, refs = build_prompt(d, c)
            args = ["gen", prompt] + [x for r in refs for x in ("--ref", r)]
            if a.dry_run:
                print(f"{take}  refs={[Path(r).name for r in refs]}\n  {prompt}\n"); continue
        try:
            print(take, json.dumps(voice_call(args, out)), flush=True)
            if c.get("anchor") and ch is not None:
                ch["ref"] = f"takes/{take}.wav"; save(d)
        except SoundError as e:
            failed.append(take); print(take, "FAILED", e, flush=True)
    if failed:
        raise SoundError("PROVIDER_ERROR", f"failed: {', '.join(failed)}")


def gen_beds(d: dict, kinds: set, a) -> None:
    only = set(a.only.split(",")) if a.only else None
    beds = [b for b in d["beds"] if bed_kind(b) in kinds and b.get("prompt") and not b.get("file")]
    if not beds:
        raise SoundError("INPUT_NOT_FOUND", f"no {'/'.join(sorted(kinds))} bed with a prompt")
    failed = []
    for b in beds:
        out = bed_file(d, b); out.parent.mkdir(parents=True, exist_ok=True)
        if (only and b["id"] not in only) or (out.exists() and not a.force):
            continue
        if a.dry_run:
            print(f"{b['id']} ({bed_kind(b)}): {b['prompt']}\n"); continue
        try:
            print(b["id"], json.dumps(voice_call(["gen", b["prompt"]], out)), flush=True)
        except SoundError as e:
            failed.append(b["id"]); print(b["id"], "FAILED", e, flush=True)
    if failed:
        raise SoundError("PROVIDER_ERROR", f"failed: {', '.join(failed)}")


# ---------- ASR ----------
def asr(d: dict, media: Path, tag: str) -> dict:
    out = P(d, f"work/checks/asr_{tag}.json"); out.parent.mkdir(parents=True, exist_ok=True)
    lang = d["language"] if d["language"] in ("en", "zh") else "auto"
    p = run([sys.executable, voice_py(), "asr", media, "--language", lang, "--output", "json", "--out", out], 900, check=False)
    if p.returncode != 0 or not out.exists():
        msg = (p.stderr.strip().splitlines() or ["asr failed"])[-1]
        if "NO_SPEECH" in msg:
            return {"segments": []}
        raise SoundError("PROVIDER_ERROR", msg)
    return json.loads(out.read_text(encoding="utf-8"))


def toks(s: str) -> list[str]:
    return re.findall(r"[a-z0-9']+|[\u4e00-\u9fff]", s.lower())


# ---------- levels ----------
def max_db(f: Path, a: float | None = None, b: float | None = None) -> float:
    cut = (["-ss", str(a)] if a is not None else []) + (["-to", str(b)] if b is not None else [])
    p = run(["ffmpeg", "-hide_banner", *cut, "-i", f, "-af", "volumedetect", "-f", "null", "-"], check=False)
    m = re.search(r"max_volume: (-?[\d.]+) dB", p.stderr)
    return float(m.group(1)) if m else -91.0


def dur_of(f: Path) -> float:
    return float(run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f]).stdout.strip())


def lufs(f: Path, a: float | None = None, b: float | None = None) -> float:
    af = (f"atrim={a or 0}:{b}," if b is not None else "") + "ebur128"
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", f, "-af", af, "-f", "null", "-"], check=False)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    return float(m[-1]) if m else -70.0


def gate_expr(spans: list) -> str:
    return "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in spans)


def loudness(f: Path, spans: list | None = None) -> dict:
    """Integrated loudness and true peak. With `spans`, loudness counts only those spans (silence elsewhere is
    removed by the -70 LUFS absolute gate): an approximation of dialogue-gated loudness."""
    af = (f"volume=0:enable='not({gate_expr(spans)})'," if spans else "") + "ebur128=peak=true"
    p = run(["ffmpeg", "-hide_banner", "-nostats", "-i", f, "-af", af, "-f", "null", "-"], check=False)
    i = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr); tp = re.findall(r"Peak:\s+(-?[\d.]+) dBFS", p.stderr)
    res = {"lufs": float(i[-1]) if i else None, "true_peak": float(tp[-1]) if tp else None}
    if spans:  # the true peak must come from the whole programme
        res["true_peak"] = loudness(f)["true_peak"]
    return res


def slug(d: dict) -> str:
    return re.sub(r"[^\w\-]+", "_", d["title"]).strip("_") or "sound"


# ---------- placement ----------
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


def place(d: dict, cues: list, out: Path) -> list[dict] | None:
    """Render placed cues onto a silent, full-length timeline. Returns the events, or None when nothing is placed.
    Every mix is anchored by a full-length silent input: mixing adelayed clips alone shifts the whole stem."""
    DUR = d["video"]["duration"]
    ev = [c for c in cues if cue_at(d, c) is not None]
    if not ev:
        out.unlink(missing_ok=True)
        return None
    inputs, parts, labels, rows = [], [f"anullsrc=r={SR}:cl=stereo:d={DUR}[base]"], ["[base]"], []
    for i, c in enumerate(ev):
        take = c.get("take") or c["id"]; f = P(d, f"takes/{take}.wav")
        if not f.exists():
            raise SoundError("INPUT_NOT_FOUND", f"{f} missing (cue {c['id']})")
        a0 = float(c.get("in", 0)); b0 = float(c.get("out", dur_of(f))); at = cue_at(d, c)
        default_peak = -6 if cue_kind(c) in DIALOGUE_KINDS else -8
        g = float(c.get("peak", d["characters"].get(c.get("char", ""), {}).get("peak", default_peak))) - max_db(f, a0, b0)
        ms = int(round(at * 1000)); inputs += ["-i", f]
        parts.append(f"[{i}:a]atrim={a0}:{b0},asetpts=PTS-STARTPTS,aformat=sample_rates={SR}:channel_layouts=stereo,"
                     f"afade=t=in:d=0.01,afade=t=out:st={max(b0 - a0 - 0.03, 0):.3f}:d=0.03,volume={g:.2f}dB,"
                     f"{fx_chain(d, c)},apad=pad_dur=0.8,adelay={ms}|{ms}[e{i}]")
        labels.append(f"[e{i}]")
        rows.append({"start": round(at, 3), "end": round(at + b0 - a0, 3), "cue": c["id"], "take": take,
                     "kind": cue_kind(c), "text": c.get("line", c.get("label", ""))})
    fc = ";".join(parts) + ";" + "".join(labels) + \
        f"amix=inputs={len(labels)}:normalize=0:dropout_transition=0,atrim=0:{DUR}[out]"
    out.parent.mkdir(parents=True, exist_ok=True)
    ffmpeg(*inputs, "-filter_complex", fc, "-map", "[out]", "-ar", SR, "-ac", 2, out)
    tsv = out.with_name(out.stem + "_events.tsv")
    tsv.write_text("start\tend\tcue\ttake\tkind\ttext\n" + "".join(
        f"{r['start']:.3f}\t{r['end']:.3f}\t{r['cue']}\t{r['take']}\t{r['kind']}\t{r['text']}\n" for r in rows), encoding="utf-8")
    return rows


# ---------- envelope ----------
def envelope(file: str, window: float) -> str:
    if not Path(file).exists():
        raise SoundError("INPUT_NOT_FOUND", f"{file} not found")
    try:
        raw = subprocess.run(["ffmpeg", "-v", "error", "-i", file, "-ac", "1", "-ar", "8000", "-f", "s16le", "-"],
                             capture_output=True, timeout=600).stdout
    except FileNotFoundError:
        raise SoundError("DEPENDENCY_MISSING", "ffmpeg not found on PATH")
    import array
    x = array.array("h"); x.frombytes(raw[: len(raw) // 2 * 2])
    n = int(8000 * window); out = []
    for i in range(0, len(x), n):
        seg = x[i:i + n]; r = math.sqrt(sum(v * v for v in seg) / max(len(seg), 1))
        out.append(f"{i / 8000:.1f}:{20 * math.log10(r / 32768) if r else -99:.0f}")
    return " ".join(out)
