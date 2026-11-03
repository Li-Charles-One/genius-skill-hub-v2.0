#!/usr/bin/env python3
"""
Genius Footage — AG_FOOTAGE/1.0 brief for one clip (`<clip>.footage.md` + `.footage.json` + `.footage/`).

    python3 footage.py <clip> [--script FILE] [--provider ID] [--model M] [--output text|json]
    python3 footage.py --check

Steps: genius-omni video-shots (frame measurement, storyboard check, per-shot description) →
genius-voice asr --speakers (words → frames, cut points) → one whole-clip request where the model
answers with IDs only (S001, U001, P1, G01) → IDs converted to frames and timecode → validate.
Uses genius-omni and genius-voice from sibling folders (FOOTAGE_OMNI_DIR / FOOTAGE_VOICE_SCRIPT override).
Protocol: ArtisticCut/AG_FOOTAGE.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from bisect import bisect_left, bisect_right
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
OMNI_DIR = Path(os.environ.get("FOOTAGE_OMNI_DIR", str(HERE.parent.parent / "genius-omni" / "scripts")))
DEFAULT_VOICE = HERE.parent.parent / "genius-voice" / "scripts" / "voice.py"
sys.path.insert(0, str(OMNI_DIR))
try:
    import measure
    import vision
except ImportError:
    print(f"Error [DEPENDENCY_MISSING]: genius-omni not found at {OMNI_DIR} (set FOOTAGE_OMNI_DIR)", file=sys.stderr)
    sys.exit(5)

PROTOCOL = "AG_FOOTAGE/1.0"
CUT_GAP, JOINED_GAP = 4, 2     # frames: a pause ≥4 is a clean cut; <2 at punctuation is run-together
PUNCT = set("，。！？；：、,.!?;:…—")


class FootageError(RuntimeError):
    pass


# ── Speech (genius-voice) ────────────────────────────────────────────────

def voice_script() -> Path | None:
    p = Path(os.environ.get("FOOTAGE_VOICE_SCRIPT", str(DEFAULT_VOICE)))
    return p if p.is_file() else None


def transcribe(src: str) -> dict:
    """genius-voice ASR with speaker labels; raises FootageError with its message on failure."""
    script = voice_script()
    if not script:
        raise FootageError(f"genius-voice not found at {DEFAULT_VOICE} (set FOOTAGE_VOICE_SCRIPT)")
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


# ── Whole clip (model answers with IDs only; frames and timecode are computed) ──

OVERVIEW_PROMPT = (
    "You are logging one raw video clip for an editor. Watch the clip. Below are its shot list and "
    "transcript, measured frame by frame (IDs: S### shots, U### utterances; ASR speakers are 1, 2, …)."
    "{script}\n\nSHOTS\n{shots}\n\nTRANSCRIPT\n{utts}\n\n"
    "Return ONLY one JSON object with these keys. Refer to shots and lines ONLY by their IDs, never by time; "
    "use only IDs listed above.\n"
    '{"summary": "2–3 sentences: what this clip is, who, where, what is said",\n'
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


def _overview(src: str, conf: dict, r: dict, utts: list, script: str | None) -> dict:
    plan = vision.plan_media(src, "video", conf["api_style"])
    if plan["action"] == "segments":
        r["warnings"].append(f"clip longer than {vision.format_duration(vision.MAX_SINGLE_SEC)}: whole-clip overview skipped")
        return {}
    shot_lines = "\n".join(
        f"{s['id']} {s['tc_in']} {s['end'] - s['start']:.1f}s | "
        + " | ".join(s.get("desc", {}).get(k, "") for k in ("shot_size", "scene", "action")) for s in r["shots"])
    utt_lines = "\n".join(f"{u['id']} [{u.get('speaker') or '?'}] {u['shots'][0] if u['shots'] else ''} | {u['text']}"
                          for u in utts) or "(no transcript)"
    prompt = (OVERVIEW_PROMPT.replace("{script}", f"\n\nSCRIPT / KEYWORDS (correct spellings)\n{script}" if script else "")
              .replace("{shots}", shot_lines).replace("{utts}", utt_lines)) + vision.LANGUAGE_RULE
    upload = src if plan["action"] == "passthrough" else vision.build_proxy(src, "video", plan, conf["api_style"] == "gemini")
    print("[genius-footage] whole-clip overview…", file=sys.stderr)
    text = vision.call_model(conf, [(upload, "video")], prompt, max(300, min(900, plan["duration"] * 0.6)))
    a, b = text.find("{"), text.rfind("}")
    try:
        ov = json.loads(text[a:b + 1]) if a != -1 and b > a else {}
    except ValueError:
        ov = {}
    if not ov:
        r["warnings"].append("whole-clip overview returned no JSON")
    return ov


def run(src: str, conf: dict, script: str | None = None) -> dict:
    """Write <stem>.footage.md, <stem>.footage.json and <stem>.footage/ next to the clip."""
    clip = Path(src)
    base = clip.with_suffix("")
    if not os.access(clip.parent, os.W_OK):
        raise vision.OmniError("UNSUPPORTED_FORMAT", f"cannot write the footage brief next to the clip: {clip.parent}")
    r = vision._analyze_shots(src, conf, Path(f"{base}.footage"))
    seek = measure.frame_times(src, for_seek=True)

    asr_note, utts, asr_model = None, [], None
    try:
        print("[genius-footage] transcribing with genius-voice…", file=sys.stderr)
        asr = transcribe(src)
        asr_model = asr.get("model")
        utts = utterances(asr, seek, r["shots"], r["frames"])
        cut_points(utts, r["frames"])
    except (FootageError, ValueError) as e:
        asr_note = str(e)
        print(f"[genius-footage] {asr_note}", file=sys.stderr)

    ov = _overview(src, conf, r, utts, script)
    doc = build(r, utts, ov, asr_note,
                {"measure": "genius-omni measure.py", "asr": asr_model, "storyboard": conf["model"],
                 "overview": conf["model"] if ov else None},
                vision._file_fingerprint(src), datetime.now().astimezone().isoformat(timespec="seconds"),
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

def main() -> None:
    parser = argparse.ArgumentParser(description="AG_FOOTAGE/1.0 footage brief for one clip")
    parser.add_argument("file", nargs="?", help="Local video file")
    parser.add_argument("--script", default=None, help="Script or keyword file (correct spellings of names, brands)")
    parser.add_argument("--provider", "-p", default=None, help="genius-omni provider id (default: its active one)")
    parser.add_argument("--model", "-m", default=None, help="Model override")
    parser.add_argument("--output", "-o", choices=["text", "json"], default="text")
    parser.add_argument("--check", action="store_true", help="Check ffmpeg, genius-omni, genius-voice and the provider")
    args = parser.parse_args()
    try:
        if args.check:
            info, conf = vision.check_system(), vision.provider_conf(args.provider, model=args.model, kind="video")
            voice = voice_script()
            print(f"genius-omni:  {OMNI_DIR}\ngenius-voice: {voice or 'not found (no transcript)'}\n"
                  f"ffmpeg:       {info['ffmpeg']}\nprovider:     {conf['id']} model={conf['model']} "
                  f"key={'yes' if conf['api_key'] else 'no'}")
            ok = info["ok"] and bool(conf["api_key"]) and bool(voice)
            print("ok" if ok else "NOT READY")
            sys.exit(0 if ok else 2)
        if not args.file:
            parser.error("file is required (unless --check)")
        if not Path(args.file).is_file():
            raise vision.OmniError("INPUT_NOT_FOUND", f"File not found: {args.file}")
        if vision.media_kind(args.file) != "video":
            raise vision.OmniError("UNSUPPORTED_FORMAT", "footage needs a local video file")
        conf = vision.provider_conf(args.provider, model=args.model, kind="video")
        if not conf["api_key"]:
            raise vision.OmniError("PROVIDER_ERROR", f"API key not found for provider '{conf['id']}' "
                                   f"(set {' / '.join(conf['key_envs'])} in genius-omni scripts/.env)")
        res = run(args.file, conf, Path(args.script).read_text(encoding="utf-8") if args.script else None)
        print(json.dumps(res, ensure_ascii=False, indent=2) if args.output == "json"
              else f"## Footage\n\n{render_result(res)}")
    except Exception as e:
        code = vision._error_code(e)
        print(f"Error [{code}]: {e}" if code else f"Error: {e}", file=sys.stderr)
        sys.exit(vision.EXIT_CODES.get(code, 1))


if __name__ == "__main__":
    main()
