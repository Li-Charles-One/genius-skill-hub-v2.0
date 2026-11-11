#!/usr/bin/env python3
"""
Offline self-test for genius-footage: no network, no model, no keys. Needs ffmpeg.

    python3 selftest.py

Builds a 7.4 s test clip (hard cut, fade through black, dissolve) and checks that measure.py puts the cuts on
the built frames, that storyboard.grab returns exactly the frames asked for (against one ffmpeg per frame),
the frame arithmetic of lines, cut points, talking-head marks and keep[], the overlay enter / leave wording,
client.ask / client.cached, and footage.run end to end with a scripted model and transcript. Run it after
editing any script here.
"""

from __future__ import annotations

import collections
import json
import re
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import asr
import client
import footage
import measure
import overlays
import storyboard

FPS, SIZE = 25, "320x180"
failures = []


def check(name: str, got, want) -> None:
    if got != want:
        failures.append(name)
        print(f"FAIL {name}\n  got  {got!r}\n  want {want!r}")


def build_clip(path: Path) -> None:
    """f0–49 moving test pattern | hard cut | f50–99 bars, fading to black | f100–184 fade in (f100–101 are
    still black), then a dissolve (f135–149) into another pattern. libx264 with B-frames, like most footage."""
    src = lambda name: ["-f", "lavfi", "-i", f"{name}=s={SIZE}:r={FPS}:d=2"]  # noqa: E731
    graph = ("[1]fade=t=out:st=1.5:d=0.5[b];[2]fade=t=in:st=0:d=0.5[c];"
             "[c][3]xfade=transition=fade:duration=0.6:offset=1.4[cd];[0][b][cd]concat=n=3[v]")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *src("testsrc2"), *src("smptebars"), *src("rgbtestsrc"),
                    *src("testsrc"), "-filter_complex", graph, "-map", "[v]", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", str(path)], check=True)


def one_frame(path: str, seek: list, frame: int, crop=None) -> bytes:
    """The reference grab: one ffmpeg per frame."""
    w, h = storyboard.CELL
    vf = (f"crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}," if crop else "") + \
        f"scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2"
    return subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0.0, seek[frame] - 0.5 / FPS):.6f}", "-i", path,
                           "-map", "0:v:0", "-frames:v", "1", "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                          capture_output=True).stdout


def test_measure_and_grab(tmp: Path) -> None:
    clip = str(tmp / "test.mp4")
    build_clip(Path(clip))
    r = measure.measure(clip)
    check("frames", r["frames"], 185)
    check("shot starts", [(s["first"], s["via"]) for s in r["shots"]], [(0, "start"), (50, "cut"), (102, "black")])
    check("dissolve is a suspect", [s["kind"] for s in r["suspects"] if s["first"] <= 149 and s["last"] >= 135], ["gradual"])
    proxy = tmp / "proxy.mp4"   # the whole-clip proxy from the same decode must not change what is measured
    both = measure.measure(clip, (client.PROXY_VF, client.proxy_output(500, client.PROXY_ENCODERS[-1], proxy)))
    check("measure with a second output", (both == r, proxy.stat().st_size > 0), (True, True))
    measure.add_boundaries(r, {135: "storyboard"})
    check("added boundary", [s["id"] for s in r["shots"] if s["first"] == 135], ["S004"])

    seek = measure.frame_times(clip, for_seek=True)
    crop = (40, 20, 160, 90)
    keys = [(f, None) for f in [*range(10, 23), 49, 50, 5, 100, 150, 184]] + [(f, crop) for f in (60, 61, 62)]
    got = storyboard.grab(clip, seek, FPS, keys)
    check("grab: every frame is the one asked for", [k for k in keys if got[k] != one_frame(clip, seek, *k)], [])
    check("grab: neighbouring frames differ", got[(10, None)] != got[(11, None)], True)


