#!/usr/bin/env python3
"""
Genius Voice — speech-to-text via Doubao file ASR 2.0, text-to-speech via Xiaomi MiMo v2.5,
audio generation via Doubao Seed Audio 1.0.

    python3 voice.py --check
    python3 voice.py asr <audio_or_video> [--language auto|zh|en] [--speakers] [--output text|json] [--out FILE]
    python3 voice.py tts "<text>" | --text-file F | -   [--voice ID | --clone REF | --design PROMPT]
                     [--style "<direction>"] [--out FILE.wav|.mp3]
    python3 voice.py gen "<prompt>" | --text-file F | -  [--ref AUDIO ...] [--speaker ID] [--image IMG]
                     [--subtitle] [--out FILE.wav|.mp3]

ASR: volc.seedasr.auc (utterance + word timestamps, optional speaker labels).
TTS: mimo-v2.5-tts, mimo-v2.5-tts-voiceclone, mimo-v2.5-tts-voicedesign.
Gen: seed-audio-1.0 (sound effects, music, multi-role scenes, timeline control; ≤120s per call).
Failures print `Error [CODE]: ...` to stderr and exit with EXIT_CODES[CODE].
"""

from __future__ import annotations

import argparse
import base64
import http.client
import io
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import uuid
import wave
from datetime import datetime
from functools import lru_cache
from pathlib import Path

DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
TTS_MODEL = "mimo-v2.5-tts"
CLONE_MODEL = "mimo-v2.5-tts-voiceclone"
DESIGN_MODEL = "mimo-v2.5-tts-voicedesign"
PRESET_VOICES = ["mimo_default", "冰糖", "茉莉", "苏打", "白桦", "Mia", "Chloe", "Milo", "Dean"]

ASR_URL = "https://openspeech.bytedance.com/api/v3/auc/bigmodel/"
ASR_MODEL = "volc.seedasr.auc"
ASR_LANGUAGES = {"zh": "zh-CN", "en": "en-US"}  # auto: omit the field
# Speaker diarization changes the text (fewer, merged utterances; 100 → 一百), so it runs as a second pass.
ASR_PASS_TEXT = {"enable_itn": True, "enable_punc": True, "show_speech_rate": True,
                 "enable_emotion_detection": True, "enable_gender_detection": True}
ASR_PASS_SPEAKER = {"enable_itn": True, "enable_punc": True, "enable_speaker_info": True,
                    "ssd_version": "200"}  # 200 separated 5 speakers where 300 merged them into 3
ASR_MAX_B64_BYTES = 100 * 1000 * 1000  # above this the provider wants audio.url instead of inline data
ASR_POLL_SEC = 2
ASR_WAIT_PER_AUDIO_SEC = 0.3  # measured ≈0.09s per audio second; 3× margin for queueing
GEN_URL = "https://openspeech.bytedance.com/api/v3/tts/create"
GEN_MODEL = "seed-audio-1.0"  # override with DOUBAO_AUDIO_MODEL (some accounts are granted only a variant)
GEN_MAX_SECONDS = 120
GEN_MAX_PROMPT_CHARS = 3000
GEN_MAX_REFS = 3
GEN_REF_MAX_SECONDS = 30
GEN_IMAGE_TYPES = {".jpg", ".jpeg", ".png", ".webp"}
TIMELINE_TAG = re.compile(r"\[\s*\d+(?:\.\d+)?\s*s?\s*[:：]\s*(\d+(?:\.\d+)?)\s*s?\s*\]")
# TTS starts skipping or looping past ~250 chars per request; keep chunks well below.
TTS_CHUNK_CHARS = int(os.environ.get("VOICE_TTS_CHUNK_CHARS", "150"))
MAX_B64_BYTES = 10 * 1000 * 1000  # documented limit for input audio and clone reference
REQUEST_TIMEOUT = float(os.environ.get("VOICE_TIMEOUT", "600"))

EXIT_CODES = {
    "INPUT_NOT_FOUND": 3,
    "UNSUPPORTED_FORMAT": 4,
    "DEPENDENCY_MISSING": 5,
    "PROVIDER_ERROR": 6,
    "TIMEOUT": 7,
}


class VoiceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def log(msg: str) -> None:
    print(f"[genius-voice] {msg}", file=sys.stderr, flush=True)


