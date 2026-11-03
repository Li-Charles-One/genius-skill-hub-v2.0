"""
AG_FOOTAGE/1.0 — build, render and validate a footage brief (`<clip>.footage.md` + `.footage.json`).

No model calls here: speech → frames, cut points, ID → frame conversion, markdown, validation.
The model's answers arrive as plain dicts that reference IDs (S001, U001, P1, G01), never times.
Protocol: ArtisticCut/AG_FOOTAGE.md.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from bisect import bisect_left, bisect_right
from pathlib import Path

import measure

PROTOCOL = "AG_FOOTAGE/1.0"
CUT_GAP, JOINED_GAP = 4, 2     # frames: a pause ≥4 is a clean cut; <2 at punctuation is run-together
PUNCT = set("，。！？；：、,.!?;:…—")
DEFAULT_VOICE = Path(__file__).resolve().parent.parent.parent / "genius-voice" / "scripts" / "voice.py"


class FootageError(RuntimeError):
    pass


# ── Speech (genius-voice) ────────────────────────────────────────────────

def voice_script() -> Path | None:
    p = Path(os.environ.get("OMNI_VOICE_SCRIPT", str(DEFAULT_VOICE)))
    return p if p.is_file() else None


def transcribe(src: str) -> dict:
    """genius-voice ASR with speaker labels; raises FootageError with its message on failure."""
    script = voice_script()
    if not script:
        raise FootageError(f"genius-voice not found at {DEFAULT_VOICE} (set OMNI_VOICE_SCRIPT)")
    p = subprocess.run([sys.executable, str(script), "asr", src, "--speakers", "--output", "json"],
                       capture_output=True, text=True)
    if p.returncode != 0:
        raise FootageError(f"genius-voice asr failed: {(p.stderr or p.stdout).strip()[-300:]}")
    return json.loads(p.stdout)


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
           "audio": audio, "summary": ov.get("summary", ""), "people": people, "segments": segments,
           "shots": r["shots"], "utterances": utts, "highlights": ov.get("highlights") or {},
           "uncertain": uncertain, "suspects": r["suspects"], "storyboards": r.get("storyboards", []),
           "warnings": r.get("warnings", [])}
    doc["counts"] = {"shots": len(r["shots"]), "utterances": len(utts), "people": len(people), "segments": len(segments)}
    doc["review"] = {"unresolved_suspects": sum("check" not in s for s in r["suspects"]),
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

    L += ["## 2. 人物", "", "| 人物 | 外观 | 身份 | 说话人 | 出场镜头 |", "|---|---|---|---|---|"]
    for p in doc["people"]:
        L.append(f"| {p.get('id')} | {_cell(p.get('appearance'))} | {_cell(p.get('identity'))} | "
                 f"{', '.join('S' + str(s).lstrip('Ss') for s in p.get('speakers') or []) or '—'} | "
                 f"{_short_ids(id_range(p.get('shots', ''), 'S'))} |")

    L += ["", "## 3. 分段", "", "| 分段 | 镜头 | 帧 | 时间码 | 内容 | 情绪 | 适合用作 |", "|---|---|---|---|---|---|---|"]
    for g in doc["segments"]:
        L.append(f"| {g['id']} | {_short_ids(g['shots'])} | f{g['first']}–f{g['last']} | {tc(g['first'])}–{tc(g['last'])} | "
                 f"{_cell(g['content'])} | {_cell(g['emotion'])} | {_cell(g['use'])} |")

    L += ["", "## 4. 镜头", "", "| 镜头 | 帧 | 时间码 入–出 | 时长 | 切入 | 景别 | 角度 | 运镜 | 人物 | 场景 | 画面 | 表演 | 标记 |",
          "|" + "---|" * 13]
    for s in doc["shots"]:
        d = s.get("desc", {})
        via = s["via"] + (f" (f{s['transition'][0]}–f{s['transition'][1]})" if "transition" in s else "")
        L.append(f"| {s['id']} | f{s['first']}–f{s['last']} | {s['tc_in']}–{s['tc_out']} | {s['end'] - s['start']:.2f}s | {via} | "
                 + " | ".join(_cell(d.get(k)) for k in ("shot_size", "angle", "movement", "people", "scene", "action",
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
