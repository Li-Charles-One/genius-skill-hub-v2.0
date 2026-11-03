#!/usr/bin/env python3
"""
ArtisticCut measure — frame-accurate facts for one clip, no AI.

    python3 measure.py <video> [--output text|json] [--out FILE]

Reports fps, frame count, duration, resolution, start timecode, and shots (S001…)
as inclusive frame ranges. How a shot boundary is found:

  cut      one-frame jump far above the local motion level   → confirmed
  black    dip or fade through black                        → confirmed
  gradual  dissolve, fade to a non-black card, or fast move  → suspect, needs a visual check

Suspects do not split shots; they are listed with their frame span for the storyboard check.
Needs ffmpeg / ffprobe; Python standard library only.
"""

from __future__ import annotations

import argparse
import json
import operator
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

W, H = 32, 18                 # analysis size; enough to separate shots, cheap to diff in pure Python
FRAME_BYTES = W * H * 3
LOCAL = 5                     # neighbours on each side that define the local motion level
CUT_MIN, CUT_RATIO = 6.0, 3.0        # mean abs diff (0–255) and jump over local level for a cut
CUT_AREA, AREA_PIX = 0.6, 30         # share of pixels that changed (RGB diff sum > AREA_PIX); a hand
                                     # crossing frame measured 0.35, real cuts 0.89–0.97
WEAK_MIN, WEAK_RATIO = 3.0, 2.5      # below a cut but still a spike: suspect
MOTION_FLOOR = 0.5            # local level floor so static shots do not turn noise into huge ratios
DUP_D1 = 0.3                  # repeated frames (low-fps sources upconverted) are left out of the local level,
                              # otherwise every real picture update in 7.5 fps webcam footage looks like a cut
BLACK_Y = 3.0                 # mean RGB at or below this is a black frame
GRAD_MIN = 1.5                # per-frame change that counts as "still moving" inside a gradual run
GRAD_CHANGE = 12.0            # change across half a second needed to call a run a transition
GRAD_MAX_SEC = 2.0            # longer runs are camera moves, not transitions
GRAD_GAP = 2                  # still frames bridged inside a run (duplicated frames in AI / pulldown footage)


class MeasureError(RuntimeError):
    pass


def run(cmd: list) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, check=True)
    except FileNotFoundError as e:
        raise MeasureError(f"{cmd[0]} not found on PATH (install ffmpeg)") from e
    except subprocess.CalledProcessError as e:
        raise MeasureError(f"{cmd[0]} failed: {e.stderr.decode(errors='replace')[-300:]}") from e


# ── Probe ────────────────────────────────────────────────────────────────

def probe(path: str) -> dict:
    data = json.loads(run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", path]).stdout)
    streams = data.get("streams", [])
    v = next((s for s in streams if s.get("codec_type") == "video"
              and not s.get("disposition", {}).get("attached_pic")), None)
    if not v:
        raise MeasureError(f"no video stream in {path}")
    tcs = [(s.get("tags") or {}).get("timecode") for s in streams] + [(data["format"].get("tags") or {}).get("timecode")]
    r, avg = Fraction(v.get("r_frame_rate", "0/1")), Fraction(v.get("avg_frame_rate", "0/1"))
    return {"width": v.get("width"), "height": v.get("height"), "codec": v.get("codec_name"),
            "fps": r, "avg_fps": avg, "nb_frames": int(v["nb_frames"]) if v.get("nb_frames", "").isdigit() else None,
            "timecode": next((t for t in tcs if t), None)}


def frame_times(path: str, for_seek: bool = False) -> list[float]:
    """Presentation time of every video frame, from packet pts (no decode). Relative to the first video
    frame; with for_seek, relative to the container start instead, which is what ffmpeg -ss counts from
    (they differ when audio or an edit list starts before the first video frame)."""
    out = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
               "-show_entries", "format=start_time", "-of", "csv=p=0", path]).stdout.decode().split()
    *packets, start = out
    pts = sorted(float(x) for x in packets if x not in ("N/A", ""))
    base = float(start) if for_seek and start not in ("N/A", "") else (pts[0] if pts else 0.0)
    return [round(t - base, 6) for t in pts]