# ── Config ───────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def _dotenv() -> dict:
    env_path = Path(__file__).parent / ".env"
    out = {}
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                name, value = line.split("=", 1)
                out[name.strip()] = value.strip().strip('"').strip("'")
    return out


def _env(name: str, default: str = "") -> str:
    return (os.environ.get(name) or _dotenv().get(name) or default).strip()


def base_url() -> str:
    return _env("MIMO_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def api_key() -> str:
    key = _env("MIMO_API_KEY")
    if not key:
        raise VoiceError("PROVIDER_ERROR", "MIMO_API_KEY is not set (scripts/.env or environment)")
    return key


def doubao_key() -> str:
    key = _env("DOUBAO_API_KEY")
    if not key:
        raise VoiceError("PROVIDER_ERROR", "DOUBAO_API_KEY is not set (scripts/.env or environment)")
    return key


# ── HTTP ─────────────────────────────────────────────────────────────────

RETRY_HTTP = {429, 500, 502, 503, 504}
RETRY_DELAYS = (5, 15, 30)


def _http(method: str, url: str, headers: dict, body: dict | None = None):
    """JSON request with retries on 429/5xx/network errors. Returns (response headers, parsed body)."""
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json", **headers}
    for attempt, delay in enumerate((*RETRY_DELAYS, None), 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                raw = resp.read().decode("utf-8")
                return resp.headers, json.loads(raw) if raw.strip() else {}
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace")
            try:
                parsed = json.loads(text)
                err = parsed.get("error") or (parsed.get("header") or {}).get("message")
                text = (err.get("message") if isinstance(err, dict) else err) or text
            except Exception:
                pass
            error = VoiceError("PROVIDER_ERROR", f"API error {e.code}: {str(text)[:300]}")
            transient = e.code in RETRY_HTTP
        except (socket.timeout, TimeoutError) as e:
            raise VoiceError("TIMEOUT", f"No response within {REQUEST_TIMEOUT:g}s") from e
        except urllib.error.URLError as e:
            if isinstance(e.reason, (socket.timeout, TimeoutError)):
                raise VoiceError("TIMEOUT", f"No response within {REQUEST_TIMEOUT:g}s") from e
            error = VoiceError("PROVIDER_ERROR", f"Network error: {e.reason}")
            transient = True
        except (ConnectionError, http.client.HTTPException) as e:  # e.g. server closed without a response
            error = VoiceError("PROVIDER_ERROR", f"Network error: {e}")
            transient = True
        if delay is None or not transient:
            raise error
        log(f"{error} — retry {attempt}/{len(RETRY_DELAYS)} in {delay}s…")
        time.sleep(delay)
    raise AssertionError("unreachable")


def _request(method: str, path: str, body: dict | None = None) -> dict:
    """MiMo (TTS) call."""
    key = api_key()
    return _http(method, base_url() + path, {"api-key": key, "Authorization": f"Bearer {key}"}, body)[1]


def _doubao(path: str, body: dict, request_id: str) -> tuple[str, str, dict]:
    """Doubao ASR call. Returns (X-Api-Status-Code, X-Api-Message, body)."""
    headers, data = _http("POST", ASR_URL + path, {
        "X-Api-Key": doubao_key(), "X-Api-Resource-Id": ASR_MODEL,
        "X-Api-Request-Id": request_id, "X-Api-Sequence": "-1"}, body)
    return headers.get("X-Api-Status-Code", ""), headers.get("X-Api-Message", ""), data


def _choice(data: dict) -> dict:
    try:
        choice = data["choices"][0]
    except (KeyError, IndexError, TypeError):
        raise VoiceError("PROVIDER_ERROR", f"Unexpected response: {json.dumps(data, ensure_ascii=False)[:300]}")
    if choice.get("finish_reason") == "content_filter":
        raise VoiceError("PROVIDER_ERROR", "Request blocked by the provider's content filter")
    return choice


# ── ffmpeg helpers ───────────────────────────────────────────────────────

def _run(cmd: list, timeout: float, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(cmd, input=stdin, capture_output=True, timeout=timeout)
    except FileNotFoundError as e:
        raise VoiceError("DEPENDENCY_MISSING", f"{cmd[0]} not found on PATH (install ffmpeg)") from e
    except subprocess.TimeoutExpired as e:
        raise VoiceError("TIMEOUT", f"{cmd[0]} exceeded {timeout:g}s") from e


def probe_duration(path: str) -> float:
    proc = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", path], 60)
    try:
        return float(json.loads(proc.stdout or b"{}")["format"]["duration"])
    except (KeyError, TypeError, ValueError):
        raise VoiceError("UNSUPPORTED_FORMAT", f"ffprobe cannot read an audio duration from {path}")


def encode_mp3(path: str, start: float, length: float) -> bytes:
    proc = _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
                 "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "64k",
                 "-f", "mp3", "pipe:1"], 900)
    if proc.returncode != 0 or not proc.stdout:
        raise VoiceError("UNSUPPORTED_FORMAT", f"ffmpeg could not decode audio: {proc.stderr.decode(errors='replace')[:300]}")
    return proc.stdout


# ── ASR ──────────────────────────────────────────────────────────────────

def _asr_pass(b64: str, options: dict, language: str, duration: float) -> list[dict]:
    """Submit one recognition job and poll until done. Returns raw utterances ([] for silence)."""
    request_id = str(uuid.uuid4())  # doubles as the task id for polling
    audio = {"data": b64, "format": "mp3"}
    if language in ASR_LANGUAGES:
        audio["language"] = ASR_LANGUAGES[language]
    code, msg, _ = _doubao("submit", {"audio": audio, "request": {
        "model_name": "bigmodel", "show_utterances": True, **options}}, request_id)
    if code != "20000000":
        raise VoiceError("PROVIDER_ERROR", f"ASR submit failed [{code}]: {msg}")
    wait = max(REQUEST_TIMEOUT, duration * ASR_WAIT_PER_AUDIO_SEC)
    deadline = time.monotonic() + wait
    while True:
        time.sleep(ASR_POLL_SEC)
        code, msg, data = _doubao("query", {}, request_id)
        if code == "20000000":
            return (data.get("result") or {}).get("utterances") or []
        if code == "20000003":  # no valid speech in audio
            return []
        if code not in ("20000001", "20000002"):  # queued / processing
            raise VoiceError("PROVIDER_ERROR", f"ASR failed [{code}]: {msg}")
        if time.monotonic() > deadline:
            raise VoiceError("TIMEOUT", f"ASR job not finished within {wait:.0f}s")


def _utterance(u: dict) -> dict:
    extra = u.get("additions") or {}
    out = {"start": u["start_time"] / 1000, "end": u["end_time"] / 1000, "text": u.get("text", "").strip()}
    if extra.get("speaker"):
        out["speaker"] = extra["speaker"]
    for k in ("emotion", "gender"):
        if extra.get(k):
            out[k] = extra[k]
    if extra.get("speech_rate"):
        out["speech_rate"] = round(float(extra["speech_rate"]), 2)
    # start_time -1 marks placeholder spaces between Chinese and Latin words.
    out["words"] = [{"start": w["start_time"] / 1000, "end": w["end_time"] / 1000, "text": w["text"]}
                    for w in u.get("words") or [] if w.get("start_time", -1) >= 0]
    return out


def _overlap(a: dict, b: dict) -> float:
    return max(0.0, min(a["end"], b["end"]) - max(a["start"], b["start"]))


def transcribe(path: str, language: str, speakers: bool) -> dict:
    duration = probe_duration(path)
    b64 = base64.b64encode(encode_mp3(path, 0, duration)).decode("ascii")
    if len(b64) > ASR_MAX_B64_BYTES:
        raise VoiceError("UNSUPPORTED_FORMAT", "Audio exceeds 100MB base64 (~3.5h at 64 kbps); split the file")
    passes = 2 if speakers else 1
    log(f"pass 1/{passes}: text + word timestamps ({duration:.0f}s)…")
    utts = [_utterance(u) for u in _asr_pass(b64, ASR_PASS_TEXT, language, duration)]
    if speakers:
        log(f"pass 2/{passes}: speaker labels…")
        labelled = [_utterance(u) for u in _asr_pass(b64, ASR_PASS_SPEAKER, language, duration)]
        for u in utts:
            best = max(labelled, key=lambda s: _overlap(u, s), default=None)
            if best and _overlap(u, best) > 0:
                u["speaker"] = best["speaker"]
        # Pass 1 can drop a speaker who cuts in without a pause; pass 2 keeps them, so fill the gaps from it.
        utts += [s for s in labelled if not any(_overlap(s, u) > 0 for u in utts)]
        utts.sort(key=lambda u: u["start"])
    lines = [(f"[S{u['speaker']}] " if "speaker" in u else "") + u["text"] for u in utts if u["text"]]
    return {"file": path, "model": ASR_MODEL, "language": language, "duration": round(duration, 2),
            "segments": utts, "text": "\n".join(lines) or "NO_SPEECH_DETECTED"}


# ── TTS ──────────────────────────────────────────────────────────────────

STYLE_TAG = re.compile(r"^\s*([(（\[][^()（）\[\]]{1,40}[)）\]])")
SENTENCE = re.compile(r".+?(?:[。！？!?；;…]+[」』”’\"]*|\.(?=\s)|$)")


def split_text(text: str, limit: int) -> list[str]:
    """Pack whole sentences into chunks of at most `limit` chars; keep paragraph breaks."""
    pieces = []
    for para in text.splitlines():
        sentences = [s.strip() for s in SENTENCE.findall(para.strip()) if s.strip()]
        for s in sentences:
            while len(s) > limit:  # overlong sentence: cut at the last comma, else hard cut
                cut = max(s.rfind(c, 0, limit) for c in "，,、：:")
                cut = cut + 1 if cut > 0 else limit
                pieces.append(s[:cut])
                s = s[cut:]
            pieces.append(s)
        if pieces and sentences:
            pieces[-1] += "\n"
    chunks, cur = [], ""
    for p in pieces:
        if cur and len(cur) + len(p) > limit:
            chunks.append(cur.strip())
            cur = ""
        if cur and not cur.endswith("\n") and p[0].isascii() and p[0].isalnum():
            cur += " "  # rejoin space-separated (e.g. English) sentences
        cur += p
    if cur.strip():
        chunks.append(cur.strip())
    return chunks


def _audio_data_url(path: str) -> str:
    """Clone reference as a data URL; non-mp3/wav or oversized input is re-encoded to mp3."""
    p = Path(path)
    if probe_duration(path) < 1.0:  # the API accepts an empty reference and silently uses a default voice
        raise VoiceError("UNSUPPORTED_FORMAT", f"Clone reference is shorter than 1s: {path}")
    raw = p.read_bytes()
    mime = {".mp3": "audio/mpeg", ".wav": "audio/wav"}.get(p.suffix.lower())
    if not mime or len(raw) * 4 / 3 > MAX_B64_BYTES:
        raw, mime = encode_mp3(path, 0, probe_duration(path)), "audio/mpeg"
    b64 = base64.b64encode(raw).decode("ascii")
    if len(b64) > MAX_B64_BYTES:
        raise VoiceError("UNSUPPORTED_FORMAT", "Clone reference exceeds 10MB base64; use a shorter clip")
    return f"data:{mime};base64,{b64}"


def _tts_once(model: str, text: str, user: str, voice: str | None) -> bytes:
    audio = {"format": "wav"}
    if voice:
        audio["voice"] = voice
    data = _request("POST", "/chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": user}, {"role": "assistant", "content": text}],
        "audio": audio,
    })
    b64 = ((_choice(data).get("message") or {}).get("audio") or {}).get("data")
    if not b64:
        raise VoiceError("PROVIDER_ERROR", "Response contained no audio")
    return base64.b64decode(b64)


