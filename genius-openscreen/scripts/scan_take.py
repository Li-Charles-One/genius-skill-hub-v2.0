#!/usr/bin/env python3
"""Scan an OpenScreen take before editing it.

Reports the audio level, frozen-picture spans (ffmpeg freezedetect), cursor events
from the take's telemetry sidecar (clicks, double-clicks, drags, flicks, idle spans)
and pause candidates: frozen picture AND idle cursor, as padded trim ranges in
source seconds. Optionally prints the cursor track binned to 0.1 s for planning
zoom keyframes.

Needs ffmpeg and ffprobe on PATH. Standard library only.
"""

import argparse
import json
import math
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

FREEZE_RE = re.compile(r"freeze_(start|end|duration):\s*([0-9.]+)")
VOLUME_RE = re.compile(r"(mean|max)_volume:\s*(-?[0-9.]+|-inf) dB")


def recordings_dirs():
    """OpenScreen's default recordings folder per OS (macOS verified, others expected)."""
    home = Path.home()
    if sys.platform == "darwin":
        return [home / "Library" / "Application Support" / "openscreen" / "recordings"]
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        return [Path(appdata) / "openscreen" / "recordings"] if appdata else []
    config = os.environ.get("XDG_CONFIG_HOME") or str(home / ".config")
    return [Path(config) / "openscreen" / "recordings"]


def latest_take():
    takes = []
    for folder in recordings_dirs():
        if folder.is_dir():
            takes += [p for p in folder.iterdir() if p.suffix.lower() in (".mp4", ".webm", ".mov")]
    if not takes:
        sys.exit("error: no takes found in " + ", ".join(str(d) for d in recordings_dirs()))
    return max(takes, key=lambda p: p.stat().st_mtime)


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")


def probe(video):
    out = run(["ffprobe", "-v", "error", "-show_entries",
               "stream=codec_type,width,height,r_frame_rate:format=duration",
               "-of", "json", str(video)])
    if out.returncode != 0:
        sys.exit("error: ffprobe failed: " + out.stderr.strip())
    data = json.loads(out.stdout)
    info = {"duration": float(data["format"]["duration"]), "has_audio": False}
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and "width" not in info:
            info["width"], info["height"] = s["width"], s["height"]
            num, _, den = s.get("r_frame_rate", "0/1").partition("/")
            info["fps"] = round(float(num) / float(den or 1), 3) if float(den or 1) else None
        elif s.get("codec_type") == "audio":
            info["has_audio"] = True
    return info


def audio_level(video):
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-map", "0:a:0",
               "-af", "volumedetect", "-f", "null", "-"])
    levels = {k: (None if v == "-inf" else float(v)) for k, v in VOLUME_RE.findall(out.stderr)}
    return levels or None


def freeze_spans(video, duration, noise_db, min_sec, width):
    vf = f"scale={width}:-2,freezedetect=n={noise_db}dB:d={min_sec}"
    out = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(video), "-map", "0:v:0",
               "-vf", vf, "-f", "null", "-"])
    spans, start = [], None
    for key, value in FREEZE_RE.findall(out.stderr):
        if key == "start":
            start = float(value)
        elif key == "end" and start is not None:
            spans.append([start, float(value)])
            start = None
    if start is not None:  # frozen until the end of the take
        spans.append([start, duration])
    return spans