# ── Features ─────────────────────────────────────────────────────────────

def _mad(a: bytes, b: bytes) -> float:
    return sum(map(abs, map(operator.sub, a, b))) / FRAME_BYTES


def _area(a: bytes, b: bytes) -> float:
    d = list(map(abs, map(operator.sub, a, b)))
    return sum(d[k] + d[k + 1] + d[k + 2] > AREA_PIX for k in range(0, FRAME_BYTES, 3)) / (W * H)


def features(path: str, k: int) -> tuple[list, list, list, list]:
    """Per frame: change from the previous frame, change from k frames back, mean brightness,
    share of pixels that changed from the previous frame."""
    proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", path, "-map", "0:v:0", "-an", "-fps_mode", "passthrough",
                             "-vf", f"scale={W}:{H}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    d1, dk, y, area, ring = [], [], [], [], []
    while True:
        f = proc.stdout.read(FRAME_BYTES)
        if len(f) < FRAME_BYTES:
            break
        d1.append(_mad(f, ring[-1]) if ring else 0.0)
        area.append(_area(f, ring[-1]) if ring else 0.0)
        dk.append(_mad(f, ring[-k]) if len(ring) >= k else 0.0)
        y.append(sum(f) / FRAME_BYTES)
        ring.append(f)
        if len(ring) > k:
            ring.pop(0)
    err = proc.stderr.read().decode(errors="replace")
    if proc.wait() != 0 or not d1:
        raise MeasureError(f"ffmpeg could not decode {path}: {err[-300:]}")
    return d1, dk, y, area


# ── Boundaries ───────────────────────────────────────────────────────────

def _runs(mask: list, gap: int) -> list[tuple[int, int]]:
    """Inclusive (first, last) spans where mask is true, bridging up to `gap` false frames."""
    spans, i, n = [], 0, len(mask)
    while i < n:
        if not mask[i]:
            i += 1
            continue
        j = i
        while (nxt := next((g for g in range(j + 1, min(n, j + 2 + gap)) if mask[g]), None)) is not None:
            j = nxt
        spans.append((i, j))
        i = j + 1
    return spans