def _concat_wav(parts: list[bytes]) -> bytes:
    out = io.BytesIO()
    writer = None
    for part in parts:
        with wave.open(io.BytesIO(part)) as r:
            if writer is None:
                writer = wave.open(out, "wb")
                writer.setparams(r.getparams())
            writer.writeframes(r.readframes(r.getnframes()))
    writer.close()
    return out.getvalue()


def synthesize(text: str, voice: str | None, clone: str | None, design: str | None, style: str) -> bytes:
    tag_match = STYLE_TAG.match(text)
    tag = tag_match.group(1) if tag_match else ""
    body = text[tag_match.end():] if tag_match else text
    chunks = split_text(body, TTS_CHUNK_CHARS)
    if not chunks:
        raise VoiceError("UNSUPPORTED_FORMAT", "No text to synthesize")
    log(f"plan: {len(body)} chars → {len(chunks)} chunk(s)")
    parts = []
    if clone:
        model, user, ref = CLONE_MODEL, style, _audio_data_url(clone)
    elif design:
        model, user, ref = DESIGN_MODEL, f"{design} {style}".strip(), None
    else:
        model, user, ref = TTS_MODEL, style, voice or "mimo_default"
    for i, chunk in enumerate(chunks, 1):
        log(f"chunk {i}/{len(chunks)} ({len(chunk)} chars, {model})…")
        parts.append(_tts_once(model, tag + chunk, user, ref))
        if design and i == 1 and len(chunks) > 1:
            # A designed voice is not reusable by id: clone chunk 1 so later chunks keep the same voice.
            model, ref = CLONE_MODEL, "data:audio/wav;base64," + base64.b64encode(parts[0]).decode("ascii")
    return _concat_wav(parts)


