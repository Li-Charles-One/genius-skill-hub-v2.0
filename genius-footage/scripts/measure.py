#!/usr/bin/env python3
"""
ArtisticCut measure — frame-accurate facts for one clip, no AI.

    python3 measure.py <video> [--output text|json] [--out FILE]

Reports fps, frame count, duration, resolution, start timecode, and shots (S001…)
as inclusive frame ranges. Two detectors read the same decode: frame differences and TransNetV2.

  cut      one-frame jump far above the local motion level   → confirmed when TransNetV2 agrees
  black    dip or fade through black                        → confirmed
  gradual  dissolve, fade to a non-black card, or fast move  → suspect, needs a visual check
  one-sided  a cut only one detector finds                  → suspect, needs a visual check

Suspects do not split shots; they are listed with their frame span for the storyboard check. Suspects
TransNetV2 scores below TN_SKIP are marked skipped. Rules: references/measurement.md.
Needs ffmpeg / ffprobe, and numpy, onnxruntime and the model from setup.py.
"""

from __future__ import annotations

import argparse
import json
import operator
import os
import subprocess
import sys
import tempfile
from fractions import Fraction
from pathlib import Path

import transnet

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
TN_CONFIRM = 0.5              # TransNetV2 probability that counts as a transition
TN_SKIP = 0.1                 # a frame-difference suspect TransNetV2 scores below this is skipped, not checked
TN_TOL = 2                    # frames of slack when matching the two detectors
CLUSTER_GAP = 3               # measured cuts this close are one event (a flash or blur frame next to a cut)


class MeasureError(RuntimeError):
    pass


class MissingDependency(MeasureError):
    pass


def run(cmd: list) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, capture_output=True, check=True)
    except FileNotFoundError as e:
        raise MissingDependency(f"{cmd[0]} not found on PATH (install ffmpeg)") from e
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
    r, avg = Fraction(v.get("r_frame_rate", "0/1")), Fraction(v.get("avg_frame_rate", "0/1") or "0/1")
    return {"width": v.get("width"), "height": v.get("height"), "codec": v.get("codec_name"),
            "fps": r, "avg_fps": avg, "nb_frames": int(v["nb_frames"]) if v.get("nb_frames", "").isdigit() else None,
            "timecode": next((t for t in tcs if t), None)}


def tc_rate(info: dict) -> int:
    """Frames per second that timecode counts. A picture rate stored on a finer timebase (24p on a 60 timebase:
    r_frame_rate 60, average 24.02) counts at the average rate, so frame 126 at 5.25 s is 00:00:05:06, not
    00:00:02:06; otherwise the nominal rate, as before."""
    r, avg = float(info["fps"]), float(info["avg_fps"] or 0)
    return round(avg) if avg and r / avg >= 1.5 else round(r)


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


def features(path: str, k: int, second: tuple[str, list] | None = None) -> tuple[list, list, list, list, tuple]:
    """Per frame: change from the previous frame, change from k frames back, mean brightness,
    share of pixels that changed from the previous frame, and TransNetV2's (single, many) probabilities.
    The frames TransNetV2 reads (48×27) come from the same decode, through a temporary raw file.
    second = (video filter, ffmpeg output args): another output written from the same decode (footage.py
    makes its whole-clip proxy this way, so the source is decoded once instead of twice)."""
    raw = ["-an", "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24"]
    fd, tn_path = tempfile.mkstemp(prefix="genius-footage-", suffix=".rgb")
    os.close(fd)
    graph = (f"[0:v:0]split={3 if second else 2}[a][t]{'[b]' if second else ''};[a]scale={W}:{H}:flags=area[m];"
             f"[t]scale={transnet.W}:{transnet.H}[n]" + (f";[b]{second[0]}[p]" if second else ""))
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", path, "-filter_complex", graph,
           "-map", "[m]", *raw, "-", "-map", "[n]", *raw, tn_path]
    if second:
        cmd += ["-map", "[p]", "-map", "0:a:0?", *second[1]]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
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
        if os.path.getsize(tn_path) != len(d1) * transnet.FRAME_BYTES:
            raise MeasureError(f"the two decodes of {path} disagree on the frame count")
        try:
            tn = transnet.predict_file(tn_path)
        except transnet.TransNetError as e:
            raise MissingDependency(f"TransNetV2: {e}") from e
    finally:
        Path(tn_path).unlink(missing_ok=True)
    return d1, dk, y, area, tn


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


