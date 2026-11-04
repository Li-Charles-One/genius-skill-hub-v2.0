"""Re-recording mix & mastering: predub D / M / E, duck music under dialogue, master to a delivery spec with a
static gain and a true-peak limiter, export the DME stems and the M&E, mux the picture."""
from __future__ import annotations

import json, re

from core import (SoundError, P, SR, BED_LUFS, bed_file, bed_kind, cue_kind, ffmpeg, load, log, loudness, lufs,
                  place, run, save, slug, gate_expr)
from dialogue import check, place_dialogue

SPECS = {  # integrated target (LUFS/LKFS), tolerance (LU), true-peak ceiling (dBTP)
    "web": {"lufs": -16, "tol": 1.0, "tp": -1.5, "label": "online video / social (default)"},
    "stream": {"lufs": -14, "tol": 1.0, "tp": -1.0, "label": "-14 LUFS platform normalisation (YouTube-style)"},
    "ebu": {"lufs": -23, "tol": 0.5, "tp": -1.0, "label": "EBU R128 broadcast"},
    "tv24": {"lufs": -24, "tol": 2.0, "tp": -2.0, "label": "ATSC A/85 broadcast; CN TV GY/T 282 also targets -24 LKFS"},
    "netflix": {"lufs": -27, "tol": 2.0, "tp": -2.0, "gated": True, "label": "Netflix, dialogue-gated (approximation)"},
}
COMP = "acompressor=threshold=0.05:ratio=4:attack=5:release=120:makeup=2,volume={boost}dB,alimiter=limit=0.95"


def bed_chain(d: dict, b: dict, i: int) -> str:
    DUR = d["video"]["duration"]; f = bed_file(d, b); t0, t1 = (b.get("trim") or [0, None])
    target = b.get("lufs", BED_LUFS.get(bed_kind(b), -30))
    g = 0.0 if target is None else float(target) - lufs(f, t0, t1)
    chain = f"[{i}:a]aformat=sample_rates={SR}:channel_layouts=stereo"
    if t1 is not None:
        chain += f",atrim={t0}:{t1},asetpts=PTS-STARTPTS,afade=t=out:st={max(t1 - t0 - 0.7, 0):.2f}:d=0.7"
    chain += f",volume={g:.2f}dB"
    for s0, s1, gain in b.get("mutes", []):
        chain += f",volume={gain}:enable='between(t,{s0},{s1})'"
    ms = int(round(float(b.get("at", 0)) * 1000))
    return chain + f",adelay={ms}|{ms},apad=whole_dur={DUR},atrim=0:{DUR}[b{i}]"


def predub(d: dict) -> list[tuple[float, float]]:
    """Writes work/stems/pre_{D,M,E,X}.wav (X = non-verbal efforts, for the M&E). Returns spoken-line spans."""
    DUR, st = d["video"]["duration"], P(d, "work/stems")
    rows = place_dialogue(d) or []
    place(d, [c for c in d["cues"] if cue_kind(c) == "foley"], st / "foley.wav")
    args, fc = [], []

    def add(f) -> int:
        args.extend(["-i", f]); return len(args) // 2 - 1
    groups = {"D": [], "X": [], "M": [], "E": []}
    for name, g in (("dialogue", "D"), ("efforts", "X"), ("foley", "E")):
        if (st / f"{name}.wav").exists():
            groups[g].append(f"[{add(st / f'{name}.wav')}:a]")
    beds = [b for b in d["beds"] if bed_file(d, b).exists()]
    missing = [b["id"] for b in d["beds"] if b not in beds]
    if missing:
        log(f"beds not generated, skipped: {', '.join(missing)}")
    ducked = []
    for b in beds:
        i = add(bed_file(d, b)); fc.append(bed_chain(d, b, i))
        g = {"music": "M", "dialogue": "D"}.get(bed_kind(b), "E")
        if b.get("duck") and g != "D":
            ducked.append((f"b{i}", g))
        else:
            groups[g].append(f"[b{i}]")
    comp = COMP.format(boost=d["mix"].get("vo_boost_db", 5))
    keys = "".join(f"[k{j}]" for j in range(len(ducked)))
    for g in "DXME":
        fc.append(f"anullsrc=r={SR}:cl=stereo:d={DUR}[z{g}]")
    fc.append(f"[zD]{''.join(groups['D'])}amix=inputs={1 + len(groups['D'])}:normalize=0,{comp},"
              f"atrim=0:{DUR},asplit={1 + len(ducked)}[D]{keys}")
    fc.append(f"[zX]{''.join(groups['X'])}amix=inputs={1 + len(groups['X'])}:normalize=0"
              + (f",{comp}" if groups["X"] else "") + f",atrim=0:{DUR}[X]")
    for j, (n, g) in enumerate(ducked):
        fc.append(f"[{n}][k{j}]sidechaincompress=threshold=0.015:ratio=8:attack=15:release=350[{n}d]")
        groups[g].append(f"[{n}d]")
    for g in "ME":
        fc.append(f"[z{g}]{''.join(groups[g])}amix=inputs={1 + len(groups[g])}:normalize=0,atrim=0:{DUR}[{g}]")
    outs = [x for g in "DMEX" for x in ("-map", f"[{g}]", "-ar", SR, "-ac", 2, st / f"pre_{g}.wav")]
    ffmpeg(*args, "-filter_complex", ";".join(fc), *outs)
    spoken = {c["id"] for c in d["cues"] if c.get("line")}
    return [(r["start"], r["end"]) for r in rows if r["cue"] in spoken]