def write_audio(wav_bytes: bytes, out: Path, bitrate: str = "64k") -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".wav":
        out.write_bytes(wav_bytes)
        return
    proc = _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "wav", "-i", "pipe:0", "-b:a", bitrate, str(out)],
                600, stdin=wav_bytes)
    if proc.returncode != 0:
        raise VoiceError("UNSUPPORTED_FORMAT", f"ffmpeg could not write {out}: {proc.stderr.decode(errors='replace')[:300]}")


# ── Audio generation (Seed Audio) ────────────────────────────────────────

def gen_model() -> str:
    return _env("DOUBAO_AUDIO_MODEL", GEN_MODEL)


def _gen(body: dict) -> dict:
    return _http("POST", GEN_URL, {"X-Api-Key": doubao_key(), "X-Api-Request-Id": str(uuid.uuid4())}, body)[1]


def _gen_ref_audio(path: str) -> dict:
    """One @音频N reference; non-mp3/wav or oversized input is re-encoded to mp3."""
    seconds = probe_duration(path)
    if seconds > GEN_REF_MAX_SECONDS:
        raise VoiceError("UNSUPPORTED_FORMAT", f"Reference is {seconds:.1f}s, over the {GEN_REF_MAX_SECONDS}s limit: {path}")
    raw = Path(path).read_bytes()
    if Path(path).suffix.lower() not in (".mp3", ".wav") or len(raw) > MAX_B64_BYTES:
        proc = _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path, "-vn",
                     "-c:a", "libmp3lame", "-b:a", "192k", "-f", "mp3", "pipe:1"], 300)
        if proc.returncode != 0 or not proc.stdout:
            raise VoiceError("UNSUPPORTED_FORMAT", f"ffmpeg could not decode audio: {proc.stderr.decode(errors='replace')[:300]}")
        raw = proc.stdout
    return {"audio_data": base64.b64encode(raw).decode("ascii")}


