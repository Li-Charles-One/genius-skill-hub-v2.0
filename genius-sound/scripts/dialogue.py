"""Dialogue & narration: place lines into the dialogue stem and check takes, sync and intelligibility by ASR."""
from __future__ import annotations

import json

from core import (SoundError, P, asr, cue_kind, is_effort, load, place, slug, toks, DIALOGUE_KINDS)


def place_dialogue(d: dict) -> list[dict] | None:
    """work/stems/dialogue.wav holds every voice and narration cue; efforts.wav repeats the non-verbal ones for the M&E."""
    rows = place(d, [c for c in d["cues"] if cue_kind(c) in DIALOGUE_KINDS], P(d, "work/stems/dialogue.wav"))
    place(d, [c for c in d["cues"] if is_effort(c)], P(d, "work/stems/efforts.wav"))
    return rows


def cmd_place(a) -> None:
    d = load(a.project); rows = place_dialogue(d)
    if rows is None:
        raise SoundError("INPUT_NOT_FOUND", "no dialogue or narration cue has `at` / `at_frame` yet")
    print(json.dumps({"out": str(P(d, "work/stems/dialogue.wav")), "events": len(rows),
                      "efforts": P(d, "work/stems/efforts.wav").exists()}))


def cue_start(d: dict, c: dict) -> float:
    return c["window"][0] / d["video"]["fps"] if c.get("window") else float(c.get("at", 0))


def check(d: dict, what: str) -> None:
    """takes: does each take say its line. stem: does each line land on its window. final: is it heard in the mix."""
    spoken = [c for c in d["cues"] if c.get("line") and cue_kind(c) in DIALOGUE_KINDS]
    report = []
    if what == "takes":
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
        media = P(d, "work/stems/dialogue.wav") if what == "stem" else P(d, f"out/{slug(d)}_mix.mp4")
        if not media.exists():
            raise SoundError("INPUT_NOT_FOUND", f"{media} not found (run `dialogue place` / `mix master` first)")
        words = [w for s in asr(d, media, what)["segments"] for w in s.get("words", [])]
        for c in spoken:
            exp = cue_start(d, c); want = toks(c["line"])
            near = [w for w in words if exp - 1.0 <= w["start"] <= exp + 1.5 + 0.3 * len(want)]
            have = [t for w in near for t in toks(w["text"])]
            hit = [w for w in near if toks(w["text"])[:1] == want[:1]] or near[:1]
            got = hit[0]["start"] if hit else None
            cover = len(set(want) & set(have)) / max(len(set(want)), 1)
            delta = None if got is None else round(got - exp, 2)
            heard = " ".join(w["text"] for w in near)
            off = c.get("offscreen") or cue_kind(c) == "narration"
            if what == "stem":
                lo, hi = (-0.5, 0.5) if off else (-0.12, 0.18)  # lips visible: audio early hurts more
                bad = delta is None or delta < lo or delta > hi
                tag = "CHECK" if bad else ("OK/OS" if off else "OK   ")
                print(f"{tag} {c['id']:5s} expect {exp:6.2f}s  asr {got if got is not None else '—':>6}  "
                      f"Δ {delta if delta is not None else '—':>5}  {c['line']}")
            else:
                bad = cover < 0.5
                tag = "OK   " if not bad else ("MISHEARD" if near else "MASKED")
                print(f"{tag:8s} {c['id']:5s} {exp:6.2f}s  heard {cover:4.0%}  want: {c['line']}  |  asr: {heard or '—'}")
            report.append({"id": c["id"], "expect": exp, "asr_start": got, "delta": delta, "coverage": round(cover, 2),
                           "asr": heard, "flag": bad})
        if what == "stem":
            print("ASR word starts run ~0.05–0.1s late; nudge `at` by -Δ only for CHECK lines (OS = off screen or narration, ±0.5s)")
        else:
            print("MASKED = nothing heard: raise the line or lower/mute the bed under it (beds[].mutes). "
                  "MISHEARD = speech heard but other words: usually a whisper or pitched voice; compare with `dialogue check stem`")
    P(d, f"work/checks/check_{what}.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_check(a) -> None:
    check(load(a.project), a.what)
