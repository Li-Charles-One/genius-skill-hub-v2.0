#!/usr/bin/env python3
"""
Genius Footage — AG_FOOTAGE/1.1 brief for one clip (`<clip>.footage.md` + `.footage.json` + `.footage/`).

    python3 footage.py <clip> [--script FILE] [--model M] [--output text|json]
    python3 footage.py --check

Steps: measure.py (cuts frame by frame) → storyboard check of doubtful cuts → per-shot description from
storyboards → asr.py, Doubao ASR with speakers (words → frames, cut points) → one whole-clip request where
the model answers with IDs only (S001, U001, P1, G01) → IDs converted to frames and timecode → validate.
Speech via asr.py (DOUBAO_API_KEY); models via client.py.
Protocol: ArtisticCut/AG_FOOTAGE.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from bisect import bisect_left, bisect_right
from datetime import datetime
from pathlib import Path

import asr
import client
import measure
import storyboard
from asr import SpeechError
from client import FootageError

HERE = Path(__file__).resolve().parent
PROTOCOL = "AG_FOOTAGE/1.1"
CUT_GAP, JOINED_GAP = 4, 2     # frames: a pause ≥4 is a clean cut; <2 at punctuation is run-together
PUNCT = set("，。！？；：、,.!?;:…—")


def audio_info(src: str) -> dict:
    data = json.loads(measure.run(["ffprobe", "-v", "error", "-select_streams", "a:0", "-show_entries",
                                   "stream=codec_name,sample_rate,channels", "-of", "json", src]).stdout)
    a = (data.get("streams") or [{}])[0] if data.get("streams") else {}
    return {"codec": a.get("codec_name"), "sample_rate": int(a["sample_rate"]) if a.get("sample_rate") else None,
            "channels": a.get("channels")}


def _first(seek: list, t: float) -> int:
    """Frame on screen at time t (rounds down, so the first syllable is never cut)."""
    return max(0, bisect_right(seek, t) - 1)


def _last(seek: list, t: float, first: int) -> int:
    """Last frame that still overlaps speech ending at t (rounds up, so the last syllable is kept)."""
    return max(first, bisect_left(seek, t) - 1)


def utterances(asr: dict, seek: list, shots: list, n: int) -> list[dict]:
    """ASR segments → U001… with frame ranges. seek = measure.frame_times(src, for_seek=True): ASR time
    counts from the container start, like ffmpeg -ss."""
    out = []
    for seg in sorted((s for s in asr.get("segments", []) if s.get("text")), key=lambda s: s["start"]):
        words = []
        for w in seg.get("words") or []:
            a = min(_first(seek, w["start"]), n - 1)
            words.append({"text": w["text"], "first": a, "last": min(_last(seek, w["end"], a), n - 1),
                          "start": w["start"], "end": w["end"]})
        first = min(_first(seek, seg["start"]), n - 1)
        last = min(_last(seek, seg["end"], first), n - 1)
        u = {"id": f"U{len(out) + 1:03d}", "first": first, "last": last, "text": seg["text"],
             "speaker": seg.get("speaker"), "words": words,
             "shots": [s["id"] for s in shots if s["first"] <= last and s["last"] >= first]}
        for k in ("emotion", "gender", "speech_rate"):
            if seg.get(k) is not None:
                u[k] = seg[k]
        out.append(u)
    return out


def _boundaries(u: dict) -> list[tuple[int, bool]]:
    """(index of the word before a boundary, punctuation there?) for every gap between words."""
    text, pos, ends = u["text"], 0, []
    for w in u["words"]:
        at = text.find(w["text"], pos)
        if at == -1:  # ASR text and words disagree: fall back to no punctuation info
            return [(k, False) for k in range(len(u["words"]) - 1)]
        pos = at + len(w["text"])
        ends.append(pos)
    starts = [text.find(w["text"], e) for w, e in zip(u["words"][1:], ends)]
    return [(k, any(c in PUNCT for c in text[ends[k]:starts[k]])) for k in range(len(u["words"]) - 1)]


def cut_points(utts: list, n: int) -> None:
    """Adds u["cuts"] = {"before": (a, b) | None, "after": (a, b) | None, "inside": [(a, b, next word)],
    "joined": [next word]} per AG_FOOTAGE section 5.2 / 8."""
    for i, u in enumerate(utts):
        prev_end = utts[i - 1]["last"] if i else -1
        next_start = utts[i + 1]["first"] if i + 1 < len(utts) else n
        inside, joined = [], []
        for k, punct in _boundaries(u):
            a, b = u["words"][k]["last"] + 1, u["words"][k + 1]["first"] - 1
            gap = b - a + 1
            if gap >= CUT_GAP:
                inside.append((a, b, u["words"][k + 1]["text"]))
            elif punct and gap < JOINED_GAP:
                joined.append(u["words"][k + 1]["text"])
        u["cuts"] = {"before": (prev_end + 1, u["first"] - 1) if u["first"] - 1 >= prev_end + 1 else None,
                     "after": (u["last"] + 1, next_start - 1) if next_start - 1 >= u["last"] + 1 else None,
                     "inside": inside, "joined": joined}


# ── IDs from the model ───────────────────────────────────────────────────

def id_range(spec: str, prefix: str) -> list[str]:
    """'S003–S006' / 'S003-S006' / 'S003' / 'S003, S007' → ['S003', …]."""
    out = []
    for part in re.split(r"[,，、\s]+", str(spec).strip()):
        m = re.fullmatch(rf"{prefix}(\d+)(?:\s*[–\-~至到]\s*{prefix}?(\d+))?", part)
        if m:
            a, b = int(m.group(1)), int(m.group(2) or m.group(1))
            width = 3 if prefix in ("S", "U") else (2 if prefix == "G" else 1)
            out += [f"{prefix}{k:0{width}d}" for k in range(a, b + 1)]
    return out


def span(ids: list[str], table: dict) -> tuple[int, int] | None:
    rows = [table[i] for i in ids if i in table]
    return (min(r["first"] for r in rows), max(r["last"] for r in rows)) if rows else None


# ── Render ───────────────────────────────────────────────────────────────

def _cell(v) -> str:
    return str(v if v not in (None, "") else "").replace("|", "/").replace("\n", " ")


def _short_ids(ids: list[str]) -> str:
    """['S001','S002','S003','S007'] → 'S001–S003, S007'."""
    if not ids:
        return ""
    prefix, width = ids[0][0], len(ids[0]) - 1
    nums = sorted(int(i[1:]) for i in ids)
    runs, a = [], nums[0]
    for x, y in zip(nums, nums[1:] + [None]):
        if y != x + 1:
            runs.append(f"{prefix}{a:0{width}d}" + (f"–{prefix}{x:0{width}d}" if x != a else ""))
            a = y
    return ", ".join(runs)


def build(r: dict, utts: list, ov: dict, asr_note: str | None, tools: dict, fingerprint: str,
          generated: str, audio: dict) -> dict:
    """Assemble the protocol document (the .footage.json body) from the parts."""
    shots = {s["id"]: s for s in r["shots"]}
    umap = {u["id"]: u for u in utts}
    people = ov.get("people") or []
    spk = {str(sp).lstrip("Ss"): p["id"] for p in people for sp in (p.get("speakers") or [])}
    for u in utts:
        u["person"] = spk.get(str(u.get("speaker")))
    segments = []
    for g in ov.get("segments") or []:
        ids = id_range(g.get("shots", ""), "S")
        sp = span(ids, shots)
        if sp:
            segments.append({"id": g.get("id"), "shots": ids, "first": sp[0], "last": sp[1],
                             **{k: g.get(k, "") for k in ("content", "emotion", "use")}})
    uncertain = list(ov.get("uncertain") or [])
    for s in r["suspects"]:
        if "check" not in s:
            uncertain.append(f"疑似切点未复核：f{s['first']}–f{s['last']}（{s['kind']}）")
        elif s["check"] == "unsure":
            uncertain.append(f"疑似切点拿不准：f{s['first']}–f{s['last']}（{s['kind']}；{s['reason']}）")
    for w in ov.get("suspect_words") or []:
        uncertain.append(f"可能听错的词：{w.get('u')} “{w.get('heard')}” → 可能是 “{w.get('likely')}”（依据：{w.get('evidence')}）")
    for s in r["shots"]:
        if "desc" not in s:
            uncertain.append(f"{s['id']} 缺少描述")
    if asr_note:
        uncertain.append(f"台词缺失：{asr_note}")
    doc = {"protocol": PROTOCOL, "file": Path(r["file"]).name, "fingerprint": fingerprint, "generated": generated,
           "tools": tools,
           "video": {k: r[k] for k in ("width", "height", "codec", "fps", "fps_rational", "frames", "duration",
                                       "timecode_start", "drop_frame")},
           "audio": audio, "summary": ov.get("summary", ""), "footage": ov.get("footage", ""), "people": people, "segments": segments,
           "shots": r["shots"], "utterances": utts, "highlights": ov.get("highlights") or {},
           "uncertain": uncertain, "suspects": r["suspects"], "storyboards": r.get("storyboards", []),
           "warnings": r.get("warnings", [])}
    doc["counts"] = {"shots": len(r["shots"]), "utterances": len(utts), "people": len(people), "segments": len(segments)}
    doc["review"] = {"unresolved_suspects": sum(s.get("check", "unsure") == "unsure" for s in r["suspects"]),
                     "uncertain_words": len(ov.get("suspect_words") or []),
                     "missing_descriptions": sum("desc" not in s for s in r["shots"])}
    doc["validation"] = validate(doc)
    doc["status"] = "ok" if not doc["validation"] and not any(doc["review"].values()) and not asr_note else "needs_review"
    return doc


def render_md(doc: dict, md_dir: Path) -> str:
    v, tc = doc["video"], _tc(doc)
    rel = lambda p: os.path.relpath(p, md_dir)
    head = {k: doc[k] for k in ("protocol", "file", "fingerprint", "generated", "tools", "video", "audio",
                                "counts", "review", "status")}
    L = ["---"] + [f"{k}: {json.dumps(val, ensure_ascii=False)}" for k, val in head.items()] + ["---", ""]
    L += [f"# {doc['file']}", "", "## 1. 概览", "", doc["summary"] or "（全片分析未完成）", ""]
    if doc["footage"]:
        L += [f"画面类型：{doc['footage']}", ""]

    L += ["## 2. 人物", "", "| 人物 | 外观 | 身份 | 说话人 | 出场镜头 |", "|---|---|---|---|---|"]
    for p in doc["people"]:
        L.append(f"| {p.get('id')} | {_cell(p.get('appearance'))} | {_cell(p.get('identity'))} | "
                 f"{', '.join('S' + str(s).lstrip('Ss') for s in p.get('speakers') or []) or '—'} | "
                 f"{_short_ids(id_range(p.get('shots', ''), 'S'))} |")

    L += ["", "## 3. 分段", "", "| 分段 | 镜头 | 帧 | 时间码 | 内容 | 情绪 | 适合用作 |", "|---|---|---|---|---|---|---|"]
    for g in doc["segments"]:
        L.append(f"| {g['id']} | {_short_ids(g['shots'])} | f{g['first']}–f{g['last']} | {tc(g['first'])}–{tc(g['last'])} | "
                 f"{_cell(g['content'])} | {_cell(g['emotion'])} | {_cell(g['use'])} |")

    L += ["", "## 4. 镜头", "", "| 镜头 | 帧 | 时间码 入–出 | 时长 | 切入 | 用途 | 景别 | 角度 | 运镜 | 人物 | 场景 | 画面 | 表演 | 标记 |",
          "|" + "---|" * 14]
    for s in doc["shots"]:
        d = s.get("desc", {})
        via = s["via"] + (f" (f{s['transition'][0]}–f{s['transition'][1]})" if "transition" in s else "")
        L.append(f"| {s['id']} | f{s['first']}–f{s['last']} | {s['tc_in']}–{s['tc_out']} | {s['end'] - s['start']:.2f}s | {via} | "
                 + " | ".join(_cell(d.get(k)) for k in ("roll", "shot_size", "angle", "movement", "people", "scene", "action",
                                                        "performance", "flags")) + " |")

    L += ["", "## 5. 台词", "", "| 台词 | 帧 | 时间码 | 说话人 | 镜头 | 文本 | 可下刀 |", "|---|---|---|---|---|---|---|"]
    for u in doc["utterances"]:
        c = u["cuts"]
        parts = ([f"前 f{c['before'][0]}–f{c['before'][1]}"] if c["before"] else ["前 无停顿"]) + \
                ([f"后 f{c['after'][0]}–f{c['after'][1]}"] if c["after"] else ["后 无停顿"]) + \
                [f"句中 f{a}–f{b}（“{w}”前）" for a, b, w in c["inside"]] + \
                [f"连读，不可切（“{w}”前）" for w in c["joined"]]
        who = u.get("person") or (f"S{u['speaker']}" if u.get("speaker") else "—")
        L.append(f"| {u['id']} | f{u['first']}–f{u['last']} | {tc(u['first'])}–{tc(u['last'])} | {who} | "
                 f"{_short_ids(u['shots'])} | {_cell(u['text'])} | {' · '.join(parts)} |")

    h = doc["highlights"]
    L += ["", "## 6. 亮点与问题", ""]
    L += [f"- 金句：{q.get('u')}（{q.get('person', '')}）——{_cell(q.get('why'))}" for q in h.get("quotes") or []]
    L += [f"- 最佳反应镜头：{b.get('s')}——{_cell(b.get('why'))}" for b in h.get("best_reaction") or []]
    L += [f"- 同一句拍了多遍：{' / '.join(t.get('us') or [])}，推荐 {t.get('pick')}（{_cell(t.get('why'))}）" for t in h.get("retakes") or []]
    L += [f"- 不可用：{x.get('shots')} {_cell(x.get('why'))}（判）" for x in h.get("unusable") or []]
    if not any(h.get(k) for k in ("quotes", "best_reaction", "retakes", "unusable")):
        L.append("- 无")

    L += ["", "## 7. 待确认", ""] + ([f"- {x}" for x in doc["uncertain"]] or ["- 无"])
    if doc["validation"]:
        L += [f"- 校验未通过：{x}" for x in doc["validation"]]
    if doc["storyboards"]:
        L += ["", "故事板：" + "、".join(f"[{Path(p).name}]({rel(p)})" for p in doc["storyboards"])]
    return "\n".join(L) + "\n"


def _tc(doc: dict):
    v = doc["video"]
    nominal = round(v["fps"])
    start, df = measure.tc_to_frames(v["timecode_start"], nominal) if v["timecode_start"] else (0, False)
    return lambda i: measure.frames_to_tc(start + i, nominal, df)


# ── Validate (AG_FOOTAGE section 7) ──────────────────────────────────────

def validate(doc: dict) -> list[str]:
    v, shots, utts, errs = doc["video"], doc["shots"], doc["utterances"], []
    n, tc, fps = v["frames"], _tc(doc), v["fps"]
    # 1. shots tile the clip, numbered without gaps
    if not shots or shots[0]["first"] != 0 or shots[-1]["last"] != n - 1:
        errs.append(f"镜头没有覆盖 f0–f{n - 1}")
    for k, s in enumerate(shots, 1):
        if s["id"] != f"S{k:03d}":
            errs.append(f"镜头编号不连续：{s['id']}")
        if k > 1 and s["first"] != shots[k - 2]["last"] + 1:
            errs.append(f"{s['id']} 与上一镜头不相接")
        # 2. timecode / seconds agree with frames
        if s["tc_in"] != tc(s["first"]) or s["tc_out"] != tc(s["last"]):
            errs.append(f"{s['id']} 时间码与帧号不一致")
        if abs(s["start"] - s["first"] / fps) > 1.5 / fps and not any("variable frame rate" in w for w in doc["warnings"]):
            errs.append(f"{s['id']} 秒数与帧号不一致")
    # 3. utterances inside the clip and on the shots they claim
    for u in utts:
        if not (0 <= u["first"] <= u["last"] < n):
            errs.append(f"{u['id']} 帧超出素材范围")
        elif u["shots"] != [s["id"] for s in shots if s["first"] <= u["last"] and s["last"] >= u["first"]]:
            errs.append(f"{u['id']} 标注的镜头与帧范围不符")
    # 4. segments: contiguous shots, no overlap, references exist
    ids = {s["id"] for s in shots} | {u["id"] for u in utts} | {p.get("id") for p in doc["people"]}
    prev = -1
    for g in doc["segments"]:
        nums = [int(x[1:]) for x in g["shots"]]
        if nums != list(range(nums[0], nums[0] + len(nums))):
            errs.append(f"{g['id']} 的镜头不连续")
        if g["first"] <= prev:
            errs.append(f"{g['id']} 与上一分段重叠")
        prev = g["last"]
    h = doc["highlights"]
    refs = [q.get("u") for q in h.get("quotes") or []] + [b.get("s") for b in h.get("best_reaction") or []] + \
           [x for t in h.get("retakes") or [] for x in (t.get("us") or []) + [t.get("pick")]]
    errs += [f"引用了不存在的编号 {x}" for x in refs if x and x not in ids]
    # 5. no estimates in precise fields (frames / timecode are generated, so check model-supplied ranges)
    errs += [f"{g['id']} 的镜头范围含估计值" for g in doc["segments"] if "~" in "".join(g["shots"])]
    # 6. every shot described or listed as uncertain
    errs += [f"{s['id']} 无描述且未列入待确认" for s in shots
             if "desc" not in s and not any(s["id"] in x for x in doc["uncertain"])]
    # 7. counts match the body
    if doc.get("counts") and doc["counts"]["shots"] != len(shots):
        errs.append("counts.shots 与镜头表不一致")
    return errs


# ── Shots: storyboard check of doubtful cuts, then one description per shot ──

LANGUAGE_RULE = (
    "\n\nOUTPUT LANGUAGE (mandatory): write the whole answer, headings included, in "
    "Simplified Chinese (简体中文). Quote on-screen text, spoken lines, names and brand "
    "names verbatim in their original language; do not translate quotes."
)
# Editing lexicon for shot descriptions (references/lexicon.md); edit the file, not the code.
_LEX = (Path(__file__).resolve().parent.parent / "references" / "lexicon.md").read_text(encoding="utf-8")
LEXICON = "\n\nEDITING LEXICON (structured fields use these Chinese names only):\n" + _LEX.split("\n---\n\n## 不收录")[0]
# The cut check keeps its own coarse categories: the lexicon's near-pairs (遮挡转场 / 遮挡穿过, 黑场 / 闪白)
# made verdicts flip between runs (emsmart 3 runs: 0/35 disagreements here, 5/35 with lexicon sections).
SHOT_CHECK_PROMPT = (
    "These images are storyboard cells around possible shot changes in one video. Each group X## is a run "
    "of exact frames in time order, X##-1 … X##-N: six frames each side of a one-frame jump, or nine frames "
    "per second across a sustained change. The time from the first to the last frame is given per group.\n"
    "For each group, look at the whole run as an editor would: what kind of picture it is, what changes, "
    "the first frame showing the change, and then your verdict — does a new shot start in this run?\n"
    "Editing conventions to weigh: a hard cut, jump cut, dissolve or wipe starts a new shot. Camera or "
    "subject movement, an effect appearing in the same composition (laser, sparks, light, smoke, CG "
    "elements), a single white or black flash frame, and a colour filter or grade change stay in the same "
    "shot. When the same composition has its content or object state replaced (common in CG), or the "
    "frames could honestly be read either way, answer unsure so a person decides.\n"
    "change, pick one: cut, jump-cut, dissolve, wipe, flash, effect, grade, camera-move, subject-move, "
    "cg-swap, collage, none, other.\n"
    'Return ONLY a JSON array: [{"id": "X01", "footage": "live | cg | motion-graphics | mixed", '
    '"change": "one value from the list", "at": "X01-7 (first frame of the change, null for none)", '
    '"verdict": "new shot | same shot | unsure", "what": "under 60 characters"}]. Keep footage, change, '
    "verdict and cell ids in English exactly as listed. Groups: {ids}" + LANGUAGE_RULE
)
CHECK_PER_SEC = 9  # frames per second for a sustained-change suspect
CHECK_SIDE = 6     # frames each side of a one-frame jump
# Storyboard sheets, not the video: shots and timing were measured locally (measure.py).
SHOT_PROMPT = (
    "These images are storyboard sheets of one video. Every cell is one exact frame, labelled at its "
    "top-left: S###a = first frame of shot S###, S###m = a middle frame (long shots only), "
    "S###b = last frame. Shot boundaries and timing were measured frame by frame and are correct: "
    "do not add, merge, renumber or re-time shots.\n"
    "Describe every shot listed below from its own frames. Infer camera movement by comparing a → m → b.\n"
    "Return ONLY a JSON array, one object per shot in the given order, keys exactly as written:\n"
    '{"id": "S001", "roll": "素材用途，词典第二节：A-roll / B-roll / 无法判断", '
    '"shot_size": "景别，词典第八节", '
    '"angle": "角度，词典第九节", '
    '"movement": "运镜，词典第七节，可用顿号组合；看不出写 无法判断", '
    '"people": "人数与外观特征，没有人写 无", "scene": "场景", '
    '"action": "画面：谁在哪里做什么", "performance": "情绪、动作、因果，没有人写 无", '
    '"flags": "废片/跑焦/打板/说错重来/最佳，以及词典第三节的速度与拍摄手段（正常速度不写），'
    '用顿号分隔，没有写空字符串"}\n'
    "Keep each value under 40 characters. The clip plays at {fps} fps; footage shot for slow motion "
    "usually has a high frame rate. Shots on these sheets: {ids}" + LEXICON + LANGUAGE_RULE
)
SHOT_FIELDS = ("roll", "shot_size", "angle", "movement", "people", "scene", "action", "performance", "flags")
SHOT_MIDDLE_SEC = 4.0  # shots at least this long get a middle frame on the storyboard


def _json(text: str, open_ch: str, close_ch: str):
    a, b = text.find(open_ch), text.rfind(close_ch)
    try:
        return json.loads(text[a:b + 1]) if a != -1 and b > a else None
    except ValueError:
        return None


def check_suspects(src: str, c: dict, r: dict, seek: list, out_dir: Path) -> None:
    """1. Suspects: a one-frame jump gets six frames each side, a sustained change nine frames per second
    across it. The model judges: what changes, on which cell, and whether a new shot starts there. A new shot
    starts on the cell it points to; unsure ones stay unresolved for review."""
    if not r["suspects"]:
        return
    last = r["frames"] - 1
    ids = {f"X{i:02d}": s for i, s in enumerate(r["suspects"], 1)}
    groups, span_of, cells = [], {}, {}  # cells: label → frame
    for x, s in ids.items():
        if s["kind"] == "weak-cut":
            frames = list(range(max(0, s["first"] - CHECK_SIDE), min(last, s["last"] + CHECK_SIDE) + 1))
        else:
            lo, hi = max(0, s["first"] - 1), min(last, s["last"] + 1)
            n = min(hi - lo + 1, max(CHECK_PER_SEC, round(CHECK_PER_SEC * (hi - lo + 1) / r["fps"])))
            frames = [lo + round(k * (hi - lo) / (n - 1)) for k in range(n)]
        groups.append((x, [(f"{x}-{k + 1}", f) for k, f in enumerate(frames)]))
        cells.update(groups[-1][1])
        span_of[x] = frames[-1] - frames[0]
    extra, spans = {}, {}
    for sheet, gids in storyboard.sheets(src, seek, r["fps"], groups, out_dir, "suspects"):
        r["storyboards"].append(str(sheet))
        print(f"[genius-footage] checking {len(gids)} suspects on {sheet.name}…", file=sys.stderr)
        listing = ", ".join(f"{x} ({span_of[x]} frames, {span_of[x] / r['fps']:.2f}s)" for x in gids)
        answer = _json(client.call(c, [str(sheet)], SHOT_CHECK_PROMPT.replace("{ids}", listing), 300), "[", "]")
        for item in answer if isinstance(answer, list) else []:
            s = ids.get(str(item.get("id")))
            verdict = str(item.get("verdict", "")).strip().lower()
            if not s or verdict not in ("new shot", "same shot", "unsure"):
                continue
            # The timeline stays measured: a one-frame jump shows every frame, so the model's cell is exact;
            # a sustained change shows every few frames, so it starts where measure.py found it.
            at = cells.get(str(item.get("at"))) if s["kind"] == "weak-cut" else s["first"]
            if verdict == "new shot" and at is None:  # a new shot the model cannot place goes to review
                verdict = "unsure"
            s.update(check=verdict, seen=str(item.get("change", "")).strip(), footage=item.get("footage", ""),
                     at=at, reason=item.get("what", ""))
            if verdict == "new shot" and at > 0:
                extra[at] = "storyboard"
                if s["kind"] != "weak-cut" and s["last"] > s["first"]:
                    spans[at] = (s["first"], s["last"])
    if extra:
        measure.add_boundaries(r, extra, spans)


def shots(src: str, c: dict, out_dir: Path) -> dict:
    """Frame-accurate shot list measured locally; the model only judges suspects and describes shots
    from labelled storyboard sheets, never times or counts them."""
    try:
        r = measure.measure(src)
    except measure.MeasureError as e:
        raise FootageError("DEPENDENCY_MISSING" if "not found on PATH" in str(e) else "UNSUPPORTED_FORMAT", str(e))
    seek = measure.frame_times(src, for_seek=True)
    print(f"[genius-footage] measured: {r['frames']} frames @ {r['fps']} fps, {r['shot_count']} shots, "
          f"{len(r['suspects'])} suspects", file=sys.stderr)
    r["storyboards"] = []
    check_suspects(src, c, r, seek, out_dir)

    # 2. Describe every shot from its first / (middle) / last frames.
    groups = []
    for s in r["shots"]:
        cells = [(s["id"] + "a", s["first"])]
        if s["frames"] >= SHOT_MIDDLE_SEC * r["fps"]:
            cells.append((s["id"] + "m", (s["first"] + s["last"]) // 2))
        if s["last"] != s["first"]:
            cells.append((s["id"] + "b", s["last"]))
        groups.append((s["id"], cells))
    by_id = {s["id"]: s for s in r["shots"]}
    for sheet, gids in storyboard.sheets(src, seek, r["fps"], groups, out_dir, "shots"):
        r["storyboards"].append(str(sheet))
        print(f"[genius-footage] describing {gids[0]}–{gids[-1]} on {sheet.name}…", file=sys.stderr)
        answer = _json(client.call(c, [str(sheet)], SHOT_PROMPT.replace("{ids}", ", ".join(gids)).replace("{fps}", f"{r['fps']:g}"), 300), "[", "]")
        for item in answer if isinstance(answer, list) else []:
            s = by_id.get(str(item.get("id")))
            if s:
                s["desc"] = {k: str(item.get(k, "")) for k in SHOT_FIELDS}
    missing = [s["id"] for s in r["shots"] if "desc" not in s]
    if missing:
        r["warnings"].append(f"no description returned for {', '.join(missing)}")
    return r


# ── Whole clip (model answers with IDs only; frames and timecode are computed) ──

OVERVIEW_PROMPT = (
    "You are logging one raw video clip for an editor. Watch the clip. Below are its shot list and "
    "transcript, measured frame by frame (IDs: S### shots, U### utterances; ASR speakers are 1, 2, …)."
    "{script}\n\nSHOTS\n{shots}\n\nTRANSCRIPT\n{utts}\n\n"
    "Return ONLY one JSON object with these keys. Refer to shots and lines ONLY by their IDs, never by time; "
    "use only IDs listed above.\n"
    '{"summary": "2–3 sentences: what this clip is, who, where, what is said",\n'
    ' "footage": "picture type of the whole clip, using 实拍 / CG / AI 生成 / 动态图形 / 定格动画 / 混合, '
    'e.g. 实拍为主，含 CG",\n'
    ' "people": [{"id": "P1", "appearance": "", "identity": "role, with evidence (badge, caption, what they say)", '
    '"speakers": ["1"], "shots": "S001–S012, S020"}],\n'
    ' "segments": [{"id": "G01", "shots": "S001–S006", "content": "", "emotion": "", "use": "what an editor could use it for"}],\n'
    ' "highlights": {"quotes": [{"u": "U014", "person": "P2", "why": ""}], "best_reaction": [{"s": "S023", "why": ""}], '
    '"retakes": [{"us": ["U007", "U009"], "pick": "U009", "why": ""}], "unusable": [{"shots": "S030–S031", "why": "跑焦/杂音/说错/打板…"}]},\n'
    ' "suspect_words": [{"u": "U003", "heard": "as transcribed", "likely": "correct form", '
    '"evidence": "script keyword / on-screen text in S004 / context"}],\n'
    ' "uncertain": ["anything you are unsure of; mark estimates with ~"]}\n'
    "Rules: P1, P2… in order of first appearance; map every ASR speaker to a person. Segments are runs of "
    "consecutive shots that cover all shots in order without overlap. Retakes: the same line said more than "
    "once. suspect_words: likely mishearings (homophones, names, brands, models) — propose, do not rewrite. "
    "Empty lists are fine."
)


def _overview(src: str, c: dict, r: dict, utts: list, script: str | None) -> dict:
    if r["duration"] > client.MAX_VIDEO_SEC:
        r["warnings"].append(f"clip longer than {client.MAX_VIDEO_SEC // 60} min: whole-clip overview skipped")
        return {}
    shot_lines = "\n".join(
        f"{s['id']} {s['tc_in']} {s['end'] - s['start']:.1f}s | "
        + " | ".join(s.get("desc", {}).get(k, "") for k in ("shot_size", "scene", "action")) for s in r["shots"])
    utt_lines = "\n".join(f"{u['id']} [{u.get('speaker') or '?'}] {u['shots'][0] if u['shots'] else ''} | {u['text']}"
                          for u in utts) or "(no transcript)"
    prompt = (OVERVIEW_PROMPT.replace("{script}", f"\n\nSCRIPT / KEYWORDS (correct spellings)\n{script}" if script else "")
              .replace("{shots}", shot_lines).replace("{utts}", utt_lines)) + LANGUAGE_RULE
    upload = client.video_proxy(src, r["duration"])
    print("[genius-footage] whole-clip overview…", file=sys.stderr)
    ov = _json(client.call(c, [upload], prompt, max(300, min(900, r["duration"] * 0.6))), "{", "}")
    if not isinstance(ov, dict) or not ov:
        r["warnings"].append("whole-clip overview returned no JSON")
        return {}
    return ov


def run(src: str, c: dict, script: str | None = None) -> dict:
    """Write <stem>.footage.md, <stem>.footage.json and <stem>.footage/ next to the clip."""
    clip = Path(src)
    base = clip.with_suffix("")
    if not os.access(clip.parent, os.W_OK):
        raise FootageError("UNSUPPORTED_FORMAT", f"cannot write the footage brief next to the clip: {clip.parent}")
    r = shots(src, c, Path(f"{base}.footage"))
    seek = measure.frame_times(src, for_seek=True)

    asr_note, utts, asr_model = None, [], None
    try:
        print("[genius-footage] transcribing (Doubao ASR)…", file=sys.stderr)
        speech = asr.transcribe(src)
        asr_model = speech.get("model")
        utts = utterances(speech, seek, r["shots"], r["frames"])
        cut_points(utts, r["frames"])
    except (SpeechError, ValueError) as e:
        asr_note = str(e)
        print(f"[genius-footage] {asr_note}", file=sys.stderr)

    ov = _overview(src, c, r, utts, script)
    doc = build(r, utts, ov, asr_note,
                {"measure": "genius-footage measure.py", "asr": asr_model, "storyboard": c["model"],
                 "overview": c["model"] if ov else None},
                client.fingerprint(src), datetime.now().astimezone().isoformat(timespec="seconds"),
                audio_info(src))
    md_path, json_path = Path(f"{base}.footage.md"), Path(f"{base}.footage.json")
    md_path.write_text(render_md(doc, md_path.parent), encoding="utf-8")
    json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return {"footage_md": str(md_path), "footage_json": str(json_path), "status": doc["status"],
            "counts": doc["counts"], "review": doc["review"], "validation": doc["validation"],
            "warnings": doc["warnings"]}


def render_result(res: dict) -> str:
    c, rv = res["counts"], res["review"]
    lines = [f"状态：**{res['status']}** · {c['shots']} 镜头 · {c['utterances']} 句台词 · {c['people']} 人 · {c['segments']} 段",
             f"说明书：`{res['footage_md']}`", f"数据：`{res['footage_json']}`"]
    if any(rv.values()):
        lines.append(f"待复核：未复核切点 {rv['unresolved_suspects']} · 可能听错的词 {rv['uncertain_words']} · "
                     f"缺描述镜头 {rv['missing_descriptions']}")
    lines += [f"校验未通过：{x}" for x in res["validation"]] + [f"⚠️ {w}" for w in res["warnings"]]
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────

VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".wmv", ".m4v", ".mxf"}


def main() -> None:
    parser = argparse.ArgumentParser(description="AG_FOOTAGE/1.1 footage brief for one clip")
    parser.add_argument("file", nargs="?", help="Local video file")
    parser.add_argument("--script", default=None, help="Script or keyword file (correct spellings of names, brands)")
    parser.add_argument("--model", "-m", default=None, help="Model override (default FOOTAGE_MODEL or gemini-4-argon-high)")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--check", action="store_true", help="Check ffmpeg, the model key and the ASR key")
    args = parser.parse_args()
    c = client.conf(args.model)
    try:
        if args.check:
            ff, asr_key = shutil.which("ffmpeg") and shutil.which("ffprobe"), client._env("DOUBAO_API_KEY")
            print(f"ffmpeg:       {shutil.which('ffmpeg') or 'MISSING'}\n"
                  f"model:        {c['model']} @ {c['base_url']} key={'yes' if c['api_key'] else 'no'}\n"
                  f"asr:          {asr.ASR_MODEL} key={'yes' if asr_key else 'no (no transcript)'}")
            ok = bool(ff and c["api_key"] and asr_key)
            print("ok" if ok else "NOT READY")
            sys.exit(0 if ok else 2)
        if not args.file:
            parser.error("file is required (unless --check)")
        if not Path(args.file).is_file():
            raise FootageError("INPUT_NOT_FOUND", f"File not found: {args.file}")
        if Path(args.file).suffix.lower() not in VIDEO_EXTENSIONS:
            raise FootageError("UNSUPPORTED_FORMAT", "footage needs a local video file")
        if not c["api_key"]:
            raise FootageError("PROVIDER_ERROR", "API key not found: set FOOTAGE_API_KEY (or CPA_API_KEY) in scripts/.env")
        res = run(args.file, c, Path(args.script).read_text(encoding="utf-8") if args.script else None)
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.output == "json"
              else f"## Footage\n\n{render_result(res)}")
    except FootageError as e:
        print(f"Error [{e.code}]: {e}", file=sys.stderr)
        sys.exit(client.EXIT_CODES.get(e.code, 1))
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