def _gen_image(path: str) -> dict:
    p = Path(path)
    if p.suffix.lower() not in GEN_IMAGE_TYPES or p.stat().st_size > MAX_B64_BYTES:
        raise VoiceError("UNSUPPORTED_FORMAT", f"Reference image must be jpeg/png/webp and ≤10MB: {path}")
    return {"image_data": base64.b64encode(p.read_bytes()).decode("ascii")}


def _ms_segments(subtitle: dict) -> list[dict]:
    """Seed Audio subtitle (ms offsets) → the same segment shape as asr --output json (seconds)."""
    return [{"start": s["start_time"] / 1000, "end": s["end_time"] / 1000, "text": s.get("text", ""),
             "words": [{"start": w["start_time"] / 1000, "end": w["end_time"] / 1000, "text": w["text"]}
                       for w in s.get("words") or []]}
            for s in (subtitle or {}).get("sentences") or []]


def generate(prompt: str, refs: list[str], speaker: str | None, image: str | None, subtitle: bool) -> dict:
    prompt = prompt.strip()
    if not prompt:
        raise VoiceError("UNSUPPORTED_FORMAT", "No prompt to generate from")
    if len(prompt) > GEN_MAX_PROMPT_CHARS:
        raise VoiceError("UNSUPPORTED_FORMAT", f"Prompt is {len(prompt)} chars, over {GEN_MAX_PROMPT_CHARS}; split the scene")
    ends = [float(t) for t in TIMELINE_TAG.findall(prompt)]
    if ends and max(ends) > GEN_MAX_SECONDS:
        raise VoiceError("UNSUPPORTED_FORMAT", f"Timeline runs to {max(ends):g}s; one call makes at most "
                                               f"{GEN_MAX_SECONDS}s. Split the scene into ≤{GEN_MAX_SECONDS}s parts")
    if len(refs) > GEN_MAX_REFS:
        raise VoiceError("UNSUPPORTED_FORMAT", f"At most {GEN_MAX_REFS} --ref clips (@音频1..{GEN_MAX_REFS})")
    if image and (refs or speaker):
        raise VoiceError("UNSUPPORTED_FORMAT", "--image cannot be combined with --ref or --speaker")
    references = [_gen_ref_audio(r) for r in refs]
    if speaker:
        references.append({"speaker": speaker})
    if image:
        references.append(_gen_image(image))
    body = {"model": gen_model(), "text_prompt": prompt,
            "audio_config": {"format": "wav", "sample_rate": 48000, "enable_subtitle": subtitle}}
    if references:
        body["references"] = references
    log(f"generating ({len(prompt)} chars, {len(references)} reference(s), {body['model']})…")
    data = _gen(body)
    if data.get("code") not in (None, 0):
        raise VoiceError("PROVIDER_ERROR", f"Audio generation failed [{data.get('code')}]: {data.get('message')}")
    if not data.get("audio"):
        raise VoiceError("PROVIDER_ERROR", "Response contained no audio")
    if data.get("original_duration", 0) >= GEN_MAX_SECONDS - 0.5:
        log(f"warning: output reached the {GEN_MAX_SECONDS}s cap and may be cut off; split the scene")
    return data