def sum_lufs(d: dict, spans: list) -> float:
    st = P(d, "work/stems")
    gate = f"volume=0:enable='not({gate_expr(spans)})'," if spans else ""
    p = run(["ffmpeg", "-hide_banner", "-nostats", *[x for g in "DME" for x in ("-i", st / f"pre_{g}.wav")],
             "-filter_complex", f"amix=inputs=3:normalize=0,{gate}ebur128", "-f", "null", "-"], check=False)
    m = re.findall(r"I:\s+(-?[\d.]+) LUFS", p.stderr)
    if not m or float(m[-1]) <= -69:
        raise SoundError("INPUT_NOT_FOUND", "the mix is silent: nothing is placed and no bed exists")
    return float(m[-1])


def render_master(d: dict, gain: float, tp: float, out) -> None:
    st = P(d, "work/stems"); ceiling = 10 ** ((tp - 0.3) / 20)  # 4x oversampled limiter, 0.3 dB margin
    ffmpeg(*[x for g in "DME" for x in ("-i", st / f"pre_{g}.wav")], "-filter_complex",
           f"amix=inputs=3:normalize=0,volume={gain:.2f}dB,aresample={SR * 4},"
           f"alimiter=limit={ceiling:.4f}:level=false:latency=true:attack=1:release=60,aresample={SR}",
           "-c:a", "pcm_s24le", "-ar", SR, "-ac", 2, out)


def cmd_master(a) -> None:
    d = load(a.project); m = d["mix"]
    legacy = {k: m.pop(k) for k in ("lufs", "tp", "lra") if k in m}
    if legacy:
        log(f"genius-dub mix targets {legacy} replaced by delivery specs")
    name = a.spec or m.get("spec", "web"); spec = SPECS[name]
    spans = predub(d)
    gated = bool(spec.get("gated") and spans)
    if spec.get("gated") and not spans:
        log("no spoken line placed: measuring the whole programme instead of dialogue only")
    gain = spec["lufs"] - sum_lufs(d, spans if gated else None)
    stems, out = P(d, "out/stems"), P(d, "out"); stems.mkdir(parents=True, exist_ok=True)
    base = slug(d); master = stems / f"{base}_master.wav"
    for _ in range(3):  # the limiter can pull the loudness down a little: correct and render again
        render_master(d, gain, spec["tp"], master)
        meas = loudness(master, spans if gated else None)
        if abs(meas["lufs"] - spec["lufs"]) <= 0.3:
            break
        gain += spec["lufs"] - meas["lufs"]
    st = P(d, "work/stems")
    ffmpeg(*[x for g in "DMEX" for x in ("-i", st / f"pre_{g}.wav")], "-filter_complex",
           f"[0:a]volume={gain:.2f}dB[D];[1:a]volume={gain:.2f}dB,asplit[M][m];[2:a]volume={gain:.2f}dB,asplit[E][e];"
           f"[3:a]volume={gain:.2f}dB[x];[m][e][x]amix=inputs=3:normalize=0[ME]",
           *[x for g in ("D", "M", "E", "ME") for x in ("-map", f"[{g}]", "-c:a", "pcm_s24le", stems / f"{base}_{g}.wav")])
    video = out / f"{base}_mix.mp4"
    clip = P(d, d["clip"])  # frame n shows at n/fps + the picture's start time: start the sound there too
    v0 = run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=start_time",
              "-of", "csv=p=0", clip]).stdout.strip()
    ffmpeg("-i", clip, "-itsoffset", v0 if re.match(r"^-?[\d.]+$", v0) else "0", "-i", master,
           "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", video)
    ok = abs(meas["lufs"] - spec["lufs"]) <= spec["tol"] and meas["true_peak"] <= spec["tp"]
    m["spec"] = name
    m["measured"] = {"spec": name, "lufs": meas["lufs"], "true_peak": meas["true_peak"], "gain_db": round(gain, 2),
                     "dialogue_gated": gated, "pass": ok}
    save(d)
    print(json.dumps({"out": str(video), "master": str(master), "stems": [f"{base}_{g}.wav" for g in ("D", "M", "E", "ME")],
                      "spec": f"{name}: {spec['lufs']} ±{spec['tol']} LU, TP ≤ {spec['tp']} dBTP ({spec['label']})",
                      "lufs": meas["lufs"], "true_peak": meas["true_peak"], "dialogue_gated": gated,
                      "result": "PASS" if ok else "FAIL", "beds": [b["id"] for b in d["beds"] if bed_file(d, b).exists()]},
                     ensure_ascii=False))


def cmd_check(a) -> None:
    check(load(a.project), "final")
