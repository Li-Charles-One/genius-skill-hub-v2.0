#!/usr/bin/env python3
"""
Genius Voice — speech-to-text and text-to-speech via Xiaomi MiMo v2.5.

    python3 voice.py --check
    python3 voice.py asr <audio_or_video> [--language auto|zh|en] [--output text|json] [--out FILE]
    python3 voice.py tts "<text>" | --text-file F | -   [--voice ID | --clone REF | --design PROMPT]
                     [--style "<direction>"] [--out FILE.wav|.mp3]

Models: mimo-v2.5-asr, mimo-v2.5-tts, mimo-v2.5-tts-voiceclone, mimo-v2.5-tts-voicedesign.
Failures print `Error [CODE]: ...` to stderr and exit with EXIT_CODES[CODE].
"""

from __future__ import annotations

import argparse
import base64
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
import wave
from datetime import datetime
from functools import lru_cache
from pathlib import Path

DEFAULT_BASE_URL = "https://api.xiaomimimo.com/v1"
ASR_MODEL = "mimo-v2.5-asr"
TTS_MODEL = "mimo-v2.5-tts"
CLONE_MODEL = "mimo-v2.5-tts-voiceclone"
DESIGN_MODEL = "mimo-v2.5-tts-voicedesign"
PRESET_VOICES = ["mimo_default", "冰糖", "茉莉", "苏打", "白桦", "Mia", "Chloe", "Milo", "Dean"]

# Measured: 180–300s segments silently drop whole passages with finish=stop; 120s kept everything.
ASR_SEGMENT_SEC = float(os.environ.get("VOICE_ASR_SEGMENT_SEC", "120"))
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


# ── HTTP ─────────────────────────────────────────────────────────────────

RETRY_HTTP = {429, 500, 502, 503, 504}
RETRY_DELAYS = (5, 15, 30)


def _request(method: str, path: str, body: dict | None = None) -> dict:
    key = api_key()
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Content-Type": "application/json", "api-key": key, "Authorization": f"Bearer {key}"}
    for attempt, delay in enumerate((*RETRY_DELAYS, None), 1):
        req = urllib.request.Request(base_url() + path, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace")
            try:
                err = json.loads(text).get("error")
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
        if delay is None or not transient:
            raise error
        log(f"{error} — retry {attempt}/{len(RETRY_DELAYS)} in {delay}s…")
        time.sleep(delay)
    raise AssertionError("unreachable")


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


def silence_midpoints(path: str) -> list[float]:
    proc = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", path, "-vn",
                 "-af", "silencedetect=noise=-35dB:d=0.25", "-f", "null", "-"], 1800)
    text = proc.stderr.decode("utf-8", errors="replace")
    starts = [float(x) for x in re.findall(r"silence_start: ([\d.]+)", text)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", text)]
    return [(s + e) / 2 for s, e in zip(starts, ends)]


def plan_cuts(duration: float, seg: float, silences: list[float]) -> list[tuple[float, float]]:
    """Cut at the latest silence in the back half of each window, else at the window end."""
    cuts = [0.0]
    while duration - cuts[-1] > seg:
        lo, hi = cuts[-1] + seg / 2, cuts[-1] + seg
        cands = [m for m in silences if lo < m <= hi]
        cuts.append(max(cands) if cands else hi)
    cuts.append(duration)
    return list(zip(cuts, cuts[1:]))


def encode_mp3(path: str, start: float, length: float) -> bytes:
    proc = _run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{start:.3f}", "-t", f"{length:.3f}",
                 "-i", path, "-vn", "-ac", "1", "-ar", "16000", "-c:a", "libmp3lame", "-b:a", "64k",
                 "-f", "mp3", "pipe:1"], 900)
    if proc.returncode != 0 or not proc.stdout:
        raise VoiceError("UNSUPPORTED_FORMAT", f"ffmpeg could not decode audio: {proc.stderr.decode(errors='replace')[:300]}")
    return proc.stdout


# ── ASR ──────────────────────────────────────────────────────────────────

def _asr_once(mp3: bytes, language: str) -> tuple[str, str]:
    b64 = base64.b64encode(mp3).decode("ascii")
    if len(b64) > MAX_B64_BYTES:
        raise VoiceError("UNSUPPORTED_FORMAT", "Segment exceeds 10MB base64; lower VOICE_ASR_SEGMENT_SEC")
    data = _request("POST", "/chat/completions", {
        "model": ASR_MODEL,
        "messages": [{"role": "user", "content": [
            {"type": "input_audio", "input_audio": {"data": f"data:audio/mpeg;base64,{b64}"}}]}],
        "asr_options": {"language": language},
    })
    choice = _choice(data)
    return (choice.get("message") or {}).get("content") or "", choice.get("finish_reason") or ""