# ── CLI ──────────────────────────────────────────────────────────────────

def check() -> dict:
    result = {
        "ffmpeg": shutil.which("ffmpeg") or "MISSING",
        "ffprobe": shutil.which("ffprobe") or "MISSING",
        "base_url": base_url(),
        "has_mimo_key": bool(_env("MIMO_API_KEY")),
        "has_doubao_key": bool(_env("DOUBAO_API_KEY")),
    }
    try:
        ids = [m.get("id") for m in _request("GET", "/models").get("data", [])]
        result["tts_models"] = [m for m in (TTS_MODEL, CLONE_MODEL, DESIGN_MODEL) if m in ids]
    except VoiceError as e:
        result["tts_models"] = f"ERROR: {e}"
    try:
        # A random task id answers 45000092 (task not found) once the key and resource are accepted.
        code, msg, _ = _doubao("query", {}, str(uuid.uuid4()))
        result["asr"] = "ok" if code == "45000092" else f"ERROR [{code}]: {msg}"
    except VoiceError as e:
        result["asr"] = f"ERROR: {e}"
    try:
        # The model/resource is checked before the body, so an empty prompt answers 45001116 only when access is fine.
        _gen({"model": gen_model(), "text_prompt": ""})
        result["audio_gen"] = "ERROR: empty prompt was accepted"
    except VoiceError as e:
        result["audio_gen"] = "ok" if "45001116" in str(e) else f"ERROR: {e}"
    result["ok"] = (result["ffmpeg"] != "MISSING" and result["ffprobe"] != "MISSING" and result["asr"] == "ok"
                    and result["audio_gen"] == "ok"
                    and isinstance(result["tts_models"], list) and len(result["tts_models"]) == 3)
    return result