def load_cursor(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    samples = sorted(data.get("samples", []), key=lambda s: s["timeMs"])
    return [{"t": s["timeMs"] / 1000.0, "x": s["cx"], "y": s["cy"],
             "kind": s.get("interactionType", "move")} for s in samples]


def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def presses(samples, drag_min_dist, drag_min_sec, double_gap):
    """Pair click/mouseup (FIFO) into clicks, double-clicks and drags."""
    open_clicks, pressed = [], []
    for s in samples:
        if s["kind"] == "click":
            open_clicks.append(s)
        elif s["kind"] == "mouseup" and open_clicks:
            down = open_clicks.pop(0)
            pressed.append((down, s))
    events = []
    for down, up in pressed:
        moved = dist((down["x"], down["y"]), (up["x"], up["y"]))
        dur = up["t"] - down["t"]
        if moved > drag_min_dist and dur >= drag_min_sec:
            events.append({"kind": "drag", "start": down["t"], "end": up["t"],
                           "from": [down["x"], down["y"]], "to": [up["x"], up["y"]]})
            continue
        prev = events[-1] if events else None
        if (prev and prev["kind"] in ("click", "double-click")
                and down["t"] - prev["start"] <= double_gap
                and dist(prev["at"], (down["x"], down["y"])) < 0.01):
            prev["kind"] = "double-click"
            continue
        events.append({"kind": "click", "start": down["t"], "end": up["t"],
                       "at": [down["x"], down["y"]]})
    return events


def merge(spans, gap=0.0):
    spans = sorted(spans)
    out = []
    for s, e in spans:
        if out and s <= out[-1][1] + gap:
            out[-1][1] = max(out[-1][1], e)
        else:
            out.append([s, e])
    return out


def active_spans(samples, move_eps, pad):
    """Times when the cursor moves or a button is pressed, padded and merged."""
    spans = []
    for a, b in zip(samples, samples[1:]):
        if dist((a["x"], a["y"]), (b["x"], b["y"])) > move_eps:
            spans.append([a["t"] - pad, b["t"] + pad])
    for s in samples:
        if s["kind"] != "move":
            spans.append([s["t"] - pad, s["t"] + pad])
    return merge(spans)


def complement(spans, start, end):
    out, cur = [], start
    for s, e in spans:
        if s > cur:
            out.append([cur, min(s, end)])
        cur = max(cur, e)
    if cur < end:
        out.append([cur, end])
    return [x for x in out if x[1] > x[0]]


def intersect(a, b):
    out, i, j = [], 0, 0
    while i < len(a) and j < len(b):
        s, e = max(a[i][0], b[j][0]), min(a[i][1], b[j][1])
        if e > s:
            out.append([s, e])
        if a[i][1] < b[j][1]:
            i += 1
        else:
            j += 1
    return out


def flicks(samples, speed_min, window):
    """Fast pointer moves (screen fractions per second) the camera will lag behind."""
    spans = []
    j = 0
    for i, a in enumerate(samples):
        while j < len(samples) and samples[j]["t"] - a["t"] < window:
            j += 1
        if j >= len(samples):
            break
        b = samples[j]
        dt = b["t"] - a["t"]
        if dt > 0 and dist((a["x"], a["y"]), (b["x"], b["y"])) / dt >= speed_min:
            spans.append([a["t"], b["t"]])
    out = []
    for s, e in merge(spans):
        first = min(samples, key=lambda x: abs(x["t"] - s))
        last = min(samples, key=lambda x: abs(x["t"] - e))
        out.append({"start": s, "end": e, "from": [first["x"], first["y"]], "to": [last["x"], last["y"]]})
    return out


def track(samples, step):
    bins = {}
    for s in samples:
        bins.setdefault(int(s["t"] / step), []).append(s)
    return [[round(k * step, 2), round(sum(p["x"] for p in v) / len(v), 3),
             round(sum(p["y"] for p in v) / len(v), 3)] for k, v in sorted(bins.items())]


def r(v):
    return round(v, 2)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", nargs="?", help="the take (.mp4); omit with --latest")
    ap.add_argument("--latest", action="store_true", help="use the newest take in OpenScreen's recordings folder")
    ap.add_argument("--cursor", help="cursor telemetry (default: <video>.cursor.json next to the take)")
    ap.add_argument("--noise-db", type=float, default=-70.0, help="freezedetect noise in dB (default -70)")
    ap.add_argument("--freeze-min", type=float, default=0.8, help="shortest frozen span in s (default 0.8)")
    ap.add_argument("--pause-min", type=float, default=1.5, help="shortest pause to cut in s (default 1.5)")
    ap.add_argument("--pad", type=float, default=0.3, help="kept at each end of a cut in s (default 0.3)")
    ap.add_argument("--track", action="store_true", help="also print the cursor track binned to 0.1 s")
    ap.add_argument("--output", choices=["text", "json"], default="text")
    args = ap.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            sys.exit(f"error: {tool} not found on PATH")
    if args.latest:
        video = latest_take()
    elif args.video:
        video = Path(args.video).expanduser()
    else:
        ap.error("give a video path or --latest")
    if not video.is_file():
        sys.exit(f"error: not a file: {video}")

    info = probe(video)
    half_width = max(2, (info.get("width", 1920) // 4) * 2)
    result = {"take": str(video), **{k: info.get(k) for k in ("duration", "width", "height", "fps")}}
    result["audio"] = audio_level(video) if info["has_audio"] else None
    freezes = freeze_spans(video, info["duration"], args.noise_db, args.freeze_min, half_width)
    result["freeze"] = {"noise_db": args.noise_db, "min_sec": args.freeze_min,
                        "spans": [[r(s), r(e)] for s, e in freezes]}

    cursor_path = Path(args.cursor) if args.cursor else video.with_name(video.name + ".cursor.json")
    samples = load_cursor(cursor_path) if cursor_path.is_file() else []
    result["cursor"] = str(cursor_path) if samples else None
    if samples:
        idle = complement(active_spans(samples, move_eps=0.0015, pad=0.15), 0.0, info["duration"])
        events = presses(samples, drag_min_dist=0.01, drag_min_sec=0.2, double_gap=0.5)
        result["clicks"] = [{"kind": e["kind"], "t": r(e["start"]), "at": [round(v, 3) for v in e["at"]]}
                            for e in events if e["kind"] != "drag"]
        result["drags"] = [{"start": r(e["start"]), "end": r(e["end"]),
                            "from": [round(v, 3) for v in e["from"]], "to": [round(v, 3) for v in e["to"]]}
                           for e in events if e["kind"] == "drag"]
        result["flicks"] = [{"start": r(f["start"]), "end": r(f["end"]),
                             "from": [round(v, 3) for v in f["from"]], "to": [round(v, 3) for v in f["to"]]}
                            for f in flicks(samples, speed_min=1.5, window=0.1)]
        result["idle"] = [[r(s), r(e)] for s, e in idle if e - s >= 1.0]
        paused = intersect(freezes, idle)
    else:
        paused = freezes
        result["warning"] = f"no cursor telemetry at {cursor_path}: pause candidates use the picture only"

    candidates = []
    for s, e in paused:
        if e - s >= args.pause_min:
            candidates.append({"trim": [r(s + args.pad), r(e - args.pad)], "frozen": [r(s), r(e)],
                               "cut_sec": r(e - s - 2 * args.pad)})
    result["pause_candidates"] = candidates
    result["cut_total_sec"] = r(sum(c["cut_sec"] for c in candidates))
    if args.track and samples:
        result["track_0_1s"] = track(samples, 0.1)

    if args.output == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    print(f"take: {result['take']}")
    print(f"  {info['duration']:.2f} s, {info.get('width')}x{info.get('height')}, {info.get('fps')} fps")
    a = result["audio"]
    if a is None:
        print("audio: none")
    else:
        mean = a.get("mean")
        silent = mean is None or mean < -60
        print(f"audio: mean {mean} dB, max {a.get('max')} dB" + ("  (silent: no transcript to cut by)" if silent else ""))
    print(f"frozen picture (n={args.noise_db:g} dB, >= {args.freeze_min:g} s): {len(freezes)} spans")
    for s, e in result["freeze"]["spans"]:
        print(f"  {s:7.2f} - {e:7.2f}  ({e - s:.2f} s)")
    if samples:
        print(f"cursor: {len(samples)} samples from {cursor_path.name}")
        for c in result["clicks"]:
            print(f"  {c['kind']:12s} {c['t']:7.2f}  at ({c['at'][0]:.3f}, {c['at'][1]:.3f})")
        for d in result["drags"]:
            print(f"  drag         {d['start']:7.2f} - {d['end']:.2f}  ({d['from'][0]:.3f}, {d['from'][1]:.3f}) -> ({d['to'][0]:.3f}, {d['to'][1]:.3f})")
        for f in result["flicks"]:
            print(f"  flick        {f['start']:7.2f} - {f['end']:.2f}  ({f['from'][0]:.3f}, {f['from'][1]:.3f}) -> ({f['to'][0]:.3f}, {f['to'][1]:.3f})")
        print("idle cursor >= 1 s: " + ", ".join(f"{s:.2f}-{e:.2f}" for s, e in result["idle"]))
    else:
        print("warning: " + result["warning"])
    print(f"pause candidates (frozen and idle >= {args.pause_min:g} s, pad {args.pad:g} s): {len(candidates)}")
    for c in candidates:
        print(f"  trim {c['trim'][0]:7.2f} - {c['trim'][1]:7.2f}  cuts {c['cut_sec']:.2f} s  (frozen {c['frozen'][0]:.2f}-{c['frozen'][1]:.2f})")
    print(f"  total cut: {result['cut_total_sec']:.2f} s")
    if args.track and samples:
        print("cursor track (t, x, y) every 0.1 s:")
        for t, x, y in result["track_0_1s"]:
            print(f"  {t:6.1f} {x:.3f} {y:.3f}")


if __name__ == "__main__":
    main()
