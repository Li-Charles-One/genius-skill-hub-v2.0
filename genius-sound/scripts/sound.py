#!/usr/bin/env python3
"""Genius Sound: film sound post-production for one clip, one module at a time or end to end.

  sound.py <module> <action> <project> ...   modules: spot, dialogue, foley, sfx, music, mix, deliver
  sound.py --check | env <audio>

Audio generation and ASR go through the genius-voice skill; shots come from genius-footage. Stdlib only, plus
ffmpeg/ffprobe. Subtitles belong to genius-subtitle.
Failures print `Error [CODE]: ...` to stderr and exit with EXIT_CODES[CODE].
"""
from __future__ import annotations

import argparse, json, platform, shutil, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import core, deliver, dialogue, mix, spot  # noqa: E402
from core import EXIT_CODES, SoundError, envelope, gen_beds, gen_cues, load, place, P, cue_kind  # noqa: E402


def foley_place(a) -> None:
    d = load(a.project)
    rows = place(d, [c for c in d["cues"] if cue_kind(c) == "foley"], P(d, "work/stems/foley.wav"))
    if rows is None:
        raise SoundError("INPUT_NOT_FOUND", "no foley cue has `at` / `at_frame` yet")
    print(json.dumps({"out": str(P(d, "work/stems/foley.wav")), "events": len(rows)}))


def selfcheck() -> None:
    res = {"ffmpeg": shutil.which("ffmpeg"), "ffprobe": shutil.which("ffprobe")}
    vp = core.sibling("genius-voice", "scripts/voice.py"); res["genius_voice"] = str(vp) if vp else None
    fp = core.sibling("genius-footage", "scripts/footage.py"); res["genius_footage"] = str(fp) if fp else None
    res["specs"] = {k: f"{v['lufs']} ±{v['tol']} LU, TP ≤ {v['tp']}" for k, v in mix.SPECS.items()}
    res["ok"] = bool(res["ffmpeg"] and res["ffprobe"] and vp)
    res["os"] = platform.system()
    print(json.dumps(res, ensure_ascii=False, indent=1))
    if not res["ok"]:
        sys.exit(2)


def gen_args(s) -> None:
    s.add_argument("project"); s.add_argument("--only", help="comma-separated cue / take / bed ids")
    s.add_argument("--force", action="store_true", help="regenerate files that exist")
    s.add_argument("--dry-run", action="store_true", help="print prompts, call nothing")


def build() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="sound.py", description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="check ffmpeg, sibling skills, delivery specs")
    mods = ap.add_subparsers(dest="module")

    def module(name, help_):
        m = mods.add_parser(name, help=help_); return m.add_subparsers(dest="action")

    s = mods.add_parser("env", help="loudness envelope of any audio file"); s.add_argument("file")
    s.add_argument("--window", type=float, default=1.0)
    s.set_defaults(fn=lambda a: print(envelope(a.file, a.window)))

    m = module("spot", "定点: project, frame grids, cue sheet")
    s = m.add_parser("init"); s.add_argument("clip"); s.add_argument("--dir"); s.add_argument("--title")
    s.add_argument("--language", default="en"); s.add_argument("--force", action="store_true"); s.set_defaults(fn=spot.cmd_init)
    s = m.add_parser("grid"); s.add_argument("project"); g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--shot"); g.add_argument("--frames", help="A-B"); s.add_argument("--crop", help="W:H:X:Y")
    s.add_argument("--step", type=int, default=1); s.add_argument("--cols", type=int, default=10)
    s.add_argument("--width", type=int, default=192); s.add_argument("--name")
    s.add_argument("--motion", action="store_true", help="per-frame motion in the crop and candidate contact frames")
    s.set_defaults(fn=spot.cmd_grid)
    s = m.add_parser("sheet"); s.add_argument("project"); s.set_defaults(fn=spot.cmd_sheet)

    m = module("dialogue", "对白&旁白: lines, narration, lip sync")
    s = m.add_parser("gen"); gen_args(s)
    s.set_defaults(fn=lambda a: gen_cues(load(a.project), core.DIALOGUE_KINDS, a))
    s = m.add_parser("place"); s.add_argument("project"); s.set_defaults(fn=dialogue.cmd_place)
    s = m.add_parser("check"); s.add_argument("project"); s.add_argument("what", choices=["takes", "stem"])
    s.set_defaults(fn=dialogue.cmd_check)

    m = module("foley", "拟音: sounds synced to on-screen action")
    s = m.add_parser("gen"); gen_args(s); s.set_defaults(fn=lambda a: gen_cues(load(a.project), {"foley"}, a))
    s = m.add_parser("place"); s.add_argument("project"); s.set_defaults(fn=foley_place)

    m = module("sfx", "音效&环境: hard / design effects and ambience beds")
    s = m.add_parser("gen"); gen_args(s); s.set_defaults(fn=lambda a: gen_beds(load(a.project), {"sfx", "amb"}, a))

    m = module("music", "配乐: score and source music beds")
    s = m.add_parser("gen"); gen_args(s); s.set_defaults(fn=lambda a: gen_beds(load(a.project), {"music"}, a))

    m = module("mix", "混录&母带: DME predub, ducking, delivery spec, stems, M&E")
    s = m.add_parser("master"); s.add_argument("project"); s.add_argument("--spec", choices=list(mix.SPECS))
    s.set_defaults(fn=mix.cmd_master)
    s = m.add_parser("check"); s.add_argument("project"); s.set_defaults(fn=mix.cmd_check)

    m = module("deliver", "交付: package the sound project")
    s = m.add_parser("pack"); s.add_argument("project"); s.add_argument("--dest"); s.set_defaults(fn=deliver.cmd_pack)
    return ap


def main(argv=None) -> int:
    ap = build(); a = ap.parse_args(argv)
    try:
        if a.check:
            selfcheck(); return 0
        if not hasattr(a, "fn"):
            ap.print_help(); return 1
        a.fn(a); return 0
    except SoundError as e:
        print(f"Error [{e.code}]: {e}", file=sys.stderr)
        return EXIT_CODES.get(e.code, 1)


if __name__ == "__main__":
    sys.exit(main())