def _read_text(args) -> str:
    if args.text_file:
        p = Path(args.text_file)
        if not p.is_file():
            raise VoiceError("INPUT_NOT_FOUND", f"Text file not found: {p}")
        return p.read_text(encoding="utf-8")
    if args.text == "-":
        return sys.stdin.buffer.read().decode("utf-8")
    if not args.text:
        raise VoiceError("UNSUPPORTED_FORMAT", "Give text, --text-file, or - for stdin")
    return args.text


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Speech-to-text via Doubao, text-to-speech via Xiaomi MiMo v2.5, "
                                                 "audio generation via Doubao Seed Audio")
    parser.add_argument("--check", action="store_true", help="Check ffmpeg, key, and model access")
    sub = parser.add_subparsers(dest="cmd")

    asr = sub.add_parser("asr", help="Transcribe speech from an audio or video file")
    asr.add_argument("file")
    asr.add_argument("--language", "-l", default="auto", choices=["auto", "zh", "en"])
    asr.add_argument("--speakers", action="store_true", help="Second pass for speaker labels (multi-person audio)")
    asr.add_argument("--output", choices=["text", "json"], default="text")
    asr.add_argument("--out", help="Also write the result to this file")

    tts = sub.add_parser("tts", help="Synthesize speech")
    tts.add_argument("text", nargs="?", help="Text to speak, or - to read stdin")
    tts.add_argument("--text-file", "-f")
    voice = tts.add_mutually_exclusive_group()
    voice.add_argument("--voice", "-v", choices=PRESET_VOICES, help="Preset voice (default mimo_default)")
    voice.add_argument("--clone", "-c", metavar="REF_AUDIO", help="Clone the voice in this recording")
    voice.add_argument("--design", "-d", metavar="DESCRIPTION", help="Design a voice from a description")
    tts.add_argument("--style", "-s", default="", help="Natural-language delivery direction")
    tts.add_argument("--out", "-o", help="Output file (.wav default; other extensions via ffmpeg)")

    gen = sub.add_parser("gen", help="Generate sound effects, music or a scene from a description (≤120s)")
    gen.add_argument("text", nargs="?", metavar="PROMPT", help="Prompt, or - to read stdin")
    gen.add_argument("--text-file", "-f")
    gen.add_argument("--ref", "-r", action="append", default=[], metavar="AUDIO",
                     help="Reference clip ≤30s, repeatable up to 3; the Nth is @音频N in the prompt")
    gen.add_argument("--speaker", help="Doubao TTS 2.0 voice id or cloned-voice id")
    gen.add_argument("--image", "-i", metavar="IMG", help="Reference image (jpeg/png/webp); not with --ref/--speaker")
    gen.add_argument("--subtitle", action="store_true", help="Also return sentence and word timestamps")
    gen.add_argument("--out", "-o", help="Output file (.wav default; other extensions via ffmpeg)")

    args = parser.parse_args()
    try:
        if args.check:
            result = check()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 2
        if args.cmd == "asr":
            if not Path(args.file).is_file():
                raise VoiceError("INPUT_NOT_FOUND", f"File not found: {args.file}")
            result = transcribe(args.file, args.language, args.speakers)
            rendered = json.dumps(result, ensure_ascii=False, indent=2) if args.output == "json" else result["text"]
            if args.out:
                Path(args.out).write_text(rendered + "\n", encoding="utf-8")
                log(f"saved → {args.out}")
            print(rendered)
            return 0
        if args.cmd == "tts":
            if args.clone and not Path(args.clone).is_file():
                raise VoiceError("INPUT_NOT_FOUND", f"Reference audio not found: {args.clone}")
            wav_bytes = synthesize(_read_text(args), args.voice, args.clone, args.design, args.style)
            out = Path(args.out or f"genius-voice-{datetime.now():%Y%m%d-%H%M%S}.wav")
            write_audio(wav_bytes, out)
            with wave.open(io.BytesIO(wav_bytes)) as r:
                seconds = r.getnframes() / r.getframerate()
            print(json.dumps({"out": str(out.resolve()), "seconds": round(seconds, 2)}, ensure_ascii=False))
            return 0
        if args.cmd == "gen":
            for f in args.ref + ([args.image] if args.image else []):
                if not Path(f).is_file():
                    raise VoiceError("INPUT_NOT_FOUND", f"Reference file not found: {f}")
            data = generate(_read_text(args), args.ref, args.speaker, args.image, args.subtitle)
            out = Path(args.out or f"genius-voice-{datetime.now():%Y%m%d-%H%M%S}.wav")
            write_audio(base64.b64decode(data["audio"]), out, bitrate="192k")
            result = {"out": str(out.resolve()), "seconds": round(float(data.get("duration") or 0), 2)}
            if args.subtitle:
                result["segments"] = _ms_segments(data.get("subtitle"))
            print(json.dumps(result, ensure_ascii=False))
            return 0
        parser.print_help()
        return 1
    except VoiceError as e:
        print(f"Error [{e.code}]: {e}", file=sys.stderr)
        return EXIT_CODES.get(e.code, 1)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