def test_lines() -> None:
    seek = [i / FPS for i in range(200)]
    shots = [{"id": "S001", "first": 0, "last": 49}, {"id": "S002", "first": 50, "last": 199}]
    speech = {"segments": [
        {"start": 1.01, "end": 1.99, "text": "你好，世界", "words": [{"start": 1.01, "end": 1.39, "text": "你好"},
                                                                 {"start": 1.81, "end": 1.99, "text": "世界"}]},
        {"start": 3.01, "end": 3.49, "text": "再见", "words": [{"start": 3.01, "end": 3.49, "text": "再见"}]}]}
    utts = footage.utterances(speech, seek, shots, 200)
    footage.cut_points(utts, 200)
    check("line frames", [(u["id"], u["first"], u["last"], u["shots"]) for u in utts],
          [("U001", 25, 49, ["S001"]), ("U002", 75, 87, ["S002"])])
    check("cut points", utts[0]["cuts"], {"before": (0, 24), "after": (50, 74), "inside": [(35, 44, "世界")], "joined": []})
    seg = lambda i, a, b, **k: {"id": i, "shots": ["S001"], "first": a, "last": b, **k}  # noqa: E731
    doc = {"video": {"frames": 200, "fps": 25.0, "timecode_start": None}, "utterances": [], "people": [],
           "highlights": {}, "warnings": [], "uncertain": [], "counts": {"shots": 1},
           "shots": [{"id": "S001", "first": 0, "last": 199, "start": 0.0, "tc_in": "00:00:00:00",
                      "tc_out": "00:00:07:24", "desc": {}}]}
    doc["segments"] = [seg("G01", 10, 50, us=["U001"]), seg("G02", 50, 90, us=["U002"])]
    check("segments over lines may share a frame", footage.validate(doc), [])
    doc["segments"] = [seg("G01", 10, 50), seg("G02", 50, 90)]
    check("segments over shots may not", footage.validate(doc), ["G02 与上一分段重叠"])
    doc["segments"] = [seg("G01", 10, 50, us=["U001"]), seg("G02", 49, 90, us=["U002"])]
    check("a real overlap of lines is still caught", footage.validate(doc), ["G02 与上一分段重叠"])
    check("id_range", footage.id_range("S003–S005, S007", "S"), ["S003", "S004", "S005", "S007"])
    check("_short_ids", footage._short_ids(["S003", "S004", "S005", "S007"]), "S003–S005, S007")


def test_talking_head() -> None:
    word = lambda text, k: {"text": text, "first": 10 * k, "last": 10 * k + 9}  # noqa: E731
    texts = ["嗯", "我们", "今天", "我们", "今天", "讲", "这个"]
    utts = [{"id": "U001", "text": "".join(texts), "words": [word(t, k) for k, t in enumerate(texts)]},
            {"id": "U002", "text": "好", "words": [{"text": "好", "first": 100, "last": 109}]}]
    marks = footage.speech_marks(utts, FPS)
    check("pause", marks["pauses"], [{"after": "U001", "before": "U002", "first": 70, "last": 99}])
    check("filler", marks["fillers"], [{"u": "U001", "word": "嗯", "first": 0, "last": 9}])
    check("restart", marks["restarts"], [{"u": "U001", "dropped": "我们今天", "first": 10, "last": 29, "retake": "我们"}])
    keep = [{"u": "U001", "from": "我们今天讲", "to": "这个"}, {"u": "U001", "from": "不存在", "to": ""}, {"u": "U002"}]
    pieces, edit, bad = footage.keep_frames(keep, utts, 200)
    check("keep pieces", [(p["first"], p["last"], p["text"]) for p in pieces], [(30, 81, "我们今天讲这个"), (94, 121, "好")])
    check("keep merged", [(e["first"], e["last"], e["keep"]) for e in edit], [(30, 121, ["K01", "K02"])])
    check("keep unmatched", len(bad), 1)


def test_timecode_and_overlays() -> None:
    check("drop-frame round trip", [fn for fn in range(0, 200000, 997)
                                    if measure.tc_to_frames(measure.frames_to_tc(fn, 30, True), 30)[0] != fn], [])
    shots = [{"first": 0, "last": 49}, {"first": 50, "last": 99}, {"first": 100, "last": 199}]
    t = {"in": 52, "out": 97, "review": []}
    overlays.relations(t, shots, FPS, 199, 5)   # edges snap to a cut inside their cell
    check("overlay on cuts", (t["in"], t["out"], t["enter"], t["leave"]), (50, 99, "随切点出现", "随镜头切走"))
    t = {"in": 60, "out": 80, "review": []}
    overlays.relations(t, shots, FPS, 199, 0)
    check("overlay inside a shot", (t["enter"], t["leave"]), ("切点 f50 后 10 帧出现", "在镜头内消失（这个镜头到 f99）"))


