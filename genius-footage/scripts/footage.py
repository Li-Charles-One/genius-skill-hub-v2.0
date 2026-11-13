#!/usr/bin/env python3
"""
Genius Footage — AG_FOOTAGE/1.1 brief for one clip (`<clip>.footage.md` + `.footage.json` + `.footage/`).

    python3 footage.py <clip|url> [<clip|url> …] [--talking-head | --breakdown] [--jobs 6] [--script FILE]
    python3 footage.py --check

Steps: measure.py (cuts frame by frame) → storyboard check of doubtful cuts → per-shot description from
storyboards → asr.py, Doubao ASR with speakers (words → frames, cut points) → one whole-clip request where
the model answers with IDs only (S001, U001, P1, G01) → IDs converted to frames and timecode → validate.
--talking-head (口播): doubtful cuts are not checked; pauses, fillers and restarts come from word times; the
whole-clip request also returns keep[] (line ID + verbatim first / last words), converted here to frames.
--breakdown (拉片): a reference film; the whole-clip request answers how it is built (structure, editing,
picture and sound, packaging, takeaways) and rhythm figures are computed from the measured shots; several
films also get one comparison (拉片汇总). Several clips run --jobs at a time; model requests share one cap.
Speech via asr.py (DOUBAO_API_KEY); models via client.py; links via download.py. One failed model request
does not lose the clip: what is missing goes to 待确认 and the status is needs_review.
Protocol: AG_FOOTAGE/1.1 (the spec, AG_FOOTAGE.md, is kept in the ArtisticCut project, not in this package).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from bisect import bisect_left, bisect_right
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import asr
import client
import download
import measure
import storyboard
from asr import SpeechError
from client import FootageError

HERE = Path(__file__).resolve().parent
PROTOCOL = "AG_FOOTAGE/1.1"
CUT_GAP, JOINED_GAP = 4, 2     # frames: a pause ≥4 is a clean cut; <2 at punctuation is run-together
PUNCT = set("，。！？；：、,.!?;:…—")
# Talking head (口播)
TH_PAUSE_SEC = 0.8                 # dead air listed for the editor
TH_PAD_IN, TH_PAD_OUT = 6, 12      # frames kept before the first / after the last word, never into a neighbour
TH_MERGE = 20                      # consecutive kept pieces closer than this (frames) become one piece
FILLERS = set("嗯呃额啊哦唔")         # a filler only at a line start or right after punctuation
STUTTER = set("我你他她这那就是在跟")   # one-character words that, said twice in a row, are a stutter
TH_HINT = (50, 0.6)                # default mode: ≤2 measured shots, >50 suspects, speech >60% → suggest --talking-head
JOBS = 6                           # clips at once; their model requests share client.MAX_REQUESTS
_procs = None                      # several clips: cut measurement (pure Python, holds the GIL) runs in processes


class _TagStream:
    def __init__(self, stream):
        self._s = stream

    def write(self, text):
        tag = getattr(client.ctx, "tag", None)
        return self._s.write(text.replace("[genius-footage]", f"[genius-footage {tag}]") if tag else text)

    def __getattr__(self, name):
        return getattr(self._s, name)


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


# ── Talking head: marks from word times, keep[] → frames ─────────────────

def _norm(s: str) -> str:
    return re.sub(r"[^\w%×]", "", s)


def _chars(u: dict) -> tuple[str, list[int], list[int]]:
    """Normalised text of a line's words, the word owning each character, and each word's first character."""
    text, owner, off = "", [], []
    for k, w in enumerate(u["words"]):
        t = _norm(w["text"])
        off.append(len(text))
        text += t
        owner += [k] * len(t)
    return text, owner, off


def speech_marks(utts: list, fps: float) -> dict:
    """Dead air (≥TH_PAUSE_SEC), fillers and restarts inside a line, all from word frames; hints, not cuts."""
    words = [(u, w) for u in utts for w in u["words"]]
    gap = round(TH_PAUSE_SEC * fps)
    pauses = [{"after": a[0]["id"], "before": b[0]["id"], "first": a[1]["last"] + 1, "last": b[1]["first"] - 1}
              for a, b in zip(words, words[1:]) if b[1]["first"] - a[1]["last"] - 1 >= gap]
    fillers, restarts = [], []
    for u in utts:
        ws = u["words"]
        punct = dict(_boundaries(u))  # boundary after word k → punctuation there?
        fillers += [{"u": u["id"], "word": w["text"], "first": w["first"], "last": w["last"]}
                    for k, w in enumerate(ws) if w["text"] in FILLERS and (k == 0 or punct.get(k - 1))]
        text, owner, off = _chars(u)
        j = 1
        while j < len(ws):
            best = None  # (i, chars) of the longest earlier run the line starts over with at word j
            for i in range(max(0, j - 20), j):
                n = 0
                while off[j] + n < len(text) and off[i] + n < off[j] and text[off[i] + n] == text[off[j] + n]:
                    n += 1
                stutter = n == 1 and i == j - 1 and ws[i]["text"] in STUTTER and ws[j]["text"] == ws[i]["text"]
                if (n >= 3 or stutter) and (best is None or n > best[1]):
                    best = (i, n)
            if best:
                i = best[0]
                restarts.append({"u": u["id"], "dropped": "".join(w["text"] for w in ws[i:j]),
                                 "first": ws[i]["first"], "last": ws[j]["first"] - 1, "retake": ws[j]["text"]})
                j = owner[off[j] + best[1] - 1] + 1
            else:
                j += 1
    return {"pauses": pauses, "fillers": fillers, "restarts": restarts}


def keep_frames(keep: list, utts: list, n: int) -> tuple[list, list, list[str]]:
    """keep[] from the model (line ID + verbatim first / last words) → frame pieces and merged edit ranges.
    A repeated 'from' resolves to its last occurrence that still has 'to' after it (retakes come later)."""
    umap = {u["id"]: u for u in utts}
    allw = sorted((w for u in utts for w in u["words"]), key=lambda w: w["first"])
    pieces, bad = [], []
    for item in keep or []:
        u = umap.get(str(item.get("u")))
        if not u or not u["words"]:
            bad.append(f"精剪建议引用了不存在或无字级时间的台词 {item.get('u')}")
            continue
        text, owner, off = _chars(u)
        fr, to = _norm(str(item.get("from") or "")), _norm(str(item.get("to") or ""))
        starts = [k for k in range(len(text)) if text.startswith(fr, k)][::-1] if fr else [0]
        a = b = None
        for k in starts:
            e = text.find(to, off[owner[k]]) if to else len(text) - 1
            if e != -1:
                a, b = owner[k], owner[e + len(to) - 1] if to else len(u["words"]) - 1
                break
        if a is None or b < a:
            bad.append(f"精剪建议 {u['id']} 对不上原文：从“{item.get('from')}”到“{item.get('to')}”")
            continue
        w0, w1 = u["words"][a], u["words"][b]
        prev = max((w["last"] for w in allw if w["last"] < w0["first"]), default=-1)
        nxt = min((w["first"] for w in allw if w["first"] > w1["last"]), default=n)
        pieces.append({"id": f"K{len(pieces) + 1:02d}", "u": u["id"], "from": item.get("from") or "",
                       "to": item.get("to") or "", "why": item.get("why") or "",
                       "first": max(w0["first"] - TH_PAD_IN, prev + 1, 0), "last": min(w1["last"] + TH_PAD_OUT, nxt - 1, n - 1),
                       "text": "".join(w["text"] for w in u["words"][a:b + 1])})
    edit = []
    for p in pieces:
        e = edit[-1] if edit else None
        if e and e["first"] <= p["first"] and p["first"] - e["last"] - 1 < TH_MERGE:
            e["last"] = max(e["last"], p["last"])
            e["keep"].append(p["id"])
        else:
            edit.append({"id": f"E{len(edit) + 1:02d}", "keep": [p["id"]], "first": p["first"], "last": p["last"]})
    return pieces, edit, bad


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
          generated: str, audio: dict, marks: dict | None = None) -> dict:
    """Assemble the protocol document (the .footage.json body) from the parts.
    marks is set in talking-head mode: segments then run over lines (U), and keep[] becomes frames."""
    shots = {s["id"]: s for s in r["shots"]}
    umap = {u["id"]: u for u in utts}
    people = ov.get("people") or []
    spk = {str(sp).lstrip("Ss"): p["id"] for p in people for sp in (p.get("speakers") or [])}
    for u in utts:
        u["person"] = spk.get(str(u.get("speaker")))
    segments = []
    for g in ov.get("segments") or []:
        us = id_range(g.get("us", ""), "U") if marks is not None else []
        sp = span(us, umap) if us else span(id_range(g.get("shots", ""), "S"), shots)
        if sp:
            ids = [s["id"] for s in r["shots"] if s["first"] <= sp[1] and s["last"] >= sp[0]]
            segments.append({"id": g.get("id"), **({"us": us} if us else {}), "shots": ids, "first": sp[0], "last": sp[1],
                             **{k: g.get(k, "") for k in ("content", "emotion", "use")},
                             **({"function": g["function"]} if g.get("function") else {})})
    uncertain = list(ov.get("uncertain") or [])
    keep, edit, keep_bad = keep_frames(ov.get("keep"), utts, r["frames"]) if marks is not None else ([], [], [])
    uncertain += keep_bad
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
    if marks is not None:
        doc.update(mode="talking-head", speech_marks=marks, keep=keep, edit=edit)
    doc["counts"] = {"shots": len(r["shots"]), "utterances": len(utts), "people": len(people), "segments": len(segments)}
    doc["review"] = {"unresolved_suspects": sum(s.get("check", "unsure") == "unsure" for s in r["suspects"]),
                     "uncertain_words": len(ov.get("suspect_words") or []),
                     "missing_descriptions": sum("desc" not in s for s in r["shots"])}
    if marks is not None:
        doc["review"]["unmatched_keep"] = len(keep_bad) + (0 if keep or not utts else 1)
        if not keep and utts:
            uncertain.append("精剪建议缺失：全片分析没有返回 keep")
    doc["validation"] = validate(doc)
    doc["status"] = "ok" if not doc["validation"] and not any(doc["review"].values()) and not asr_note else "needs_review"
    return doc


def render_md(doc: dict, md_dir: Path) -> str:
    v, tc = doc["video"], _tc(doc)
    rel = lambda p: os.path.relpath(p, md_dir)
    head = {k: doc[k] for k in ("protocol", "mode", "file", "fingerprint", "generated", "tools", "video", "audio",
                                "counts", "review", "status") if k in doc}
    L = ["---"] + [f"{k}: {json.dumps(val, ensure_ascii=False)}" for k, val in head.items()] + ["---", ""]
    L += [f"# {doc['file']}", "", "## 1. 概览", "", doc["summary"] or "（全片分析未完成）", ""]
    if doc["footage"]:
        L += [f"画面类型：{doc['footage']}", ""]

    L += ["## 2. 人物", ""] + _people_table(doc)

    by_line = doc.get("mode") == "talking-head"
    L += ["", "## 3. 分段", "", f"| 分段 | {'台词' if by_line else '镜头'} | 帧 | 时间码 | 内容 | 情绪 | 适合用作 |",
          "|---|---|---|---|---|---|---|"]
    for g in doc["segments"]:
        L.append(f"| {g['id']} | {_short_ids(g.get('us') or g['shots'])} | f{g['first']}–f{g['last']} | {tc(g['first'])}–{tc(g['last'])} | "
                 f"{_cell(g['content'])} | {_cell(g['emotion'])} | {_cell(g['use'])} |")

    L += ["", "## 4. 镜头", ""] + _shot_table(doc)

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
    L += [f"- 画面事件：{x.get('u')}——{_cell(x.get('what'))}" for x in h.get("visual_events") or []]
    L += [f"- 不可用：{x.get('us') or x.get('shots')} {_cell(x.get('why'))}（判）" for x in h.get("unusable") or []]
    if not any(h.get(k) for k in ("quotes", "best_reaction", "visual_events", "retakes", "unusable")):
        L.append("- 无")

    L += ["", "## 7. 待确认", ""] + ([f"- {x}" for x in doc["uncertain"]] or ["- 无"])
    if doc["validation"]:
        L += [f"- 校验未通过：{x}" for x in doc["validation"]]
    if by_line:
        L += _render_talking_head(doc, tc)
    if doc["storyboards"]:
        L += ["", "故事板：" + "、".join(f"[{Path(p).name}]({rel(p)})" for p in doc["storyboards"])]
    return "\n".join(L) + "\n"


def _people_table(doc: dict) -> list[str]:
    L = ["| 人物 | 外观 | 身份 | 说话人 | 出场镜头 |", "|---|---|---|---|---|"]
    for p in doc["people"]:
        L.append(f"| {p.get('id')} | {_cell(p.get('appearance'))} | {_cell(p.get('identity'))} | "
                 f"{', '.join('S' + str(s).lstrip('Ss') for s in p.get('speakers') or []) or '—'} | "
                 f"{_short_ids(id_range(p.get('shots', ''), 'S'))} |")
    return L


def _shot_table(doc: dict) -> list[str]:
    L = ["| 镜头 | 帧 | 时间码 入–出 | 时长 | 切入 | 用途 | 景别 | 角度 | 运镜 | 人物 | 场景 | 画面 | 表演 | 标记 |",
         "|" + "---|" * 14]
    for s in doc["shots"]:
        d = s.get("desc", {})
        via = s["via"] + (f" (f{s['transition'][0]}–f{s['transition'][1]})" if "transition" in s else "")
        L.append(f"| {s['id']} | f{s['first']}–f{s['last']} | {s['tc_in']}–{s['tc_out']} | {s['end'] - s['start']:.2f}s | {via} | "
                 + " | ".join(_cell(d.get(k)) for k in ("roll", "shot_size", "angle", "movement", "people", "scene", "action",
                                                        "performance", "flags")) + " |")
    return L


def _render_talking_head(doc: dict, tc) -> list[str]:
    fps, kmap = doc["video"]["fps"], {k["id"]: k for k in doc["keep"]}
    total = sum(e["last"] - e["first"] + 1 for e in doc["edit"])
    L = ["", "## 8. 精剪建议", "",
         f"共 {len(doc['edit'])} 段，约 {total / fps:.1f}s（原 {doc['video']['duration']:.1f}s）。入点 = 首字 −{TH_PAD_IN} 帧、"
         f"出点 = 末字 +{TH_PAD_OUT} 帧，不压相邻字；同一素材间隔 <{TH_MERGE} 帧的相邻片段已合并。区间含首尾两帧。", "",
         "| 段 | 帧 | 时间码 | 时长 | 台词 | 保留内容 | 理由 |", "|---|---|---|---|---|---|---|"]
    for e in doc["edit"]:
        ks = [kmap[k] for k in e["keep"]]
        L.append(f"| {e['id']} | f{e['first']}–f{e['last']} | {tc(e['first'])}–{tc(e['last'])} | "
                 f"{(e['last'] - e['first'] + 1) / fps:.2f}s | {', '.join(dict.fromkeys(k['u'] for k in ks))} | "
                 f"{_cell('／'.join(k['text'] for k in ks))} | {_cell('；'.join(k['why'] for k in ks if k['why']))} |")
    m = doc["speech_marks"]
    sec = lambda a, b: f"{(b - a + 1) / fps:.1f}s"
    L += ["", "## 9. 口播标记（按字级时间算，供参考）", "",
          f"- 长停顿（≥{TH_PAUSE_SEC}s）{len(m['pauses'])} 处：" +
          ("、".join(f"f{p['first']}–f{p['last']}（{p['after']} 后，{sec(p['first'], p['last'])}）" for p in m["pauses"]) or "无"),
          f"- 语气词 {len(m['fillers'])} 处：" +
          ("、".join(f"{x['u']}“{x['word']}” f{x['first']}" for x in m["fillers"]) or "无"),
          f"- 句内重复起头 {len(m['restarts'])} 处：" +
          ("、".join(f"{x['u']} 弃“{x['dropped']}” f{x['first']}–f{x['last']}" for x in m["restarts"]) or "无")]
    return L


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
        # Two lines said without a pause share a frame (a line's start rounds down, its end rounds up),
        # so segments over lines (talking head) may share that one frame; segments over shots may not.
        if g["first"] < prev or (g["first"] == prev and not g.get("us")):
            errs.append(f"{g['id']} 与上一分段重叠")
        prev = g["last"]
    h = doc["highlights"]
    refs = [q.get("u") for q in h.get("quotes") or []] + [b.get("s") for b in h.get("best_reaction") or []] + \
           [x.get("u") for x in h.get("visual_events") or []] + \
           [x for t in h.get("retakes") or [] for x in (t.get("us") or []) + [t.get("pick")]]
    # 8. talking head: edit pieces inside the clip and in order of the merged ranges
    for e in doc.get("edit") or []:
        if not (0 <= e["first"] <= e["last"] < n):
            errs.append(f"精剪建议 {e['id']} 帧超出素材范围")
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
    pages, jobs = storyboard.sheets(src, seek, r["fps"], groups, out_dir, "suspects"), []
    for sheet, gids in pages:
        r["storyboards"].append(str(sheet))
        print(f"[genius-footage] checking {len(gids)} suspects on {sheet.name}…", file=sys.stderr)
        listing = ", ".join(f"{x} ({span_of[x]} frames, {span_of[x] / r['fps']:.2f}s)" for x in gids)
        jobs.append(([str(sheet)], SHOT_CHECK_PROMPT.replace("{ids}", listing)))
    for answer in client.ask(c, jobs, [g for _, g in pages], r["errors"]):
        for item in answer or []:
            s = ids.get(str(item.get("id")))
            verdict = str(item.get("verdict", "")).strip().lower()
            if not s or "check" in s or verdict not in ("new shot", "same shot", "unsure"):
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


def measured(src: str, duration: float) -> dict:
    """measure.py's result, cached per file. A first run on a clip writes the whole-clip proxy from the same
    decode: one pass over the source instead of two (four clips at once: 140–169 s → 81–90 s of decoding)."""
    def fresh() -> dict:
        go = lambda second: _procs.submit(measure.measure, src, second).result() if _procs else measure.measure(src, second)  # noqa: E731
        out, kbps = client.proxy_file(src, duration)
        if duration > client.MAX_VIDEO_SEC or out.is_file():
            return go(None)
        client.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        part = out.with_suffix(".part.mp4")
        try:
            r = go((client.PROXY_VF, client.proxy_output(kbps, client.PROXY_ENCODERS[0], part)))
        except measure.MeasureError:  # e.g. that encoder is missing: measure alone, video_proxy has the fallback
            part.unlink(missing_ok=True)
            return go(None)
        if part.is_file() and part.stat().st_size:
            part.replace(out)
        return r

    try:
        return client.cached(src, "measure", fresh, measure.__file__)
    except measure.MeasureError as e:
        raise FootageError("DEPENDENCY_MISSING" if "not found on PATH" in str(e) else "UNSUPPORTED_FORMAT", str(e))


def shots(src: str, c: dict, r: dict, out_dir: Path, seek: list, talking_head: bool = False) -> dict:
    """r = the shot list measured locally (measured()); the model only judges suspects and describes shots
    from labelled storyboard sheets, never times or counts them."""
    r["file"], r["errors"] = src, []  # errors: model requests that failed twice (client.ask)
    print(f"[genius-footage] measured: {r['frames']} frames @ {r['fps']} fps, {r['shot_count']} shots, "
          f"{len(r['suspects'])} suspects", file=sys.stderr)
    r["storyboards"] = []
    r["measured_shots"] = r["shot_count"]
    if talking_head:  # one take with a hand-held camera: weak suspects are shake, not cuts
        for s in r["suspects"]:
            s.update(check="skipped")
        if r["suspects"]:
            r["warnings"].append(f"口播模式：{len(r['suspects'])} 处弱疑似切点未核对，镜头只按测得的硬切划分")
    else:
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
    pages, jobs = storyboard.sheets(src, seek, r["fps"], groups, out_dir, "shots"), []
    for sheet, gids in pages:
        r["storyboards"].append(str(sheet))
        print(f"[genius-footage] describing {gids[0]}–{gids[-1]} on {sheet.name}…", file=sys.stderr)
        jobs.append(([str(sheet)], SHOT_PROMPT.replace("{ids}", ", ".join(gids)).replace("{fps}", f"{r['fps']:g}")))
    for answer in client.ask(c, jobs, [g for _, g in pages], r["errors"]):
        for item in answer or []:
            s = by_id.get(str(item.get("id")))
            if s and "desc" not in s:
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
# Talking head: one take of one person speaking. Segments run over lines; the model also proposes the edit.
_TH_SWAPS = [
    ('"segments": [{"id": "G01", "shots": "S001–S006",', '"segments": [{"id": "G01", "us": "U001–U012",'),
    ('"best_reaction": [{"s": "S023", "why": ""}], ',
     '"visual_events": [{"u": "U023", "what": "转身展示身后的车 / 低头看手机 / 捂嘴忘词 / 前后两遍画面跳动大，接缝宜推近"}], '),
    ('"unusable": [{"shots": "S030–S031", "why": "跑焦/杂音/说错/打板…"}]},\n',
     '"unusable": [{"us": "U030–U031", "why": "说错/忘词/杂音…"}]},\n'
     ' "keep": [{"u": "U010", "from": "first words kept, copied verbatim from that line; empty = line start", '
     '"to": "last words kept, verbatim; empty = line end", "why": "short reason"}],\n'),
    ("Segments are runs of consecutive shots that cover all shots in order without overlap.",
     "Segments are runs of consecutive lines (U) that cover all lines in order without overlap."),
]
TH_RULES = (
    "\n\nTALKING HEAD: this is one person speaking to camera in one take. keep is the tight edit an editor "
    "would cut, in playback order: one entry per kept piece; a line may give several pieces. Keep one take "
    "of each idea — the cleanest retake, usually the last complete one; drop abandoned starts, restarts inside "
    "a line, stutters, fillers, dead air, forgotten-line pauses and off-topic asides. Cut a line by giving "
    "from / to as words copied exactly from that line (at least 4 characters when the words repeat in the "
    "line). You may move a hook or an outro to where it belongs and say so in why. The marks below were "
    "measured from word times; use them as hints.\n\nMARKS\n{marks}"
)
OVERVIEW_PROMPT_TH = OVERVIEW_PROMPT
for _a, _b in _TH_SWAPS:
    assert _a in OVERVIEW_PROMPT_TH, _a
    OVERVIEW_PROMPT_TH = OVERVIEW_PROMPT_TH.replace(_a, _b)


def _marks_text(marks: dict, fps: float) -> str:
    p = [f"pause {x['after']}→{x['before']} {(x['last'] - x['first'] + 1) / fps:.1f}s" for x in marks["pauses"]]
    f = [f"filler {x['u']} “{x['word']}”" for x in marks["fillers"]]
    r = [f"restart {x['u']} drops “{x['dropped']}”" for x in marks["restarts"]]
    return "\n".join(p + f + r) or "(none)"


# ── Breakdown (拉片): how a reference film is built ──────────────────────

BREAKDOWN_PROMPT = (
    "You are breaking down a finished reference film for a director and an editor who want to learn how it "
    "was made (拉片). Watch the whole film. Below are its shot list and transcript, measured frame by frame "
    "(IDs: S### shots, U### utterances; ASR speakers are 1, 2, …), and rhythm figures computed from the "
    "measured shots.{script}\n\nSHOTS\n{shots}\n\nTRANSCRIPT\n{utts}\n\nRHYTHM (measured)\n{rhythm}\n\n"
    "Return ONLY one JSON object with these keys. Refer to shots and lines ONLY by their IDs (ranges like "
    "S001–S004 are fine), never by time; use only IDs listed above. Structure and storytelling matter most: "
    "be specific and concrete there, tie every claim to shots.\n"
    '{"summary": "2–3 sentences: what the film is, for whom, its one core message",\n'
    ' "genre": "类型与平台感：广告片 / 品牌短片 / 产品展示 / 剧情短片 / vlog / 口播 / 混剪 …，以及时长定位",\n'
    ' "footage": "picture type: 实拍 / CG / AI 生成 / 动态图形 / 定格动画 / 混合",\n'
    ' "people": [{"id": "P1", "appearance": "", "identity": "role in the story", "speakers": ["1"], "shots": "S001–S012"}],\n'
    ' "segments": [{"id": "G01", "shots": "S001–S006", "function": "叙事功能：钩子 / 建立 / 铺垫 / 冲突 / 转折 / '
    '高潮 / 产品露出 / 证明 / 行动号召 / 收尾 …", "content": "这一段讲了什么、给出了什么信息", "emotion": "", '
    '"use": "这一段用了什么拍法和剪法达到它的作用"}],\n'
    ' "structure": {"hook": {"shots": "S001–S003", "how": "前几秒靠什么抓住人，为什么有效"}, '
    '"arc": "整体叙事结构（如 问题→方案→证明→号召 / 三幕 / 反转 / 并列排比），信息按什么顺序递进、为什么这样排", '
    '"emotion_curve": "情绪怎么起伏，在哪些分段到顶、在哪里回落", '
    '"ending": {"shots": "S040–S042", "how": "结尾怎么收：落点、口号、行动号召、余味"}, '
    '"selling_points": [{"point": "卖点或核心信息", "shots": "S010–S014", "how": "怎么呈现出来的"}]},\n'
    ' "editing": {"pace": "节奏总评与变化，引用上面的节奏数据", '
    '"transitions": [{"shots": "S010–S011", "type": "硬切 / 匹配剪辑 / 遮挡转场 / 叠化 / 声音先入 …", "why": "效果"}], '
    '"music_sync": "剪辑点和音乐节拍、重音、台词的卡点关系", '
    '"techniques": [{"shots": "S020–S026", "what": "跳切 / 平行剪辑 / 重复 / 变速 / 蒙太奇 / 前后呼应 …，具体怎么用的"}]},\n'
    ' "language": {"shots_style": "景别、角度、运镜的组合规律（如 大远景建立后连续特写）", '
    '"light_color": "光线与调色", "sound": "配乐风格与变化、音效、环境声、人声处理、声音转场", '
    '"signature": [{"shots": "S015", "what": "最有记忆点的镜头及其拍法"}]},\n'
    ' "packaging": {"captions": "花字：字体、颜色、动效、位置、出现频率；没有写 无", "subtitles": "台词字幕样式；没有写 无", '
    '"graphics": "图形包装、logo、片头片尾卡；没有写 无"},\n'
    ' "takeaways": [{"what": "可以直接借鉴的一个做法", "shots": "S001–S003", "how": "怎么用到我们自己的片子里"}],\n'
    ' "highlights": {"quotes": [{"u": "U014", "person": "P2", "why": "为什么是金句"}]},\n'
    ' "suspect_words": [{"u": "U003", "heard": "as transcribed", "likely": "correct form", "evidence": "on-screen text in S004 / context"}],\n'
    ' "uncertain": ["anything you are unsure of; mark estimates with ~"]}\n'
    "Rules: segments are runs of consecutive shots that cover all shots in order without overlap. Give 5–10 "
    "takeaways, most useful first. Music and sung lyrics are not dialogue; say so in sound. Empty lists are fine."
)
RHYTHM_FIELDS = (("shot_size", "景别"), ("angle", "角度"), ("movement", "运镜"))


def rhythm(shots: list, fps: float, frames: int, segments: list, utts: list) -> dict:
    """Pace figures from the measured shots only (no model)."""
    lens = sorted(s["end"] - s["start"] for s in shots)
    n, duration = len(lens), shots[-1]["end"] if shots else 0
    step = 5 if duration <= 90 else 10 if duration <= 300 else 30
    curve = [{"from": a, "to": round(min(duration, a + step), 1),
              "cuts": sum(a <= s["start"] < a + step for s in shots[1:])}
             for a in range(0, int(duration) + 1, step) if a < duration]
    seg = [{"id": g["id"], "shots": len(g["shots"]), "seconds": round((g["last"] - g["first"] + 1) / fps, 2),
            "asl": round((g["last"] - g["first"] + 1) / fps / max(1, len(g["shots"])), 2)} for g in segments]
    dist = {}
    for key, _ in RHYTHM_FIELDS:
        count = {}
        for s in shots:
            for v in re.split(r"[、,，/]+", s.get("desc", {}).get(key, "") or "无法判断"):
                if v.strip():
                    count[v.strip()] = count.get(v.strip(), 0) + 1
        dist[key] = sorted(count.items(), key=lambda kv: -kv[1])
    by_len = sorted(shots, key=lambda s: s["end"] - s["start"])
    return {"shots": n, "seconds": round(duration, 2), "asl": round(duration / max(1, n), 2),
            "median": round((lens[(n - 1) // 2] + lens[n // 2]) / 2, 2) if n else 0,
            "shortest": [by_len[0]["id"], round(lens[0], 2)] if n else None,
            "longest": [by_len[-1]["id"], round(lens[-1], 2)] if n else None,
            "cuts_per_min": round((n - 1) / max(duration, 1e-6) * 60, 1),
            "speech": round(sum(u["last"] - u["first"] + 1 for u in utts) / max(1, frames), 2),
            "step": step, "curve": curve, "segments": seg, "dist": dist}


def _rhythm_text(m: dict) -> str:
    return (f"{m['shots']} shots in {m['seconds']}s; mean shot {m['asl']}s, median {m['median']}s, "
            f"shortest {m['shortest']}, longest {m['longest']}; {m['cuts_per_min']} cuts per minute; "
            f"speech covers {m['speech']:.0%} of the film.\ncuts per {m['step']}s: "
            + ", ".join(f"{b['from']}–{b['to']}s {b['cuts']}" for b in m["curve"]))


def _where(spec, shots: dict, tc) -> str:
    sp = span(id_range(spec or "", "S"), shots)
    return f"{spec}（{tc(sp[0])}–{tc(sp[1])}）" if sp else str(spec or "—")


def breakdown_refs(b: dict) -> list[str]:
    """Shot IDs the breakdown points at, for validation."""
    st, ed, lg = b.get("structure") or {}, b.get("editing") or {}, b.get("language") or {}
    specs = [(st.get("hook") or {}).get("shots"), (st.get("ending") or {}).get("shots")]
    specs += [x.get("shots") for x in (st.get("selling_points") or []) + (ed.get("transitions") or [])
              + (ed.get("techniques") or []) + (lg.get("signature") or []) + (b.get("takeaways") or []) if isinstance(x, dict)]
    return [i for sp in specs if sp for i in id_range(sp, "S")]


def render_breakdown_md(doc: dict, md_dir: Path) -> str:
    tc, b, m = _tc(doc), doc["breakdown"], doc["rhythm"]
    shots = {s["id"]: s for s in doc["shots"]}
    w = lambda spec: _where(spec, shots, tc)
    st, ed, lg, pk = (b.get(k) or {} for k in ("structure", "editing", "language", "packaging"))
    head = {k: doc[k] for k in ("protocol", "mode", "file", "fingerprint", "generated", "tools", "video", "counts",
                                "review", "status") if k in doc}
    L = ["---"] + [f"{k}: {json.dumps(val, ensure_ascii=False)}" for k, val in head.items()] + ["---", ""]
    L += [f"# {doc['file']} · 拉片", "", "## 1. 概览", "", doc["summary"] or "（全片分析未完成）", ""]
    L += [f"- 类型：{b.get('genre') or '—'}", f"- 画面类型：{doc['footage'] or '—'}",
          f"- 时长 {m['seconds']}s · {m['shots']} 个镜头 · 平均镜头 {m['asl']}s · 台词占 {m['speech']:.0%}", ""]

    hook, end = st.get("hook") or {}, st.get("ending") or {}
    L += ["## 2. 结构与叙事", "", f"- **开头钩子** {w(hook.get('shots'))}：{_cell(hook.get('how')) or '—'}",
          f"- **叙事结构**：{_cell(st.get('arc')) or '—'}", f"- **情绪曲线**：{_cell(st.get('emotion_curve')) or '—'}",
          f"- **结尾** {w(end.get('shots'))}：{_cell(end.get('how')) or '—'}"]
    L += [f"- **卖点** {_cell(x.get('point'))} · {w(x.get('shots'))}：{_cell(x.get('how'))}"
          for x in st.get("selling_points") or [] if isinstance(x, dict)]
    segm = {x["id"]: x for x in m["segments"]}
    L += ["", "| 分段 | 镜头 | 时间码 | 时长 | 平均镜头 | 叙事功能 | 内容 | 情绪 | 拍法与剪法 |", "|" + "---|" * 9]
    for g in doc["segments"]:
        x = segm.get(g["id"], {})
        L.append(f"| {g['id']} | {_short_ids(g['shots'])} | {tc(g['first'])}–{tc(g['last'])} | {x.get('seconds', '')}s | "
                 f"{x.get('asl', '')}s | {_cell(g.get('function'))} | {_cell(g['content'])} | {_cell(g['emotion'])} | {_cell(g['use'])} |")

    L += ["", "## 3. 节奏与剪辑", "", "镜头数据（逐帧测得）：",
          f"- {m['shots']} 个镜头，平均 {m['asl']}s，中位 {m['median']}s，每分钟 {m['cuts_per_min']} 刀",
          f"- 最短 {m['shortest'][0]} {m['shortest'][1]}s，最长 {m['longest'][0]} {m['longest'][1]}s" if m["shots"] else "- 无镜头",
          "", f"| 时间 | 每 {m['step']}s 切数 | |", "|---|---|---|"]
    top = max([x["cuts"] for x in m["curve"]] or [1]) or 1
    L += [f"| {x['from']}–{x['to']}s | {x['cuts']} | {'█' * round(x['cuts'] * 20 / top)} |" for x in m["curve"]]
    L += ["", f"- **节奏**：{_cell(ed.get('pace')) or '—'}", f"- **卡点**：{_cell(ed.get('music_sync')) or '—'}"]
    L += [f"- **转场** {w(x.get('shots'))}：{_cell(x.get('type'))}——{_cell(x.get('why'))}"
          for x in ed.get("transitions") or [] if isinstance(x, dict)]
    L += [f"- **剪辑手法** {w(x.get('shots'))}：{_cell(x.get('what'))}" for x in ed.get("techniques") or [] if isinstance(x, dict)]

    L += ["", "## 4. 视听语言", ""]
    for key, name in RHYTHM_FIELDS:
        L.append(f"- {name}分布：" + "、".join(f"{v} {k}（{k / max(1, m['shots']):.0%}）" for v, k in m["dist"][key][:8]))
    L += [f"- **镜头组合**：{_cell(lg.get('shots_style')) or '—'}", f"- **光色**：{_cell(lg.get('light_color')) or '—'}",
          f"- **声音**：{_cell(lg.get('sound')) or '—'}"]
    L += [f"- **标志镜头** {w(x.get('shots'))}：{_cell(x.get('what'))}" for x in lg.get("signature") or [] if isinstance(x, dict)]

    L += ["", "## 5. 包装", "", f"- 花字：{_cell(pk.get('captions')) or '—'}", f"- 字幕：{_cell(pk.get('subtitles')) or '—'}",
          f"- 图形：{_cell(pk.get('graphics')) or '—'}"]
    L += ["", "## 6. 可借鉴手法", ""]
    L += [f"{k}. **{_cell(x.get('what'))}** {w(x.get('shots'))}：{_cell(x.get('how'))}"
          for k, x in enumerate([x for x in b.get("takeaways") or [] if isinstance(x, dict)], 1)] or ["- 无"]
    L += [f"- 金句：{q.get('u')}——{_cell(q.get('why'))}" for q in (doc["highlights"].get("quotes") or [])]

    L += ["", "## 7. 人物", ""] + _people_table(doc)
    L += ["", "## 8. 镜头", ""] + _shot_table(doc)
    L += ["", "## 9. 台词", "", "| 台词 | 时间码 | 说话人 | 镜头 | 文本 |", "|---|---|---|---|---|"]
    for u in doc["utterances"]:
        who = u.get("person") or (f"S{u['speaker']}" if u.get("speaker") else "—")
        L.append(f"| {u['id']} | {tc(u['first'])}–{tc(u['last'])} | {who} | {_short_ids(u['shots'])} | {_cell(u['text'])} |")
    L += ["", "## 10. 待确认", ""] + ([f"- {x}" for x in doc["uncertain"]] or ["- 无"])
    L += [f"- 校验未通过：{x}" for x in doc["validation"]]
    if doc["storyboards"]:
        L += ["", "故事板：" + "、".join(f"[{Path(p).name}]({os.path.relpath(p, md_dir)})" for p in doc["storyboards"])]
    return "\n".join(L) + "\n"


COMPARE_PROMPT = (
    "Below are breakdowns (拉片) of {n} reference films, labelled A, B, C … Each gives measured rhythm "
    "figures and a structured analysis; shot IDs are per film (write them as A:S003).\n\n{films}\n\n"
    "Write a comparison for a director planning a new film in this style, in Markdown, with exactly these "
    "headings: ## 共同套路 (structure and storytelling first: hooks, arcs, ending, how selling points land; "
    "then editing, picture, sound, packaging), ## 各自特色 (one short paragraph per film), ## 节奏对比 "
    "(read the measured figures; do not invent numbers), ## 可复用的结构模板 (a beat-by-beat template with "
    "rough share of running time per beat, citing which film each beat comes from), ## 拍摄与剪辑清单 "
    "(concrete, checkable items). Cite films and shots for every claim. No preamble." + LANGUAGE_RULE
)


def compare(c: dict, docs: list[tuple[str, dict]], out_dir: Path) -> str:
    """One text-only request over several breakdowns → 拉片汇总-<time>.md next to the first film."""
    labels = [chr(65 + k) for k in range(len(docs))]
    films = "\n\n".join(
        f"=== {lab}: {d['file']} ===\nRHYTHM {_rhythm_text(d['rhythm'])}\nSEGMENTS "
        + json.dumps([{k: g.get(k) for k in ("id", "function", "content", "emotion", "use")} | {"shots": _short_ids(g["shots"])}
                      for g in d["segments"]], ensure_ascii=False)
        + "\nANALYSIS " + json.dumps({"summary": d["summary"], **{k: d["breakdown"].get(k) for k in
                                      ("genre", "structure", "editing", "language", "packaging", "takeaways")}}, ensure_ascii=False)
        for lab, (_, d) in zip(labels, docs))
    print(f"[genius-footage] comparing {len(docs)} films…", file=sys.stderr)
    text = client.call(c, [], COMPARE_PROMPT.replace("{n}", str(len(docs))).replace("{films}", films), 600)
    m = [d["rhythm"] for _, d in docs]
    L = ["# 拉片汇总", "", "| 片子 | 文件 | 时长 | 镜头 | 平均镜头 | 中位 | 每分钟刀数 | 台词占比 | 主要景别 |", "|" + "---|" * 9]
    for lab, (path, d), r in zip(labels, docs, m):
        L.append(f"| {lab} | [{d['file']}](<{os.path.relpath(Path(path).resolve(), out_dir)}>) | {r['seconds']}s | {r['shots']} | {r['asl']}s | "
                 f"{r['median']}s | {r['cuts_per_min']} | {r['speech']:.0%} | "
                 + "、".join(v for v, _ in r["dist"]["shot_size"][:3]) + " |")
    out = out_dir / f"拉片汇总-{datetime.now():%Y%m%d-%H%M}.md"
    out.write_text("\n".join(L) + "\n\n（表中数字为逐帧测量，下文为模型对比分析）\n\n" + text.strip() + "\n", encoding="utf-8")
    return str(out)


def _overview(c: dict, r: dict, utts: list, script: str | None, upload: str, marks: dict | None = None,
              breakdown: bool = False) -> dict:
    shot_lines = "\n".join(
        f"{s['id']} {s['tc_in']} {s['end'] - s['start']:.1f}s | "
        + " | ".join(s.get("desc", {}).get(k, "") for k in ("shot_size", "scene", "action")) for s in r["shots"])
    utt_lines = "\n".join(f"{u['id']} [{u.get('speaker') or '?'}] {u['shots'][0] if u['shots'] else ''} | {u['text']}"
                          for u in utts) or "(no transcript)"
    base = OVERVIEW_PROMPT if marks is None else OVERVIEW_PROMPT_TH + TH_RULES.replace("{marks}", _marks_text(marks, r["fps"]))
    if breakdown:
        base = BREAKDOWN_PROMPT.replace("{rhythm}", _rhythm_text(rhythm(r["shots"], r["fps"], r["frames"], [], utts)))
    prompt = (base.replace("{script}", f"\n\nSCRIPT / KEYWORDS (correct spellings)\n{script}" if script else "")
              .replace("{shots}", shot_lines).replace("{utts}", utt_lines)) + LANGUAGE_RULE
    print("[genius-footage] whole-clip overview…", file=sys.stderr)
    ov = client.parse_json(client.call(c, [upload], prompt, max(300, min(900, r["duration"] * 0.6))), "{", "}")
    if not isinstance(ov, dict) or not ov:
        r["warnings"].append("whole-clip overview returned no JSON")
        return {}
    return ov


def run(src: str, c: dict, script: str | None = None, talking_head: bool = False, breakdown: bool = False) -> dict:
    """Write <stem>.footage.md, <stem>.footage.json and <stem>.footage/ next to the clip
    (--breakdown: <stem>.breakdown.md / .breakdown.json, storyboards still in <stem>.footage/).
    Speech needs no shot list, so it runs alongside the measurement and the storyboard steps."""
    clip = Path(src)
    base = clip.with_suffix("")
    if not os.access(clip.parent, os.W_OK):
        raise FootageError("UNSUPPORTED_FORMAT", f"cannot write the footage brief next to the clip: {clip.parent}")
    seek = measure.frame_times(src, for_seek=True)
    bg = ThreadPoolExecutor(2)
    print("[genius-footage] transcribing (Doubao ASR) in the background…", file=sys.stderr)
    speech_job = bg.submit(client.tagged(lambda: client.cached(src, "asr", lambda: asr.transcribe(src), asr.__file__)))
    duration = asr.probe_duration(src)
    r = measured(src, duration)  # also leaves the whole-clip proxy in the cache, so the next line only checks
    proxy = bg.submit(client.tagged(client.video_proxy), src, duration) if duration <= client.MAX_VIDEO_SEC else None
    r = shots(src, c, r, Path(f"{base}.footage"), seek, talking_head)

    asr_note, utts, asr_model = None, [], None
    try:
        speech = speech_job.result()
        asr_model = speech.get("model")
        utts = utterances(speech, seek, r["shots"], r["frames"])
        cut_points(utts, r["frames"])
    except (SpeechError, ValueError) as e:
        asr_note = str(e)
        print(f"[genius-footage] {asr_note}", file=sys.stderr)

    marks = speech_marks(utts, r["fps"]) if talking_head else None
    spoken = sum(u["last"] - u["first"] + 1 for u in utts) / max(1, r["frames"])
    if not talking_head and not breakdown and r["measured_shots"] <= 2 and len(r["suspects"]) > TH_HINT[0] and spoken > TH_HINT[1]:
        r["warnings"].append(f"像是口播（测得 {r['measured_shots']} 个镜头、{len(r['suspects'])} 处疑似切点、"
                             f"台词占 {spoken:.0%}）：下次可加 --talking-head，更快，并给出精剪建议")
    ov = {}
    if proxy is None:
        r["warnings"].append(f"clip longer than {client.MAX_VIDEO_SEC // 60} min: whole-clip overview skipped")
    else:
        try:
            ov = _overview(c, r, utts, script, proxy.result(), marks, breakdown)
        except FootageError as e:
            r["errors"].append(e)
    bg.shutdown()
    if r["errors"] and not ov and not any("desc" in s for s in r["shots"]):
        raise r["errors"][0]  # the model gave nothing at all (bad key, gateway down): fail as before
    r["warnings"] += list(dict.fromkeys(f"模型请求失败 [{e.code}]：{e}（缺的部分见待确认，重跑可补）" for e in r["errors"]))
    doc = build(r, utts, ov, asr_note,
                {"measure": "genius-footage measure.py", "asr": asr_model, "storyboard": c["model"],
                 "overview": c["model"] if ov else None},
                client.fingerprint(src), datetime.now().astimezone().isoformat(timespec="seconds"),
                audio_info(src), marks)
    if proxy is not None and not ov:  # failed or empty: the brief still has shots and lines
        doc["uncertain"].append("全片分析缺失：概览、人物、分段、亮点为空，重跑可补")
        doc["status"] = "needs_review"
    kind = "breakdown" if breakdown else "footage"
    if breakdown:
        doc.update(mode="breakdown", breakdown={k: ov.get(k) for k in ("genre", "structure", "editing", "language",
                                                                      "packaging", "takeaways")},
                   rhythm=rhythm(r["shots"], r["fps"], r["frames"], doc["segments"], utts))
        known = {s["id"] for s in r["shots"]}
        bad = sorted({i for i in breakdown_refs(doc["breakdown"]) if i not in known})
        if bad:
            doc["validation"].append(f"拉片引用了不存在的镜头 {', '.join(bad)}")
            doc["status"] = "needs_review"
    md_path, json_path = Path(f"{base}.{kind}.md"), Path(f"{base}.{kind}.json")
    md_path.write_text((render_breakdown_md if breakdown else render_md)(doc, md_path.parent), encoding="utf-8")
    json_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    res = {"mode": kind, "footage_md": str(md_path), "footage_json": str(json_path), "status": doc["status"],
           "counts": doc["counts"], "review": doc["review"], "validation": doc["validation"],
           "warnings": doc["warnings"]}
    if talking_head:
        res["edit"] = {"pieces": len(doc["edit"]), "seconds": round(sum(e["last"] - e["first"] + 1 for e in doc["edit"]) / r["fps"], 1),
                       "source_seconds": round(r["duration"], 1)}
    return res


def render_result(res: dict) -> str:
    c, rv = res["counts"], res["review"]
    lines = [f"状态：**{res['status']}** · {c['shots']} 镜头 · {c['utterances']} 句台词 · {c['people']} 人 · {c['segments']} 段",
             f"{'拉片' if res.get('mode') == 'breakdown' else '说明书'}：`{res['footage_md']}`", f"数据：`{res['footage_json']}`"]
    if "edit" in res:
        e = res["edit"]
        lines.append(f"精剪建议：{e['pieces']} 段，约 {e['seconds']}s（原 {e['source_seconds']}s）")
    if any(rv.values()):
        lines.append(f"待复核：未复核切点 {rv['unresolved_suspects']} · 可能听错的词 {rv['uncertain_words']} · "
                     f"缺描述镜头 {rv['missing_descriptions']}"
                     + (f" · 对不上的精剪建议 {rv['unmatched_keep']}" if "unmatched_keep" in rv else ""))
    lines += [f"校验未通过：{x}" for x in res["validation"]] + [f"⚠️ {w}" for w in res["warnings"]]
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────

def _one(item: str, c: dict, args, script: str | None, tag: str | None) -> tuple[str, dict | None, FootageError | None]:
    client.ctx.tag = tag
    try:
        if not Path(item).is_file() and re.search(r"https?://", item):
            item = download.fetch(item, Path(args.download_dir).expanduser(), args.cookies_from_browser)
        if not Path(item).is_file():
            raise FootageError("INPUT_NOT_FOUND", f"File not found: {item}")
        if Path(item).suffix.lower() not in client.VIDEO_EXTENSIONS:
            raise FootageError("UNSUPPORTED_FORMAT", f"footage needs a local video file: {item}")
        if args.download_only:
            return item, {"mode": "download", "path": item}, None
        return item, run(item, c, script, args.talking_head, args.breakdown), None
    except FootageError as e:
        return item, None, e
    except Exception as e:
        import traceback
        traceback.print_exc()
        return item, None, FootageError("ERROR", f"{type(e).__name__}: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="AG_FOOTAGE/1.1 footage brief (or 拉片 breakdown) for one or more clips")
    parser.add_argument("files", nargs="*", help="Local video files, or links (downloaded with yt-dlp)")
    parser.add_argument("--script", default=None, help="Script or keyword file (correct spellings of names, brands)")
    parser.add_argument("--model", "-m", default=None, help="Model override (default FOOTAGE_MODEL or gemini-4-hydrogen-xhigh)")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--jobs", "-j", type=int, default=JOBS, help=f"Clips at once (default {JOBS})")
    parser.add_argument("--max-requests", type=int, default=None,
                        help=f"Model requests in flight across all clips (default FOOTAGE_MAX_REQUESTS or {client.MAX_REQUESTS})")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--talking-head", action="store_true",
                      help="口播 / one take: skip the doubtful-cut check, add pauses, fillers, restarts and a keep[] edit")
    mode.add_argument("--breakdown", action="store_true",
                      help="拉片: how a reference film is built; several films also get one comparison (拉片汇总)")
    mode.add_argument("--download-only", action="store_true", help="视频下载: only download the links, no analysis")
    parser.add_argument("--no-compare", action="store_true", help="--breakdown with several films: skip the comparison")
    parser.add_argument("--download-dir", default="~/Downloads/genius-footage", help="Where links are downloaded")
    parser.add_argument("--cookies-from-browser", default=None, help="yt-dlp cookies for links that need a login (chrome, safari…)")
    parser.add_argument("--check", action="store_true", help="Check ffmpeg, the model key and the ASR key")
    args = parser.parse_args()
    c = client.conf(args.model)
    if args.max_requests:
        client.set_limit(args.max_requests)
    if args.check:
        ff, asr_key = shutil.which("ffmpeg") and shutil.which("ffprobe"), asr.find_key()
        print(f"ffmpeg:       {shutil.which('ffmpeg') or 'MISSING'}\n"
              f"model:        {c['model']} @ {c['base_url']} key={'yes' if c['api_key'] else 'no'}\n"
              f"asr:          {asr.ASR_MODEL} key={'yes' if asr_key else 'no (no transcript)'}\n"
              f"yt-dlp:       {shutil.which('yt-dlp') or 'not installed (links unsupported)'}\n"
              f"redfox:       key={'yes' if client._env('REDFOX_API_KEY') else 'no (抖音 / 小红书 via the ego browser)'}\n"
              f"ego-browser:  {shutil.which('ego-browser') or 'not installed'}\n"
              f"cache:        {client.CACHE_DIR} (whole-clip proxies, measured cuts, transcripts; delete to start fresh)")
        ok = bool(ff and c["api_key"] and asr_key)
        print("ok" if ok else "NOT READY")
        sys.exit(0 if ok else 2)
    if not args.files:
        parser.error("at least one file or link is required (unless --check)")
    if not c["api_key"] and not args.download_only:
        print("Error [PROVIDER_ERROR]: API key not found: set FOOTAGE_API_KEY (or CPA_API_KEY) in scripts/.env", file=sys.stderr)
        sys.exit(client.EXIT_CODES["PROVIDER_ERROR"])
    script = Path(args.script).read_text(encoding="utf-8") if args.script else None
    many = len(args.files) > 1
    if many:
        global _procs
        _procs = ProcessPoolExecutor(max(1, min(args.jobs, len(args.files), os.cpu_count() or 1)))
        sys.stderr = _TagStream(sys.stderr)
        print(f"[genius-footage] {len(args.files)} clips, {min(args.jobs, len(args.files))} at a time", file=sys.stderr)
    link = lambda f: re.search(r"https?://(\S+)", f) if not Path(f).is_file() else None
    tags = [f"{k}/{len(args.files)} {link(f).group(1) if link(f) else Path(f).stem}"[:28]
            for k, f in enumerate(args.files, 1)] if many else [None]
    with ThreadPoolExecutor(max(1, min(args.jobs, len(args.files)))) as ex:
        results = list(ex.map(lambda ft: _one(ft[0], c, args, script, ft[1]), zip(args.files, tags)))

    summary = None
    done = [(f, r) for f, r, _ in results if r]
    if args.breakdown and len(done) > 1 and not args.no_compare:
        try:
            docs = [(f, json.loads(Path(r["footage_json"]).read_text(encoding="utf-8"))) for f, r in done]
            summary = compare(c, docs, Path(docs[0][0]).resolve().parent)
        except FootageError as e:
            summary = None
            print(f"[genius-footage] 拉片汇总失败 [{e.code}]: {e}", file=sys.stderr)

    if args.output == "json":
        out = [{"file": f, **(r or {}), **({"error": {"code": e.code, "message": str(e)}} if e else {})} for f, r, e in results]
        print(json.dumps(out[0] if not many else {"clips": out, "compare_md": summary}, ensure_ascii=False, indent=2))
    else:
        show = lambda r: f"已下载：`{r['path']}`" if r.get("mode") == "download" else render_result(r)
        blocks = [f"## {f if args.download_only else Path(f).name if many else 'Footage'}\n\n" + (show(r) if r else f"Error [{e.code}]: {e}")
                  for f, r, e in results]
        if summary:
            blocks.append(f"## 拉片汇总\n\n`{summary}`")
        print("\n\n".join(blocks))
    errs = [e for _, _, e in results if e]
    for e in errs:
        print(f"Error [{e.code}]: {e}", file=sys.stderr)
    if errs:
        sys.exit(client.EXIT_CODES.get(errs[0].code, 1))

if __name__ == "__main__":
    main()