def detect(d1: list, dk: list, y: list, area: list, fps: float) -> tuple[dict, dict, list]:
    """Return ({frame: kind} confirmed shot starts, {frame: (first, last)} transition spans, [suspects])."""
    n = len(d1)
    level = lambda vals: (lambda v: v[len(v) // 2] if v else 0.0)(sorted(v for v in vals if v > DUP_D1))
    cuts, suspects, starts, spans = [], [], {}, {}
    for i in range(1, n):
        # Also take the level from this shot alone (since the last cut): a still shot before a cut into a
        # whip pan would otherwise drag the level down and turn the pan's next frames into cuts as well.
        lo, right = max(1, i - LOCAL), d1[i + 1:i + 1 + LOCAL]
        since = max(lo, cuts[-1] + 1) if cuts else lo
        ratio = d1[i] / max(level(d1[lo:i] + right), level(d1[since:i] + right), MOTION_FLOOR)
        if d1[i] >= CUT_MIN and ratio >= CUT_RATIO and area[i] >= CUT_AREA:
            cuts.append(i)
        elif d1[i] >= WEAK_MIN and ratio >= WEAK_RATIO:  # a spike over part of the picture, or a dark/low-contrast cut
            if suspects and suspects[-1]["last"] == i - 1:  # back-to-back spikes are one short dissolve
                suspects[-1].update(last=i, change=max(suspects[-1]["change"], round(d1[i], 1)))
            else:
                suspects.append({"first": i, "last": i, "kind": "weak-cut", "change": round(d1[i], 1)})

    # Fades through black: the black frames plus the change leading in and out (≤1s each side) are one
    # transition; the next shot starts on the first frame after the black.
    moving = _runs([v >= GRAD_MIN for v in d1], GRAD_GAP)
    covered = []
    for a, b in _runs([v <= BLACK_Y for v in y], 0):
        if a == 0 or b == n - 1:
            continue
        lo = min([r[0] for r in moving if a - 1 - GRAD_GAP <= r[1] and r[0] <= a] + [a])
        hi = max([r[1] for r in moving if r[0] <= b + 1 + GRAD_GAP and r[1] >= b] + [b])
        lo, hi = max(lo, a - round(fps)), min(hi, b + round(fps))
        starts[b + 1], spans[b + 1] = "black", (lo, hi)
        covered.append((lo, hi + 1))
    inside = lambda f: any(lo <= f <= hi for lo, hi in covered)
    starts.update({c: "cut" for c in cuts if not inside(c)})

    # Gradual runs: sustained change that adds up to a different picture within GRAD_MAX_SEC.
    near = lambda a, b: any(a - 2 <= f <= b + 2 for f in starts) or any(inside(f) for f in range(a, b + 1))
    gradual = [{"first": a, "last": b, "kind": "gradual", "change": round(max(dk[a:b + 1]), 1)}
               for a, b in moving
               if 3 <= b - a + 1 <= GRAD_MAX_SEC * fps and max(dk[a:b + 1]) >= GRAD_CHANGE and not near(a, b)]
    suspects = [s for s in suspects if not near(s["first"], s["last"])
                and not any(g["first"] <= s["first"] <= g["last"] for g in gradual)]
    return starts, spans, sorted(suspects + gradual, key=lambda s: s["first"])


# ── Timecode ─────────────────────────────────────────────────────────────

def tc_to_frames(tc: str, nominal: int) -> tuple[int, bool]:
    df = ";" in tc or "." in tc
    h, m, s, f = (int(x) for x in tc.replace(";", ":").replace(".", ":").split(":"))
    frames = (h * 3600 + m * 60 + s) * nominal + f
    if df:
        drop = nominal // 15  # 2 at 29.97, 4 at 59.94
        minutes = h * 60 + m
        frames -= drop * (minutes - minutes // 10)
    return frames, df


def frames_to_tc(fn: int, nominal: int, df: bool) -> str:
    if df:
        drop = nominal // 15
        per10, per1 = nominal * 600 - drop * 9, nominal * 60 - drop
        tens, rem = divmod(fn, per10)
        fn += drop * 9 * tens + (drop * ((rem - drop) // per1) if rem > drop else 0)
    f, s = fn % nominal, fn // nominal
    sep = ";" if df else ":"
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}{sep}{f:02d}"


# ── Report ───────────────────────────────────────────────────────────────

def measure(path: str) -> dict:
    info = probe(path)
    fps = float(info["fps"])
    t, tc, df, times = _clock(path, str(info["fps"]), info["timecode"])
    d1, dk, y, area = features(path, max(1, round(fps / 2)))
    n = len(d1)
    warnings = []
    if info["avg_fps"] and abs(float(info["avg_fps"]) - fps) > 0.01:
        warnings.append(f"variable frame rate (avg {float(info['avg_fps']):.3f}); times come from each frame's pts")
    if len(times) != n:
        warnings.append(f"decoded {n} frames but the container lists {len(times)} packets")

    starts, spans, suspects = detect(d1, dk, y, area, fps)
    end = t(n - 1) + 1 / fps
    shots = _shots(starts, spans, n, t, tc, end)
    for s in suspects:
        s.update({"start": round(t(s["first"]), 3), "tc": tc(s["first"])})
    _locate(suspects, shots)
    return {"file": path, "width": info["width"], "height": info["height"], "codec": info["codec"],
            "fps": round(fps, 3), "fps_rational": str(info["fps"]), "frames": n, "duration": round(end, 3),
            "timecode_start": info["timecode"], "drop_frame": df, "shot_count": len(shots),
            "shots": shots, "suspects": suspects, "warnings": warnings}


def _clock(path: str, fps_rational: str, timecode: str | None):
    """(time of frame i, timecode of frame i, drop-frame flag, frame times)."""
    fps = float(Fraction(fps_rational))
    times = frame_times(path)
    nominal = round(fps)
    start, df = tc_to_frames(timecode, nominal) if timecode else (0, False)
    return (lambda i: times[i] if i < len(times) else i / fps), \
           (lambda i: frames_to_tc(start + i, nominal, df)), df, times


def _shots(starts: dict, spans: dict, n: int, t, tc, end: float) -> list[dict]:
    edges = [0] + sorted(starts) + [n]
    return [{"id": f"S{k:03d}", "first": a, "last": b - 1, "frames": b - a,
             "start": round(t(a), 3), "end": round(t(b) if b < n else end, 3),
             "tc_in": tc(a), "tc_out": tc(b - 1), "via": starts.get(a, "start"),
             **({"transition": list(spans[a])} if a in spans else {})}
            for k, (a, b) in enumerate(zip(edges, edges[1:]), 1)]


def _locate(suspects: list, shots: list) -> None:
    for s in suspects:
        s["in_shot"] = next(x["id"] for x in shots if x["first"] <= s["first"] <= x["last"])


def add_boundaries(r: dict, extra: dict, extra_spans: dict | None = None) -> dict:
    """Split shots at extra {frame: kind} boundaries (e.g. confirmed on the storyboard) and renumber.
    extra_spans: {frame: (first, last)} transition frames for the new boundaries."""
    t, tc, _, _ = _clock(r["file"], r["fps_rational"], r["timecode_start"])
    starts = {s["first"]: s["via"] for s in r["shots"][1:]}
    spans = {s["first"]: tuple(s["transition"]) for s in r["shots"] if "transition" in s}
    starts.update(extra)
    spans.update(extra_spans or {})
    r["shots"] = _shots(starts, spans, r["frames"], t, tc, r["duration"])
    r["shot_count"] = len(r["shots"])
    _locate(r["suspects"], r["shots"])
    return r


def render_text(r: dict) -> str:
    lines = [r["file"],
             f"{r['width']}x{r['height']} {r['codec']} | {r['fps']} fps ({r['fps_rational']}) | {r['frames']} frames"
             f" | {r['duration']}s | TC start {r['timecode_start'] or '— (none, counting from 00:00:00:00)'}",
             f"shots: {r['shot_count']} confirmed" + (f", {len(r['suspects'])} suspect boundaries to check" if r["suspects"] else ""),
             "", f"{'ID':5} {'first':>6} {'last':>6} {'frames':>6} {'start s':>8}  {'TC in':11}  {'TC out':11}  via"]
    lines += [f"{s['id']:5} {s['first']:6} {s['last']:6} {s['frames']:6} {s['start']:8.3f}  {s['tc_in']:11}  {s['tc_out']:11}  {s['via']}"
              + (f" (frames {s['transition'][0]}–{s['transition'][1]})" if "transition" in s else "")
              for s in r["shots"]]
    if r["suspects"]:
        lines += ["", "suspects (check on the storyboard):"]
        lines += [f"  {s['kind']:8} frames {s['first']}–{s['last']} ({s['start']:.3f}s, {s['tc']}) in {s['in_shot']}, change {s['change']}"
                  for s in r["suspects"]]
    lines += [f"warning: {w}" for w in r["warnings"]]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Frame-accurate fps, frame count, timecode and shot list for a clip")
    parser.add_argument("file")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--out", help="Also write the result to this file")
    args = parser.parse_args()
    if not Path(args.file).is_file():
        print(f"Error: file not found: {args.file}", file=sys.stderr)
        return 3
    try:
        r = measure(args.file)
    except MeasureError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    rendered = json.dumps(r, ensure_ascii=False, indent=2) if args.output == "json" else render_text(r)
    if args.out:
        Path(args.out).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0


if __name__ == "__main__":
    sys.exit(main())