def test_client(tmp: Path) -> None:
    script = {"A": [client.FootageError("TIMEOUT", "slow"), '[{"id": "X01", "v": 1}]'],          # fails, then answers
              "B": ['[{"id": "X02", "v": 1}]', '[{"id": "X02", "v": 2}, {"id": "X03", "v": 2}]'],  # short, then whole
              "C": [client.FootageError("PROVIDER_ERROR", "down")] * 2}                          # fails twice
    seen, lock = collections.Counter(), threading.Lock()

    def fake_call(c, files, prompt, timeout):
        with lock:
            step = script[prompt][seen[prompt]]
            seen[prompt] += 1
        if isinstance(step, Exception):
            raise step
        return step

    real_call, real_dir, client.call, client.CACHE_DIR = client.call, client.CACHE_DIR, fake_call, tmp / "cache"
    try:
        failed = []
        answers = client.ask({}, [([], "A"), ([], "B"), ([], "C")], [["X01"], ["X02", "X03"], ["X09"]], failed)
        check("ask: re-asked answers", answers, [[{"id": "X01", "v": 1}],
                                                [{"id": "X02", "v": 1}, {"id": "X02", "v": 2}, {"id": "X03", "v": 2}], None])
        check("ask: failed twice", [e.code for e in failed], ["PROVIDER_ERROR"])
        runs = []
        make = lambda: runs.append(1) or {"n": len(runs)}  # noqa: E731
        check("cached", [client.cached(__file__, "t", make, __file__) for _ in range(2)], [{"n": 1}, {"n": 1}])
    finally:
        client.call, client.CACHE_DIR = real_call, real_dir


def test_run(tmp: Path) -> None:
    """A whole-clip request that times out still leaves a brief (needs_review); the rerun fills it in and
    reuses the cached cuts and transcript."""
    clip, state = str(tmp / "test.mp4"), {"overview": client.FootageError("TIMEOUT", "slow"), "asr": 0}

    def fake_call(c, files, prompt, timeout):
        if "possible shot changes" in prompt:
            return json.dumps([{"id": x, "change": "dissolve", "verdict": "new shot", "what": "叠化"}
                               for x in re.findall(r"(X\d+) \(", prompt)])
        if "Describe every shot" in prompt:
            ids = prompt.split("Shots on these sheets: ")[1].split("\n")[0].split(", ")
            return json.dumps([{"id": i, "shot_size": "全景", "scene": "测试图"} for i in ids])
        if isinstance(state["overview"], Exception):
            raise state["overview"]
        return state["overview"]

    def fake_transcribe(path):
        state["asr"] += 1
        return {"model": "scripted", "duration": 7.4, "segments": [
            {"start": 0.5, "end": 1.5, "text": "测试", "words": [{"start": 0.5, "end": 1.5, "text": "测试"}]}]}

    real = client.call, client.CACHE_DIR, asr.transcribe
    client.call, client.CACHE_DIR, asr.transcribe = fake_call, tmp / "cache", fake_transcribe
    try:
        res = footage.run(clip, {"model": "scripted"})
        doc = json.loads(Path(res["footage_json"]).read_text(encoding="utf-8"))
        check("run: timed-out overview", (res["status"], res["counts"]["shots"], res["counts"]["utterances"],
                                         any("全片分析缺失" in x for x in doc["uncertain"]),
                                         any("TIMEOUT" in w for w in res["warnings"])), ("needs_review", 4, 1, True, True))
        check("run: dissolve became a shot", [s["first"] for s in doc["shots"]], [0, 50, 102, 136])
        state["overview"] = json.dumps({"summary": "测试片", "footage": "动态图形", "people": [], "highlights": {},
                                        "segments": [{"id": "G01", "shots": "S001–S004", "content": "测试图"}]})
        res = footage.run(clip, {"model": "scripted"})
        check("run: rerun fills it in", (res["status"], res["counts"]["segments"], res["validation"], state["asr"]),
              ("ok", 1, [], 1))
    finally:
        client.call, client.CACHE_DIR, asr.transcribe = real


def main() -> int:
    with tempfile.TemporaryDirectory() as d:
        test_measure_and_grab(Path(d))
        test_lines()
        test_talking_head()
        test_timecode_and_overlays()
        test_client(Path(d))
        test_run(Path(d))
    print(f"FAILED: {', '.join(failures)}" if failures else "ok")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