def fuse(starts: dict, spans: dict, suspects: list, d1: list, single: list, many: list) -> tuple[dict, dict, list, dict]:
    """Check the frame-difference boundaries against TransNetV2 (references/measurement.md).
    Measured cuts closer than CLUSTER_GAP form one event. An event TransNetV2 also finds is confirmed, on the
    measured frame for one cut, or on TransNetV2's frame when it falls inside a cluster. Any other event becomes
    a weak-cut suspect that keeps its measured frames in "cuts". A TransNetV2 transition no measured boundary or
    suspect covers becomes a suspect too. Frame-difference suspects TransNetV2 scores below TN_SKIP are skipped.
    Black transitions stay as measured."""
    last = len(d1) - 1
    dets = [[a, min(b + 1, last), min(b + 1, last), True]  # the new shot starts after the marked frame
            for a, b in _runs([v >= TN_CONFIRM for v in single], 0)]
    dets += [[a, b, a, False] for a, b in _runs([v >= TN_CONFIRM for v in many], 0)]
    merged = []
    for d in sorted(dets):
        if merged and d[0] <= merged[-1][1] + TN_TOL:
            m = merged[-1]
            m[1] = max(m[1], d[1])
            if d[3] and not m[3]:
                m[2], m[3] = d[2], True
        else:
            merged.append(list(d))
    hits = lambda a, b: [i for i, d in enumerate(merged) if d[0] - TN_TOL <= b and d[1] + TN_TOL >= a]  # noqa: E731
    score = lambda a, b: max(single[max(0, a - TN_TOL):b + TN_TOL + 1] + many[max(0, a - TN_TOL):b + TN_TOL + 1])  # noqa: E731
    used, out = set(), []
    starts_out = {f: k for f, k in starts.items() if k != "cut"}
    for f, k in starts.items():
        if k != "cut" and f in spans:
            used.update(hits(*spans[f]))
    cuts, clusters = sorted(f for f, k in starts.items() if k == "cut"), []
    for c in cuts:
        if clusters and c - clusters[-1][-1] <= CLUSTER_GAP:
            clusters[-1].append(c)
        else:
            clusters.append([c])
    agreed = 0
    for cl in clusters:
        a, b, h = cl[0], cl[-1], hits(cl[0], cl[-1])
        used.update(h)
        if h and (len(cl) == 1 or (len(h) == 1 and a <= merged[h[0]][2] <= b)):
            starts_out[a if len(cl) == 1 else merged[h[0]][2]] = "cut"
            agreed += 1
        else:
            out.append({"first": a, "last": b, "kind": "weak-cut", "change": round(max(d1[a:b + 1]), 1),
                        "by": "frames", "cuts": cl, "tnv2": round(score(a, b), 2)})
    skipped = 0
    for s in suspects:
        h = hits(s["first"], s["last"])
        used.update(h)
        s.update(by="both" if h else "frames", tnv2=round(score(s["first"], s["last"]), 2))
        if s["tnv2"] < TN_SKIP:
            s.update(check="skipped", reason=f"TransNetV2 {s['tnv2']} < {TN_SKIP}")
            skipped += 1
    taken = [(s["first"], s["last"]) for s in suspects + out]
    added = 0
    for i, (a, b, _, cut) in enumerate(merged):
        if i in used or any(x - TN_TOL <= b and y + TN_TOL >= a for x, y in taken):
            continue
        out.append({"first": a, "last": b, "kind": "weak-cut" if cut else "gradual",
                    "change": round(max(d1[a:b + 1]), 1), "by": "transnet", "tnv2": round(score(a, b), 2)})
        added += 1
    stats = {"agreed": agreed, "one_sided": len(out) - added, "added": added, "skipped": skipped}
    return starts_out, {f: s for f, s in spans.items() if f in starts_out}, sorted(suspects + out, key=lambda s: s["first"]), stats


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