def _asr_piece(path: str, start: float, end: float, language: str, silences: list[float]) -> list[dict]:
    text, finish = _asr_once(encode_mp3(path, start, end - start), language)
    if finish != "length":
        return [{"start": round(start, 2), "end": round(end, 2), "text": text.strip()}]
    if end - start < 30:
        raise VoiceError("PROVIDER_ERROR", f"Transcript truncated even for {end - start:.0f}s at {start:.0f}s")
    span = end - start
    cands = [m for m in silences if start + span / 4 < m < end - span / 4]
    mid = min(cands, key=lambda m: abs(m - (start + end) / 2)) if cands else (start + end) / 2
    log(f"output limit hit at {start:.0f}–{end:.0f}s, re-splitting at {mid:.0f}s")
    return _asr_piece(path, start, mid, language, silences) + _asr_piece(path, mid, end, language, silences)


def transcribe(path: str, language: str) -> dict:
    duration = probe_duration(path)
    silences = silence_midpoints(path) if duration > ASR_SEGMENT_SEC else []
    pieces = plan_cuts(duration, ASR_SEGMENT_SEC, silences)
    log(f"plan: {duration:.0f}s → {len(pieces)} segment(s)")
    segments = []
    for i, (start, end) in enumerate(pieces, 1):
        log(f"segment {i}/{len(pieces)} {start:.0f}–{end:.0f}s…")
        segments += _asr_piece(path, start, end, language, silences)
    text = "\n".join(s["text"] for s in segments if s["text"])
    return {"file": path, "model": ASR_MODEL, "language": language, "duration": round(duration, 2),
            "segments": segments, "text": text or "NO_SPEECH_DETECTED"}


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


def write_audio(wav_bytes: bytes, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.suffix.lower() == ".wav":
        out.write_bytes(wav_bytes)
        return
    proc = _run(["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "wav", "-i", "pipe:0", "-b:a", "64k", str(out)],
                600, stdin=wav_bytes)
    if proc.returncode != 0:
        raise VoiceError("UNSUPPORTED_FORMAT", f"ffmpeg could not write {out}: {proc.stderr.decode(errors='replace')[:300]}")


# ── CLI ──────────────────────────────────────────────────────────────────

def check() -> dict:
    result = {
        "ffmpeg": shutil.which("ffmpeg") or "MISSING",
        "ffprobe": shutil.which("ffprobe") or "MISSING",
        "base_url": base_url(),
        "has_key": bool(_env("MIMO_API_KEY")),
    }
    try:
        ids = [m.get("id") for m in _request("GET", "/models").get("data", [])]
        result["audio_models"] = [m for m in (ASR_MODEL, TTS_MODEL, CLONE_MODEL, DESIGN_MODEL) if m in ids]
    except VoiceError as e:
        result["audio_models"] = f"ERROR: {e}"
    result["ok"] = (result["ffmpeg"] != "MISSING" and result["ffprobe"] != "MISSING"
                    and isinstance(result["audio_models"], list) and len(result["audio_models"]) == 4)
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
    parser = argparse.ArgumentParser(description="Speech-to-text and text-to-speech via Xiaomi MiMo v2.5")
    parser.add_argument("--check", action="store_true", help="Check ffmpeg, key, and model access")
    sub = parser.add_subparsers(dest="cmd")

    asr = sub.add_parser("asr", help="Transcribe speech from an audio or video file")
    asr.add_argument("file")
    asr.add_argument("--language", "-l", default="auto", choices=["auto", "zh", "en"])
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

    args = parser.parse_args()
    try:
        if args.check:
            result = check()
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0 if result["ok"] else 2
        if args.cmd == "asr":
            if not Path(args.file).is_file():
                raise VoiceError("INPUT_NOT_FOUND", f"File not found: {args.file}")
            result = transcribe(args.file, args.language)
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
        parser.print_help()
        return 1
    except VoiceError as e:
        print(f"Error [{e.code}]: {e}", file=sys.stderr)
        return EXIT_CODES.get(e.code, 1)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())