def measure(path: str, second: tuple[str, list] | None = None) -> dict:
    reason = transnet.missing()
    if reason:
        raise MissingDependency(f"TransNetV2: {reason}")
    info = probe(path)
    fps, rate = float(info["fps"]), tc_rate(info)
    t, tc, df, times = _clock(path, str(info["fps"]), info["timecode"], rate)
    d1, dk, y, area, (single, many) = features(path, max(1, round(fps / 2)), second)
    n = len(d1)
    warnings = []
    if info["avg_fps"] and abs(float(info["avg_fps"]) - fps) > 0.01:
        warnings.append(f"variable frame rate (avg {float(info['avg_fps']):.3f}); times come from each frame's pts"
                        + (f", timecode counts {rate} fps" if rate != round(fps) else ""))
    if len(times) != n:
        warnings.append(f"decoded {n} frames but the container lists {len(times)} packets")

    starts, spans, suspects, stats = fuse(*detect(d1, dk, y, area, fps), d1, single, many)
    end = t(n - 1) + 1 / fps
    shots = _shots(starts, spans, n, t, tc, end)
    for s in suspects:
        s.update({"start": round(t(s["first"]), 3), "tc": tc(s["first"])})
    _locate(suspects, shots)
    return {"file": path, "width": info["width"], "height": info["height"], "codec": info["codec"],
            "fps": round(fps, 3), "fps_rational": str(info["fps"]), "tc_fps": rate, "frames": n,
            "duration": round(end, 3), "timecode_start": info["timecode"], "drop_frame": df,
            "shot_count": len(shots), "shots": shots, "suspects": suspects,
            "transnet": {"model": "TransNetV2 (ONNX)", "confirm": TN_CONFIRM, "skip": TN_SKIP, **stats},
            "warnings": warnings}


def restore_measured_cuts(r: dict) -> dict:
    """Put back the frame-difference cuts that TransNetV2 did not confirm, as measure.py found them before
    TransNetV2 (talking-head mode and the overlay sheet, which do not check suspects)."""
    extra = {f: "cut" for s in r["suspects"] if s.get("cuts") for f in s["cuts"]}
    return add_boundaries(r, extra) if extra else r


def _clock(path: str, fps_rational: str, timecode: str | None, tc_fps: int | None = None):
    """(time of frame i, timecode of frame i, drop-frame flag, frame times). tc_fps: see tc_rate."""
    fps = float(Fraction(fps_rational))
    times = frame_times(path)
    nominal = tc_fps or round(fps)
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
    t, tc, _, _ = _clock(r["file"], r["fps_rational"], r["timecode_start"], r.get("tc_fps"))
    starts = {s["first"]: s["via"] for s in r["shots"][1:]}
    spans = {s["first"]: tuple(s["transition"]) for s in r["shots"] if "transition" in s}
    starts.update(extra)
    spans.update(extra_spans or {})
    r["shots"] = _shots(starts, spans, r["frames"], t, tc, r["duration"])
    r["shot_count"] = len(r["shots"])
    _locate(r["suspects"], r["shots"])
    return r


def render_text(r: dict) -> str:
    todo = [s for s in r["suspects"] if s.get("check") != "skipped"]
    lines = [r["file"],
             f"{r['width']}x{r['height']} {r['codec']} | {r['fps']} fps ({r['fps_rational']}) | {r['frames']} frames"
             f" | {r['duration']}s | TC start {r['timecode_start'] or '— (none, counting from 00:00:00:00)'}",
             f"shots: {r['shot_count']} confirmed" + (f", {len(todo)} suspect boundaries to check" if todo else "")
             + (f", {len(r['suspects']) - len(todo)} suspects skipped (TransNetV2 < {TN_SKIP})" if len(todo) < len(r["suspects"]) else ""),
             "", f"{'ID':5} {'first':>6} {'last':>6} {'frames':>6} {'start s':>8}  {'TC in':11}  {'TC out':11}  via"]
    lines += [f"{s['id']:5} {s['first']:6} {s['last']:6} {s['frames']:6} {s['start']:8.3f}  {s['tc_in']:11}  {s['tc_out']:11}  {s['via']}"
              + (f" (frames {s['transition'][0]}–{s['transition'][1]})" if "transition" in s else "")
              for s in r["shots"]]
    if todo:
        lines += ["", "suspects (check on the storyboard):"]
        lines += [f"  {s['kind']:8} frames {s['first']}–{s['last']} ({s['start']:.3f}s, {s['tc']}) in {s['in_shot']}, "
                  f"change {s['change']}, by {s['by']}, TransNetV2 {s['tnv2']}" for s in todo]
    lines += [f"warning: {w}" for w in r["warnings"]]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Frame-accurate fps, frame count, timecode and shot list for a clip")
    parser.add_argument("file")
    parser.add_argument("--output", choices=["text", "json"], default="text")
    parser.add_argument("--out", help="Also write the result to this file")
    transnet.reexec()
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
